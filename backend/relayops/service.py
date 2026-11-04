"""Idempotent, transactional event processing with deterministic reason codes."""
import hashlib
import json
from datetime import timezone
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .db import Shipment, Event, AuditEntry
from .domain import qualify_transition
from .schemas import EventInput

MAX_SHIPMENTS = 25
MAX_EVENTS = 350

def fingerprint(data: EventInput) -> str:
    # Normalize timestamps to UTC so equivalent offsets produce the same identity.
    obj = data.model_dump(mode="json")
    obj["occurred_at"] = data.occurred_at.astimezone(timezone.utc).isoformat()
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()

def snapshot(shipment: Shipment) -> dict:
    return {
        "reference": shipment.reference, "partner": shipment.partner,
        "status": shipment.status, "version": shipment.version,
        "created_at": shipment.created_at.isoformat() if shipment.created_at else None,
        "last_event_at": shipment.last_event_at.isoformat() if shipment.last_event_at else None,
    }

def event_snapshot(event: Event, shipment_ref: str | None = None) -> dict:
    return {
        "id": event.id, "source": event.source, "event_id": event.external_id,
        "shipment_ref": shipment_ref or event.shipment.reference,
        "requested_status": event.requested_status,
        "occurred_at": event.occurred_at.isoformat(),
        "received_at": event.received_at.isoformat() if event.received_at else None,
        "outcome": event.outcome, "rejection_reason": event.rejection_reason,
        "replay_count": event.replay_count,
    }

class ProcessingError(Exception):
    def __init__(self, code: str, message: str, http_status: int):
        self.code, self.message, self.http_status = code, message, http_status
        super().__init__(message)

def process_event(session: Session, workspace: str, payload: EventInput) -> tuple[dict, int]:
    digest = fingerprint(payload)

    # Lock the existing shipment first to serialize transitions for its state.
    shipment = session.execute(
        select(Shipment).where(Shipment.workspace_id == workspace, Shipment.reference == payload.shipment_ref)
        .with_for_update()
    ).scalar_one_or_none()
    if shipment is None:
        raise ProcessingError("SHIPMENT_NOT_FOUND", "Create the shipment before sending events.", 404)

    previous = session.execute(
        select(Event).where(Event.workspace_id == workspace, Event.source == payload.source,
                            Event.external_id == payload.event_id).with_for_update()
    ).scalar_one_or_none()
    if previous:
        if previous.payload_hash != digest:
            raise ProcessingError("EVENT_ID_CONFLICT", "Event identity was reused with a different payload.", 409)
        previous.replay_count += 1
        return {
            "outcome": "DUPLICATE", "event_id": payload.event_id,
            "original_outcome": previous.outcome, "shipment": snapshot(shipment),
            "message": "Identical retry: state was not changed.",
        }, 200

    total = session.scalar(select(func.count()).select_from(Event).where(Event.workspace_id == workspace))
    if total >= MAX_EVENTS:
        raise ProcessingError("DEMO_LIMIT_REACHED", "Demo event limit reached. Reset this workspace.", 429)

    reason = qualify_transition(shipment.status, payload.status, payload.occurred_at, shipment.last_event_at)
    before = shipment.status
    outcome = "REJECTED" if reason else "ACCEPTED"
    event = Event(
        workspace_id=workspace, shipment_id=shipment.id, source=payload.source,
        external_id=payload.event_id, payload_hash=digest,
        requested_status=payload.status, occurred_at=payload.occurred_at.astimezone(timezone.utc),
        outcome=outcome, rejection_reason=reason, replay_count=0,
    )
    session.add(event)
    session.flush()  # Ensures event.id is populated and identity is enforced.
    if not reason:
        shipment.status = payload.status
        shipment.last_event_at = payload.occurred_at.astimezone(timezone.utc)
        shipment.version += 1
    session.add(AuditEntry(
        workspace_id=workspace, shipment_id=shipment.id, event_id=event.id,
        previous_status=before, resulting_status=shipment.status,
        action=outcome, reason=reason,
    ))
    return {
        "outcome": outcome,
        "event_id": payload.event_id,
        "reason": reason,
        "message": "Event applied." if not reason else "Event rejected: " + reason,
        "shipment": snapshot(shipment),
    }, 201 if not reason else 422

def resolve_identity_race(session: Session, workspace: str, payload: EventInput) -> tuple[dict, int]:
    """Handle a unique-constraint race after a competing request commits."""
    existing = session.execute(select(Event).where(
        Event.workspace_id == workspace, Event.source == payload.source,
        Event.external_id == payload.event_id
    )).scalar_one_or_none()
    if not existing:
        raise ProcessingError("WRITE_CONFLICT", "Concurrent update; please retry.", 409)
    if existing.payload_hash != fingerprint(payload):
        raise ProcessingError("EVENT_ID_CONFLICT", "Event identity was reused with a different payload.", 409)
    existing.replay_count += 1
    shipment = session.get(Shipment, existing.shipment_id)
    return {
        "outcome": "DUPLICATE", "original_outcome": existing.outcome,
        "event_id": existing.external_id, "shipment": snapshot(shipment),
        "message": "Identical retry: state was not changed.",
    }, 200
