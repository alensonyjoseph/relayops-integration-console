"""Opt-in migration makes a newly connected synthetic demo work without manual CLI setup."""
import uuid

from relayops.api import create_app

def test_auto_migrate_initializes_fresh_database(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("AUTO_MIGRATE_DEMO", "true")
    url = f"sqlite:///{tmp_path / 'fresh-demo.sqlite'}"
    app = create_app(url)
    app.testing = True
    with app.test_client() as client:
        health = client.get("/api/health")
        assert health.status_code == 200, health.get_json()
        assert health.json["database"] == "connected"
        workspace = str(uuid.uuid4())
        first = client.get("/api/metrics", headers={"X-RelayOps-Workspace": workspace})
        assert first.status_code == 200
        assert first.json["shipments"] == 0
        # No additional migration is attempted on subsequent requests in this instance.
        second = client.get("/api/health")
        assert second.status_code == 200
