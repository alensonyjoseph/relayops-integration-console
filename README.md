<div align="center">
  <img alt="RelayOps logo" src="frontend/public/relay.svg" width="72"/>
  <h1>RelayOps</h1>
  <p><strong>Reliable events. Traceable failures. Verified fixes.</strong></p>
  <p>A production-style engineering portfolio demonstration built with Flask, PostgreSQL, React, TypeScript, SQLAlchemy, Pydantic and Pytest.</p>
</div>

[![CI](https://github.com/alensonyjoseph/relayops-integration-console/actions/workflows/ci.yml/badge.svg)](https://github.com/alensonyjoseph/relayops-integration-console/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)
![React](https://img.shields.io/badge/React-19-61dafb)
![License](https://img.shields.io/badge/license-MIT-1e9c91)

## Why this project exists

Third-party logistics systems retry delivery events, send stale timestamps and sometimes reuse identifiers with changed payloads. A naive integration can acknowledge the wrong change or corrupt a shipment's history.

**RelayOps applies validated and ordered state transitions, persists the result transactionally and produces an auditable rejection reason when an event cannot be accepted.** It is intentionally a bounded portfolio example, not a commercial carrier integration.

### Features

- Validated JSON API with stable 400/404/409/422/429 error responses.
- PostgreSQL shipments, events, audit entries, uniqueness constraints and Alembic migration.
- Canonical-payload SHA-256 fingerprints: exact retries do not reapply state changes.
- Conflicting reuse of the same source + event ID returns HTTP 409.
- Strict event-order checks and a documented shipment state machine.
- Row locking and database-unique constraints for concurrent processing.
- Workspace-scoped synthetic data and predictable sample fixtures.
- React operations console, shipment explorer, event laboratory and diagnostics.
- Pytest regression coverage, PostgreSQL-based CI and TypeScript production build.
- Docker Compose for local reproducibility and Vercel Services configuration.

> **Public demo safety:** RelayOps has no user authentication. All data is fictional. Workspace UUIDs isolate convenience views, **not** secure tenants. Never enter customer data, secrets or sensitive information. Per-workspace caps limit accidental growth; public abuse protection and lifecycle cleanup would be required for a real service.

## Run locally (one command)

Requires Docker and Docker Compose.

\`\`\`bash
git clone https://github.com/alensonyjoseph/relayops-integration-console.git
cd relayops-integration-console
docker compose up --build
\`\`\`

Open **http://localhost:8080**. The Flask API runs on **http://localhost:8000/api/health**. PostgreSQL is automatically started and migrated. Click **Load sample data**, then **Event laboratory**, and run **Identifier collision**.

Stop with Ctrl+C. To remove containers without deleting the persisted local database, run \`docker compose down\`.

### Development without Docker

1. Start a local PostgreSQL 16 instance and create a dedicated empty database.
2. From \`backend/\`, install \`pip install -r requirements-dev.txt\`, export \`DATABASE_URL\`, run \`alembic upgrade head\`, and launch \`python app.py\`.
3. From \`frontend/\`, run \`npm install && npm run dev\`, then open http://localhost:5173.

The Vite development server proxies \`/api\` requests to Flask on port 8000.

### Test

\`\`\`bash
cd backend
python -m pytest -v
python -m ruff check relayops tests
\`\`\`

By default, tests use temporary SQLite databases for portability. GitHub Actions runs the same tests against a real PostgreSQL 16 service and also runs the actual Alembic upgrade. See \`.github/workflows/ci.yml\`.

## The regression proof

Scenario: send \`event_id=evt-001\`, \`status=PICKED_UP\` and then resend the **same identifier** with \`status=DELIVERED\`.

| Action | Expected HTTP | Expected database effect |
|---|---:|---|
| First valid event | 201 | Shipment advances once |
| Exact retry | 200 | No new transition; replay counter increments |
| Same event ID with modified payload | 409 | No state change |
| Stale / invalid transition | 422 | Rejection and audit entry |
| Missing/invalid fields | 400 | No event written |

Source: \`backend/relayops/service.py\`. Regression test: \`test_regression_same_event_id_changed_payload_is_conflict\` in \`backend/tests/test_processing.py\`.

The tests are meant to be run, not merely read; consult the repository's CI checks for verified status.

## Architecture

\`\`\`text
React + TypeScript SPA (Vercel frontend / local Nginx)
       |
       | same-origin /api requests, synthetic workspace UUID
       v
Flask + Pydantic (Vercel Python Service / Gunicorn)
       |
       | schema validation → lock shipment → compare event fingerprint
       |                   → qualify transition → write event + audit
       v
PostgreSQL (managed cloud database / Docker Compose)
\`\`\`

See [architecture](docs/architecture.md), [regression witness](docs/regression-case.md), [API contract](docs/api.md), [Vercel deployment](docs/deployment.md), and [three-minute demo script](docs/demo-script.md).

## Deploy on Vercel

This repository uses **Vercel Services** to deploy two independent runtimes under one domain. Services is a beta feature and must be enabled for the project; \`vercel.json\` defines the routing. The API also needs a **dedicated managed PostgreSQL instance** and one-time migrations. Git integration alone is **not enough** to make PostgreSQL appear.

Read **[docs/deployment.md](docs/deployment.md)** before attempting a hosted release. The frontend has an explicitly labelled **sample-data design preview** when its API is not connected; that preview is not evidence of a working backend.

## Engineering trade-offs

This application intentionally avoids queues, Redis, Kubernetes, authentication frameworks and actual carrier credentials. It demonstrates one concrete reliability problem using inspectable code and tests. For a real multi-tenant system, add authenticated identity, tenant-level permissions, event retention, rate limiting, observability, webhook signature verification and background processing.

## Original work and confidentiality

RelayOps is an independent, synthetic example. It does not contain any SmallSpark Space Systems, Browns & Whites, Dreamloop, CodeAudit, Bending Spoons or other third-party confidential material.

MIT licensed · Built as a software-engineering work sample.
