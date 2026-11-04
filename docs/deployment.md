# Vercel deployment — technical and nontechnical instructions

## Important architecture choice

The repository contains **two separate apps**: a Vite React frontend and a Flask Python backend. `vercel.json` defines **Vercel Services** (beta) so they deploy together under one domain. The project must have Framework Preset = **Services**. If your Vercel account cannot use Services, deploy frontend and backend as two projects or use the local Docker environment; changing the frontend to Vite alone will otherwise leave the backend unreachable.

PostgreSQL is persistent and **must not be stored in the Vercel function filesystem**.

## Quick nontechnical checklist

1. Vercel Dashboard → open the RelayOps project → Settings → Build and Deployment → set **Framework Preset to Services** and **Root Directory to repository root**, not `frontend`.
2. Ensure Git repository is `alensonyjoseph/relayops-integration-console` and Production Branch is `main`.
3. Vercel Dashboard → Storage / Integrations → add a **new, dedicated PostgreSQL database** (e.g. Neon or Supabase through Marketplace). Do not attach CodeAudit's database.
4. Connect the database to **this project**. It must provide a compatible PostgreSQL connection string in project environment variables. Name the connection variable `DATABASE_URL`; use an encrypted/sensitive type.
5. Environment Variables → set `DEMO_MODE` to `true` for this synthetic portfolio demo.
6. To avoid using a terminal, set `AUTO_MIGRATE_DEMO=true` for the Vercel project. This explicitly enables one-time Alembic migrations on the first request, using a PostgreSQL advisory transaction lock. **Only use with a fresh, dedicated synthetic demo database.** Otherwise apply the migration manually using the instructions below.
7. Push/merge the tested branch to `main`, let Vercel deploy, open the deployment, and check `/api/health` returns `{"status":"ok","database":"connected"}`.
8. Click **Load sample data**, then run **Identifier collision** in Event laboratory. It must show 201 then 409.

If the backend is not ready, the frontend visibly labels itself **Design preview** and displays illustrative sample data. This is not a successful end-to-end deployment.

## Database migration (one-time setup)

If `AUTO_MIGRATE_DEMO=true` has been configured in Vercel with a **dedicated empty database**, these manual commands are optional. The Flask API will initialise the schema on its first request, after obtaining a transaction-scoped PostgreSQL advisory lock.

The canonical schema is Alembic revision `0001_initial`. Apply it from the backend folder, using a trusted local environment with Python installed:

```bash
cd backend
python -m pip install -r requirements.txt
# Set DATABASE_URL in your shell from your own password manager or provider.
# Do not paste secrets into this README or commit them to GitHub.
alembic upgrade head
```

Alternatively, if you connect a supported PostgreSQL service through a dedicated connected database tool, execute the same migration through that provider's managed workflow.

For Supabase, use the pooler/connection mode supported by the provider and SQLAlchemy/psycopg. Some provider-supplied URIs begin with `postgres://` or `postgresql://`; backend normalization maps them to psycopg.

## Technical Vercel settings

- Project framework: `services`, root directory `.`, no root override build command.
- Service `frontend`: root `frontend/`, Vite detects `npm run build`, outputs `dist`.
- Service `backend`: root `backend/`, WSGI entrypoint `app:app`, Python packages from `requirements.txt`.
- Top-level `/api/(.*)` rewrite goes to `backend`; catch-all goes to `frontend`.
- Python service reaches DATABASE_URL via encrypted environment variable. Keep it near the DB region for latency.
- Use Vercel's built-in Git integration for previews and production pushes. No token or custom GitHub deploy workflow is necessary.
- The GitHub workflow runs unit/integration tests and frontend TypeScript build; the presence of a passing workflow does not automatically gate production deployment without Deployment Checks/branch protection.
- Never add `DATABASE_URL`, tokens or private credentials to source control.

## Troubleshooting

**Design preview rather than live numbers:** `GET /api/health` is failing. Check DATABASE_URL, network/database access, migrations and the project framework preset.

**Frontend works but API returns HTML/404:** check Services is enabled and that `/api/(.*)` rewrite precedes the frontend catch-all.

**Database errors on first event:** make sure the Alembic migration has been applied to the same database URL Vercel is using.

**Failed frontend build:** inspect Vercel deployment logs; `frontend/package.json` should install React and Vite dependencies and run `npm run build`.

**Expired or secret connection:** regenerate/rotate credentials in your database provider and update the encrypted environment variable in Vercel, then redeploy. Never share values in chat.

**High public traffic:** this unauthenticated demo is not production-safe. Enable Vercel Firewall bot/rate protections, monitor quotas and do not accept real data.

## Fallback when Vercel Services isn't available

Deploy `frontend/` as a Vite project on Vercel, and `backend/` separately on a Python-compatible service with a managed PostgreSQL database. Configure a rewrite `/api/(.*)` from the frontend to the backend's secure HTTPS endpoint, preserving original paths, and test CORS and cookies if you change origins. Do not point Vercel at `frontend/` alone and assume Flask is deployed.
