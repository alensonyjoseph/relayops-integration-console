"""Deterministic synthetic dataset. Never references actual customers or employers."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from .db import Shipment
from .schemas import EventInput
from .service import process_event

DEMO_SHIPMENTS = [
    ("SHIP-2048", "Northstar Freight"),
    ("SHIP-2049", "Meridian Express"),
    ("SHIP-2050", "Atlas Cargo"),
    ("SHIP-2051", "Northstar Freight"),
    ("SHIP-2052", "Helio Logistics"),
    ("SHIP-2053", "Meridian Express"),
]
def populate_demo(session, workspace: str) -> int:
    if session.scalar(select(Shipment.id).where(Shipment.workspace_id == workspace).limit(1)):
        return 0
    for ref, partner in DEMO_SHIPMENTS:
        session.add(Shipment(workspace_id=workspace, reference=ref, partner=partner))
    session.flush()
    baseline = datetime.now(timezone.utc) - timedelta(days=3)
    for n, (ref, _) in enumerate(DEMO_SHIPMENTS[:5]):
        sequence = ["PICKED_UP", "IN_TRANSIT", "DELIVERED"] if n == 0 else (
            ["PICKED_UP", "IN_TRANSIT"] if n in (1, 2) else ["PICKED_UP"]
        )
        for i, status in enumerate(sequence):
            data = EventInput(source="demo_carrier", event_id=f"seed-{n}-{i}",
                              shipment_ref=ref, status=status,
                              occurred_at=baseline + timedelta(hours=n * 5 + i * 2))
            process_event(session, workspace, data)
    # A late update is rejected but remains visible in diagnostics.
    process_event(session, workspace, EventInput(source="demo_carrier", event_id="seed-stale",
        shipment_ref="SHIP-2048", status="PICKED_UP",
        occurred_at=baseline - timedelta(hours=1)))
    return len(DEMO_SHIPMENTS)
