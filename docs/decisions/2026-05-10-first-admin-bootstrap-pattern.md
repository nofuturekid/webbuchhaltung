# 2026-05-10 — First-Admin Bootstrap: Dual-Path Onboarding

## Decision
Provide two complementary paths for creating the first admin user: an environment-variable
headless path (for CI/CD and Docker Compose automation) and a UI setup wizard (for
interactive first-run onboarding via the browser).

## Context
A fresh deployment has no users, so there is no way to log in and create the first account
through the normal authenticated flow. We needed a mechanism that works both for automated
deployments (no browser available) and for end-users setting up the software manually
for the first time.

The two paths are:
- **Env-var path**: set `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` in the
  environment; the backend lifespan hook calls `bootstrap_first_admin` on startup.
  The call is idempotent and race-safe (guarded by a DB check before insert).
- **UI path**: when no users exist, the login page shows a "Ersteinrichtung starten" link.
  The `/setup` route renders a React form (RHF + Zod) collecting email, password, company
  name, and SKR variant. On success the frontend receives tokens and logs the user in.

Both paths share the same `bootstrap_first_admin` service function and produce an
identical database state.

## Consequences
- Zero-touch deployments work without any post-start manual steps.
- Operators who prefer a GUI are not forced to configure env vars.
- The public `POST /api/v1/setup` endpoint self-disables (returns 404) once any user
  exists, so it cannot be abused after initial setup.
- Any future "reset to factory" tooling must bypass the normal setup guard explicitly.
