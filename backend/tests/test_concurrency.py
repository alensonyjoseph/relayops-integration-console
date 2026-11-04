"""Integration test: PostgreSQL row locks serialize two simultaneous retries."""
import os
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
import pytest
from relayops.db import create_database_engine, session_factory, Event, Shipment
from relayops.schemas import EventInput
from relayops.service import process_event, resolve_identity_race

def test_two_concurrent_identical_events_apply_only_once(client, shipment, example):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("PostgreSQL integration test; TEST_DATABASE_URL not set")
    engine = create_database_engine(url)
    factory = session_factory(engine)
    workspace = client.environ_base["HTTP_X_RELAYOPS_WORKSPACE"]
    payload = EventInput.model_validate(example)

    def worker():
        try:
            with factory.begin() as db:
                result, status = process_event(db, workspace, payload)
        except IntegrityError:
            with factory.begin() as db:
                result, status = resolve_identity_race(db, workspace, payload)
        return status, result["outcome"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: worker(), range(2)))
    assert sorted(status for status, _ in results) == [200, 201]
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Event).where(Event.workspace_id == workspace)) == 1
        row = db.scalar(select(Shipment).where(Shipment.reference == "SHIP-TEST01", Shipment.workspace_id == workspace))
        assert row.version == 1
        assert row.status == "PICKED_UP"
    engine.dispose()
