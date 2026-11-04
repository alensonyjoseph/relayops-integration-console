"""Flask HTTP API. Synthetic workspaces isolate reviewers without requiring accounts.

This is an unauthenticated portfolio demo, not a production multi-tenant service.
No confidential data should be entered.
"""
import os
import uuid
from flask import Flask, request, jsonify
from pydantic import ValidationError
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from .db import Shipment, Event, AuditEntry, create_database_engine, session_factory
from .schemas import ShipmentInput, EventInput
from .service import (ProcessingError, process_event, resolve_identity_race,
                      snapshot, event_snapshot, MAX_SHIPMENTS)
from .seed import populate_demo
from .bootstrap import DemoSchemaInitializer

def make_error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status

def workspace_id() -> str:
    raw = request.headers.get("X-RelayOps-Workspace", "")
    try:
        return str(uuid.UUID(raw))
    except (ValueError, AttributeError):
        raise ProcessingError("WORKSPACE_REQUIRED",
                              "Provide a UUID in X-RelayOps-Workspace (the UI does this automatically).", 400)

def create_app(database_url: str | None = None) -> Flask:
    app = Flask(__name__)
    app.json.sort_keys = False
    engine = create_database_engine(database_url)
    make_session = session_factory(engine) if engine is not None else None
    demo_enabled = os.getenv("DEMO_MODE", "true").lower() == "true"
    auto_migrate = demo_enabled and os.getenv("AUTO_MIGRATE_DEMO", "false").lower() == "true"
    initializer = DemoSchemaInitializer(engine) if (auto_migrate and engine is not None) else None

    @app.errorhandler(ProcessingError)
    def processing_error(exc):
        return make_error(exc.code, exc.message, exc.http_status)

    @app.errorhandler(ValidationError)
    def validation_error(exc):
        fields = [".".join(map(str, e["loc"])) for e in exc.errors()]
        return jsonify({"error": {"code": "INVALID_PAYLOAD", "message": "Check the request fields.",
                                  "fields": fields}}), 400

    @app.errorhandler(SQLAlchemyError)
    def database_error(exc):
        app.logger.exception("Database operation failed")
        return make_error("DATABASE_UNAVAILABLE", "The database is unavailable or needs migrations.", 503)

    @app.before_request
    def require_database():
        if not request.path.startswith("/api/"):
            return None
        if request.path != "/api/health" and make_session is None:
            return make_error("DATABASE_NOT_CONFIGURED", "DATABASE_URL is not configured.", 503)
        if initializer is not None:
            try:
                initializer.ensure()
            except Exception:
                app.logger.exception("Demo database migration failed")
                return make_error("DATABASE_SETUP_FAILED", "Unable to initialize the demo database.", 503)
        return None

    @app.get("/api/health")
    def health():
        if make_session is None:
            return jsonify({"status": "setup_required", "database": "not_configured"}), 503
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM shipments LIMIT 1"))
            return jsonify({"status": "ok", "database": "connected"})
        except SQLAlchemyError:
            return jsonify({"status": "degraded", "database": "unavailable"}), 503

    @app.get("/api/shipments")
    def shipments():
        ws = workspace_id()
        with make_session() as db:
            records = db.scalars(select(Shipment).where(Shipment.workspace_id == ws).order_by(Shipment.created_at.desc())).all()
            return jsonify({"shipments": [snapshot(s) for s in records], "count": len(records)})

    @app.post("/api/shipments")
    def create_shipment():
        ws = workspace_id()
        data = ShipmentInput.model_validate(request.get_json(silent=True) or {})
        with make_session.begin() as db:
            count = db.scalar(select(func.count()).select_from(Shipment).where(Shipment.workspace_id == ws))
            if count >= MAX_SHIPMENTS:
                raise ProcessingError("DEMO_LIMIT_REACHED", "Maximum 25 demo shipments per workspace.", 429)
            if db.scalar(select(Shipment.id).where(Shipment.workspace_id == ws, Shipment.reference == data.reference)):
                raise ProcessingError("SHIPMENT_EXISTS", "Shipment reference already exists.", 409)
            item = Shipment(workspace_id=ws, reference=data.reference, partner=data.partner)
            db.add(item)
            db.flush()
            result = snapshot(item)
        return jsonify({"shipment": result}), 201

    @app.get("/api/shipments/<reference>")
    def shipment_details(reference):
        ws = workspace_id()
        with make_session() as db:
            shipment = db.scalar(select(Shipment).where(Shipment.workspace_id == ws, Shipment.reference == reference))
            if not shipment:
                raise ProcessingError("SHIPMENT_NOT_FOUND", "No shipment with that reference.", 404)
            records = db.scalars(select(Event).where(Event.shipment_id == shipment.id).order_by(Event.received_at.desc(), Event.external_id.desc())).all()
            audit = db.scalars(select(AuditEntry).where(AuditEntry.shipment_id == shipment.id).order_by(AuditEntry.created_at.desc())).all()
            return jsonify({"shipment": snapshot(shipment),
                            "events": [event_snapshot(e, reference) for e in records],
                            "audit": [{"event_id": a.event_id, "action": a.action, "before": a.previous_status,
                                       "after": a.resulting_status, "reason": a.reason} for a in audit]})

    @app.post("/api/events")
    def ingest_event():
        ws = workspace_id()
        payload = EventInput.model_validate(request.get_json(silent=True) or {})
        try:
            with make_session.begin() as db:
                result, status = process_event(db, ws, payload)
        except IntegrityError:
            # Distinguish an identical concurrent retry from an identity collision.
            with make_session.begin() as db:
                result, status = resolve_identity_race(db, ws, payload)
        return jsonify(result), status

    @app.get("/api/events")
    def events():
        ws = workspace_id()
        outcome = request.args.get("outcome", "").upper()
        if outcome and outcome not in {"ACCEPTED", "REJECTED"}:
            raise ProcessingError("INVALID_FILTER", "Outcome must be ACCEPTED or REJECTED.", 400)
        try:
            limit = min(100, max(1, int(request.args.get("limit", "50"))))
        except ValueError:
            raise ProcessingError("INVALID_FILTER", "limit must be an integer.", 400)
        with make_session() as db:
            stmt = select(Event).where(Event.workspace_id == ws)
            if outcome:
                stmt = stmt.where(Event.outcome == outcome)
            rows = db.scalars(stmt.order_by(Event.received_at.desc(), Event.external_id.desc()).limit(limit)).all()
            return jsonify({"events": [event_snapshot(e) for e in rows]})

    @app.get("/api/metrics")
    def metrics():
        ws = workspace_id()
        with make_session() as db:
            shipments_count = db.scalar(select(func.count()).select_from(Shipment).where(Shipment.workspace_id == ws))
            accepted = db.scalar(select(func.count()).select_from(Event).where(Event.workspace_id == ws, Event.outcome == "ACCEPTED"))
            rejected = db.scalar(select(func.count()).select_from(Event).where(Event.workspace_id == ws, Event.outcome == "REJECTED"))
            replays = db.scalar(select(func.coalesce(func.sum(Event.replay_count), 0)).where(Event.workspace_id == ws))
            return jsonify({"shipments": shipments_count, "accepted": accepted, "rejected": rejected,
                            "duplicates": replays, "processed": accepted + rejected + replays})

    @app.post("/api/demo/seed")
    def seed():
        if not demo_enabled:
            raise ProcessingError("DEMO_DISABLED", "Demo mutation is disabled.", 403)
        ws = workspace_id()
        with make_session.begin() as db:
            count = populate_demo(db, ws)
        return jsonify({"created_shipments": count})

    @app.post("/api/demo/reset")
    def reset():
        if not demo_enabled:
            raise ProcessingError("DEMO_DISABLED", "Demo mutation is disabled.", 403)
        ws = workspace_id()
        with make_session.begin() as db:
            # Explicit FK order, restricted to this synthetic workspace.
            db.query(AuditEntry).filter(AuditEntry.workspace_id == ws).delete(synchronize_session=False)
            db.query(Event).filter(Event.workspace_id == ws).delete(synchronize_session=False)
            db.query(Shipment).filter(Shipment.workspace_id == ws).delete(synchronize_session=False)
        return jsonify({"status": "reset", "workspace": ws})

    @app.after_request
    def safe_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    return app
