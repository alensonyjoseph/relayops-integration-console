# Architecture and reliability decisions

## Scope

RelayOps is a bounded, synthetic integration console. It demonstrates engineering judgement around a common API failure mode: duplicate event identifiers, altered retry payloads, and out-of-order state transitions.

### Runtime topology

- **Browser:** React + TypeScript + Vite frontend.
- **API:** Flask, Pydantic 2 validation, SQLAlchemy 2 sessions, Gunicorn for local containers.
- **Database:** PostgreSQL 16; Alembic revision \`0001_initial\`.
- **Operations:** GitHub Actions runs tests against PostgreSQL. Docker Compose starts the complete local stack.
- **Hosted path:** Vercel Services (beta) routes \`/api/*\` to the Python backend and other paths to Vite. Cloud PostgreSQL is external.

## Request lifecycle

1. Parse and validate request with Pydantic. Invalid input returns 400 before any mutation.
2. Acquire a \`SELECT ... FOR UPDATE\` lock on the shipment row, within a transaction.
3. Search the scoped identity key \`(workspace_id, source, external_id)\`.
4. If found and fingerprint matches: increase replay count, return 200 and do not apply a second transition.
5. If found and fingerprint differs: return 409; the shipment must remain unchanged.
6. If new, check event quota, timestamp ordering, and allowed state transition.
7. Write Event and AuditEntry; if accepted, update Shipment status, version, latest accepted time. The entire transaction commits together.
8. If a concurrent insert races on the unique key, roll back and classify the winner as replay or collision in a fresh transaction.

The unique constraint is a final line of defence. The shipment row lock serialises state transitions for that shipment when using PostgreSQL. SQLite test execution verifies functional behaviour but does not exercise PostgreSQL row locks; the CI PostgreSQL job verifies PostgreSQL compatibility.

## Shipment state graph

\`\`\`text
CREATED ──> PICKED_UP ──> IN_TRANSIT ──> DELIVERED
    │            │
    └────────> CANCELLED <────────────┘ (no route from IN_TRANSIT)
\`\`\`

The diagram's CANCELLED links originate only at CREATED and PICKED_UP. Both DELIVERED and CANCELLED are terminal states. \`occurred_at\` must be later than the latest accepted event timestamp.

## Fingerprint contract

The incoming Pydantic model is normalised as JSON with sorted keys and a UTC ISO-8601 timestamp. SHA-256 produces a deterministic fingerprint of the validated semantic payload. In other words, an equivalent timestamp offset is not incorrectly treated as changed data.

The fingerprint is not a signature. A SHA-256 payload hash is not sender authentication.

## Database

- \`shipments\` holds the current derived status, version and latest accepted event timestamp.
- \`events\` holds external identities, fingerprints, requested status, accepted/rejected result and replay count.
- \`audit_entries\` holds the before/after status decision for each first-seen valid-schema event.

Malformed requests do not create a database audit entry because required identifiers may be absent. Changed-payload identity collisions return 409 without replacing the original event. Future production systems should separately log conflicts in an append-only security/event log without breaking identity uniqueness.

## Security boundaries

This is a deliberately unauthenticated demo with synthetic data only. Each browser gets a random workspace UUID which scopes queries and writes. This is **not access control** and must not be used for customer data. The demo has a maximum of 25 shipments and 350 first-seen events per workspace. It currently does not enforce global rate limits or automatic workspace retention cleanup. Put a hosted demo behind Vercel Firewall and monitor usage.

## Known limitations

- Carrier signatures are not verified.
- Time ordering uses partner-reported timestamps; an authenticated production sender is assumed.
- Two shipments in the same workspace can share source IDs only if the external ID is unique across that source; a deliberate modelling choice.
- Transactional retries under heavy contention could use exponential backoff.
- Replays increment an in-row counter rather than creating separate audit records.
- No global workspace quota prevents unlimited anonymous workspace creation.
- No identity or RBAC system is present.
