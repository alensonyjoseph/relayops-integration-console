# Three-minute hiring-manager walkthrough

**0:00–0:25 — Business problem**

"Partner APIs retry and occasionally send inconsistent or delayed events. Without idempotency and transition checks, the same shipment can be updated twice or moved into an impossible state."

**0:25–0:50 — Stack and product**

Show the operations dashboard: Flask REST backend, PostgreSQL state, SQLAlchemy migrations, React/TypeScript interface. Explain that the browser workspace is synthetic and scoped, not authenticated.

**0:50–1:25 — Happy path**

In Event laboratory, select Valid transition and run. Open the HTTP trace. Show 201 and the updated shipment.

**1:25–2:10 — Regression witness**

Select Identifier collision. Show valid 201 followed by 409 for a modified payload with the same event ID. Open the diagnostics screen and identify the naive deduplication bug.

**2:10–2:40 — Verification**

Open \`backend/tests/test_processing.py\`, show the regression test. Point to PostgreSQL uniqueness and row lock logic. Show GitHub Actions CI outcome — only if it has actually passed.

**2:40–3:00 — Trade-offs**

"To keep this portfolio demonstration inspectable I avoided queues, AI calls and proprietary datasets. In production I would add authenticated tenants, webhook signatures, retention and rate limits."

This script should be adapted to whatever the deployed project and actual CI status confirm. Never claim an unavailable API is working.
