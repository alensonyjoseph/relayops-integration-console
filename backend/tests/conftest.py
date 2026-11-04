import os
import uuid
import pytest
from relayops.api import create_app
from relayops.db import Base, create_database_engine

@pytest.fixture()
def client(tmp_path):
    # TEST_DATABASE_URL enables real PostgreSQL tests in GitHub Actions.
    # Use a distinct sqlite file for each unit test when no PostgreSQL is supplied.
    url = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_database_engine(url)
    Base.metadata.create_all(engine)
    app = create_app(url)
    app.config["TESTING"] = True
    with app.test_client() as client:
        client.environ_base["HTTP_X_RELAYOPS_WORKSPACE"] = str(uuid.uuid4())
        yield client
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture()
def example():
    return {
        "source": "carrier_alpha", "event_id": "evt-001",
        "shipment_ref": "SHIP-TEST01", "status": "PICKED_UP",
        "occurred_at": "2026-11-04T10:00:00Z",
    }

@pytest.fixture()
def shipment(client):
    response = client.post("/api/shipments", json={"reference":"SHIP-TEST01","partner":"Example Carrier"})
    assert response.status_code == 201
    return response.json["shipment"]
