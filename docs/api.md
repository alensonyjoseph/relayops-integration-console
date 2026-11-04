# REST API contract

All endpoints start with \`/api\`. Send \`X-RelayOps-Workspace: <UUID>\` on every endpoint except health. The frontend generates and stores a UUID automatically. It is **demo isolation, not authentication**.

\`GET /api/health\` — returns \`{"status":"ok","database":"connected"}\`, or HTTP 503 when database setup is incomplete.

\`GET /api/metrics\` — \`{"shipments":0,"accepted":0,"rejected":0,"duplicates":0,"processed":0}\`.

\`GET /api/shipments\` — scoped shipment list.
\`POST /api/shipments\` — accepts JSON \`{"reference":"SHIP-EXAMPLE01","partner":"Example Freight"}\`; returns 201.

\`GET /api/shipments/<reference>\` — shipment, events and before/after audit decisions.

\`POST /api/events\` — accepts:

\`\`\`json
{
  "source": "carrier_alpha",
  "event_id": "evt-001",
  "shipment_ref": "SHIP-EXAMPLE01",
  "status": "PICKED_UP",
  "occurred_at": "2026-11-04T10:00:00Z"
}
\`\`\`

\`source\` is lowercase, \`status\` is one of PICKED_UP / IN_TRANSIT / DELIVERED / CANCELLED, and \`occurred_at\` must include timezone information.

Response codes:
- 201 accepted new event, state changed;
- 200 identical event replay, no second state mutation;
- 409 identity reused with different payload;
- 422 transition forbidden or timestamp stale;
- 400 malformed JSON, missing/invalid fields, or workspace UUID missing;
- 404 unknown shipment;
- 429 per-workspace demo quota reached;
- 503 database unconfigured/unavailable.

\`GET /api/events?outcome=REJECTED&limit=50\` — latest events, optionally filtered.

\`POST /api/demo/seed\` — populates six fictional shipments and events, once per workspace.
\`POST /api/demo/reset\` — deletes all synthetic records for the request's workspace. Both require \`DEMO_MODE=true\`.

No PII, secrets or real logistics records should ever be submitted to this public demonstration.
