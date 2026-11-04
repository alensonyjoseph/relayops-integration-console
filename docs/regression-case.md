# Regression case 001 — changed payload, reused event ID

## The bug

A naive integration uses \`(source, event_id)\` as its sole deduplication rule:

\`\`\`python
if event_id in processed_ids:
    return {"ok": True}  # Wrong if payload changed on retry.
\`\`\`

This conflates two distinct cases: an exact retry and a conflicting reuse of an identifier.

## Minimal reproducer

Create shipment \`SHIP-TEST01\`. Submit:

\`\`\`json
{"source":"carrier_alpha","event_id":"evt-001","shipment_ref":"SHIP-TEST01","status":"PICKED_UP","occurred_at":"2026-11-04T10:00:00Z"}
\`\`\`

Then submit **the same source and event ID** but change \`status\` to \`DELIVERED\`.

### Naive observed error

A naive ID-only implementation would treat the conflicting second request as an accepted duplicate, hiding the changed payload.

### Correct behaviour

RelayOps hashes canonical validated payloads. A matching identity with a different hash returns HTTP \`409\` with \`EVENT_ID_CONFLICT\`. Shipment state remains \`PICKED_UP\` and version remains \`1\`.

For exact identical retries, return \`200\` with \`DUPLICATE\` and no second transition.

## Executable verification

\`backend/tests/test_processing.py::test_regression_same_event_id_changed_payload_is_conflict\` performs the real two-request witness and asserts the 409, reason code, unchanged state and unchanged replay count.

Related tests cover exact retries, stale events, invalid transitions, schema validation and workspace isolation.

This documentation is a description of the intended behaviour. Test success must be established by actually running Pytest / reviewing CI.
