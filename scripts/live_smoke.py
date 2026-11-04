"""Public RelayOps synthetic end-to-end smoke test.

Runs from GitHub Actions against the actual production URL. Uses only standard
library, no credentials, and a fresh random workspace per run.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://relayops-integration-console.vercel.app"

def request(method: str, path: str, data: dict | None = None, workspace: str | None = None):
    headers = {"Accept": "application/json", "User-Agent": "RelayOps-GitHub-CI-Smoke/1"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if workspace:
        headers["X-RelayOps-Workspace"] = workspace
    payload = json.dumps(data).encode() if data is not None else None
    req = Request(BASE + path, data=payload, headers=headers, method=method)
    try:
        with urlopen(req, timeout=25) as response:
            status = response.status
            raw = response.read(4096).decode("utf-8", "replace")
    except HTTPError as err:
        status = err.code
        raw = err.read(4096).decode("utf-8", "replace")
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, {"_not_json": raw[:180]}

def expect(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)

def main():
    print("Testing production API:", BASE)
    last_status, last_body = None, None
    for attempt in range(1, 13):
        try:
            status, body = request("GET", "/api/health")
        except (TimeoutError, URLError, OSError) as exc:
            print(f"Health {attempt}/12: network error {type(exc).__name__}")
            time.sleep(8)
            continue
        print(f"Health {attempt}/12: HTTP {status}, response {str(body)[:250]}")
        if status == 200 and body.get("status") == "ok" and body.get("database") == "connected":
            print("PASS: Flask API and Neon PostgreSQL connected")
            break
        last_status, last_body = status, body
        time.sleep(8)
    else:
        raise AssertionError(f"Health never passed: HTTP {last_status} {str(last_body)[:350]}")

    workspace = str(uuid.uuid4())
    reference = "SHIP-LIVE-" + uuid.uuid4().hex[:10].upper()
    status, body = request("POST", "/api/shipments",
                           {"reference": reference, "partner": "RelayOps CI Synthetic Carrier"}, workspace)
    expect(status == 201, f"Create shipment failed: {status} {body}")
    print("PASS: PostgreSQL-backed shipment creation")

    event = {
        "source": "github_ci", "event_id": "live-" + uuid.uuid4().hex[:16],
        "shipment_ref": reference, "status": "PICKED_UP",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    status, body = request("POST", "/api/events", event, workspace)
    expect(status == 201 and body.get("outcome") == "ACCEPTED",
           f"New event failed: {status} {body}")
    print("PASS: HTTP 201 applies valid event")

    status, body = request("POST", "/api/events", event, workspace)
    expect(status == 200 and body.get("outcome") == "DUPLICATE",
           f"Exact retry failed: {status} {body}")
    print("PASS: HTTP 200 replay is idempotent")

    tampered = {**event, "status": "DELIVERED"}
    status, body = request("POST", "/api/events", tampered, workspace)
    expect(status == 409 and body.get("error", {}).get("code") == "EVENT_ID_CONFLICT",
           f"Conflict witness failed: {status} {body}")
    print("PASS: HTTP 409 on conflicting event identity")

    status, body = request("GET", f"/api/shipments/{reference}", workspace=workspace)
    record = body.get("shipment", {})
    expect(status == 200 and record.get("status") == "PICKED_UP" and record.get("version") == 1,
           f"Unexpected final shipment state: {status} {body}")
    print("PASS: persisted shipment state unchanged by retries/conflict")
    print("SUCCESS: Real production API/database end-to-end smoke test passed")

if __name__ == "__main__":
    main()
