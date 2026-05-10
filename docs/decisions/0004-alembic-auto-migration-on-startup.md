# ADR-0004 — Alembic Auto-Migration on Startup

*2026-05-10*

## Decision
Run `alembic upgrade head` automatically inside the FastAPI lifespan hook so that
database migrations apply on every container start without a manual step.

## Context
During the housekeeping cycle (2026-05-10), the deployment flow was simplified to
`docker compose up --build -d` with no separate migration step. Without auto-migration,
operators must remember to run `alembic upgrade head` after every deploy, which is
error-prone and breaks zero-touch CI/CD environments.

The lifespan hook (FastAPI's `@asynccontextmanager` startup/shutdown mechanism) runs
once before the server accepts requests, making it a reliable injection point. The
call is idempotent: Alembic is a no-op when the database is already at head.

## Consequences
- Fresh deployments and upgrades require no manual migration step — the backend
  self-heals on startup.
- Horizontal scaling (multiple backend replicas starting simultaneously) can cause
  concurrent migration runs. Alembic uses advisory locks on PostgreSQL, so this is safe;
  on MariaDB/MySQL, the metadata table lock provides equivalent protection.
- Local development outside Docker still requires `uv run alembic upgrade head` manually
  (documented in DEVELOPMENT.md) because the lifespan hook only runs when the app starts.
- Downgrade migrations (`alembic downgrade -1`) remain a manual operator action —
  automatic rollback on startup is intentionally not implemented.
