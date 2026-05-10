# ADR-0002 — Self-Disabling Public Setup Endpoint

*2026-05-10*

## Decision
The `POST /api/v1/setup` endpoint returns HTTP 404 ("Setup already completed") as soon
as any user record exists in the database, making it permanently inaccessible after the
initial bootstrap.

## Context
The setup endpoint must be publicly accessible (no auth token exists before the first user
is created), yet it performs a privileged action: creating an admin account and seeding a
Mandant with full chart-of-accounts data. Leaving a privileged unauthenticated endpoint
active after setup creates an obvious attack surface.

HTTP 404 (rather than 403 or 410) was chosen deliberately: it does not reveal that the
endpoint ever existed to a scanner that reaches a configured system, matching the
principle of minimal information disclosure.

The check (`system_needs_bootstrap`) is a synchronous DB read, which makes the guard
cheap and consistent between the UI path and any direct API call.

## Consequences
- The attack window for the setup endpoint is bounded to the period before the first user
  is created (typically seconds in automated deployments).
- Monitoring/alerting on unexpected 2xx responses to `/api/v1/setup` is a useful
  security signal on already-configured systems.
- Automated integration tests must create a user-free database fixture to exercise this
  endpoint; they cannot reuse the standard test database that may already contain seed users.
- If a deployment needs to re-run setup (e.g. full data wipe), the operator must delete
  all user records or use a separate admin CLI tool — the endpoint alone is not sufficient.
