from copy import deepcopy

def test_happy_path_and_transitions(client, shipment, example):
    first = client.post("/api/events", json=example)
    assert first.status_code == 201
    assert first.json["shipment"]["status"] == "PICKED_UP"
    second = dict(example, event_id="evt-002", status="IN_TRANSIT",
                  occurred_at="2026-11-04T11:00:00Z")
    result = client.post("/api/events", json=second)
    assert result.status_code == 201
    assert result.json["shipment"]["version"] == 2
    details = client.get("/api/shipments/SHIP-TEST01")
    assert details.json["shipment"]["status"] == "IN_TRANSIT"
    assert len(details.json["audit"]) == 2

def test_identical_retry_is_idempotent(client, shipment, example):
    first = client.post("/api/events", json=example)
    replay = client.post("/api/events", json=deepcopy(example))
    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json["outcome"] == "DUPLICATE"
    assert replay.json["shipment"]["version"] == 1
    metrics = client.get("/api/metrics").json
    assert (metrics["accepted"], metrics["duplicates"], metrics["processed"]) == (1, 1, 2)

def test_regression_same_event_id_changed_payload_is_conflict(client, shipment, example):
    """Bug witness: a naive dedupe-by-ID would accept this conflicting retry."""
    assert client.post("/api/events", json=example).status_code == 201
    tampered = dict(example, status="DELIVERED")
    result = client.post("/api/events", json=tampered)
    assert result.status_code == 409
    assert result.json["error"]["code"] == "EVENT_ID_CONFLICT"
    metrics = client.get("/api/metrics").json
    assert metrics["duplicates"] == 0
    assert client.get("/api/shipments/SHIP-TEST01").json["shipment"]["status"] == "PICKED_UP"

def test_stale_event_rejected_and_audited(client, shipment, example):
    assert client.post("/api/events", json=example).status_code == 201
    late = dict(example, event_id="evt-002", status="IN_TRANSIT",
                occurred_at="2026-11-04T09:59:59Z")
    result = client.post("/api/events", json=late)
    assert result.status_code == 422
    assert result.json["reason"] == "STALE_EVENT"
    assert client.get("/api/metrics").json["rejected"] == 1
    assert len(client.get("/api/shipments/SHIP-TEST01").json["audit"]) == 2

def test_invalid_transition(client, shipment, example):
    result = client.post("/api/events", json=dict(example, status="DELIVERED"))
    assert result.status_code == 422
    assert result.json["reason"] == "INVALID_TRANSITION"
    assert result.json["shipment"]["status"] == "CREATED"

def test_invalid_payload_and_unknown_fields(client, shipment, example):
    invalid = dict(example, source="carrier_alpha", occurred_at="2026-11-04T10:00:00")
    assert client.post("/api/events", json=invalid).status_code == 400
    invalid = dict(example, secret_field="unrecognized")
    assert client.post("/api/events", json=invalid).status_code == 400

def test_scope_isolation(client, shipment, example):
    assert client.post("/api/events", json=example).status_code == 201
    old_workspace = client.environ_base["HTTP_X_RELAYOPS_WORKSPACE"]
    client.environ_base["HTTP_X_RELAYOPS_WORKSPACE"] = "9d7ca74f-3fd6-4738-9e03-6bd2b63ab5c5"
    assert client.get("/api/metrics").json["shipments"] == 0
    assert client.post("/api/events", json=example).status_code == 404
    client.environ_base["HTTP_X_RELAYOPS_WORKSPACE"] = old_workspace

def test_missing_workspace_rejected(client):
    client.environ_base.pop("HTTP_X_RELAYOPS_WORKSPACE", None)
    assert client.get("/api/metrics").status_code == 400

def test_seed_reset(client):
    assert client.post("/api/demo/seed").status_code == 200
    metrics = client.get("/api/metrics").json
    assert metrics["shipments"] == 6
    assert metrics["rejected"] == 1
    assert client.post("/api/demo/seed").json["created_shipments"] == 0
    assert client.post("/api/demo/reset").status_code == 200
    assert client.get("/api/metrics").json["shipments"] == 0

def test_bad_filters(client, shipment):
    assert client.get("/api/events?outcome=BOGUS").status_code == 400
    assert client.get("/api/events?limit=x").status_code == 400
