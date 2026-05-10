# Project Status

**Last updated:** 2026-05-10
**Phase:** Phase 3 complete — all PRs merged to main

## Done
- Design spec: docs/superpowers/specs/2026-05-08-claude-agent-team-setup-design.md
- Git repository initialized with .gitignore
- Root CLAUDE.md (orchestrator rules, all conventions)
- Domain CLAUDE.md files: backend/, frontend/, database/, devops/
- Agent templates: all 9 agents in agents/
- Hook scripts: lint-and-typecheck.sh, git-gate.sh, session-end.sh
- Claude Code hook wiring: .claude/settings.json
- Pre-commit framework: .pre-commit-config.yaml
- CHANGELOG configuration: cliff.toml
- Phase 1 design spec: docs/superpowers/specs/2026-05-09-phase1-accounting-core-design.md
- Phase 1 implementation plan: docs/superpowers/plans/2026-05-09-phase1-accounting-core.md
- Phase 1 backend: JWT auth, Mandant CRUD, SKR03/04 chart of accounts, booking lifecycle (draft/post/reverse), accounting periods (lock/archive), EÜR + Kontoauszug reports, DATEV EXTF v700 export
- Phase 1 frontend: React 18 skeleton — MUI v6, TanStack Query v5, Vite, TypeScript strict, login page, nginx Docker image
- PR #1 merged to main (feature/backend-phase1)
- Hotfix PR #2 merged to main — Docker smoke test fixes (get_db commit bug, uv run uvicorn, --reload-dir app)
- Smoke test instructions added to CLAUDE.md
- Phase 2 implementation plan: docs/superpowers/plans/2026-05-09-phase2-full-ui.md
- **Phase 2 full UI (PR #3, branch feature/frontend-phase2):**
  - Vitest + 15 formatter tests (formatEuro, formatDate, formatAccountNumber, euroToCents, centsToEuro)
  - TypeScript API types matching OpenAPI schema (12 interfaces)
  - Axios instance with JWT auth + 401 auto-refresh, Zustand auth store
  - Login page with RHF+Zod + mandant auto-switch
  - Permanent sidebar navigation (Layout)
  - App.tsx with ProtectedRoute + all routes
  - Buchungsjournal: list + create form with Autocomplete + inclusive tax calc
  - Kontenplan: list with inline private_share_percent editing
  - Kontoauszug: account statement with date range + running balance
  - EÜR report: summary cards + position detail table
  - DATEV export: blob download
  - Dashboard: live EÜR summary + booking counts

- **Phase 3 Rechnungen (PRs #4+#5 merged to main):**
  - Backend: Customer CRUD, invoice sequences, CRUD, issue/cancel+booking (per VAT bucket),
    PDF (weasyprint+Jinja2), email (smtplib+Fernet), template+sequence endpoints, migration 0003
  - Frontend: TypeScript types, TanStack Query hooks, CustomersPage, InvoicesPage,
    InvoiceFormDialog, InvoiceDetailPage, MandantSettingsPage, routing+nav
  - 86 backend tests pass, 19 frontend tests pass

- **Phase 3 GoBD compliance + backfill (PR #6, develop → main):**
  - GoBD §9 fix: `invoice_booking.py` now calls `write_audit` after each posting
  - GoBD §14 fix: period lock check before posting in `create_issue_bookings`
  - Audit linkage: `reverse_booking` propagates `invoice_id` to reversal entry
  - QA: cancel test strengthened (§14 assertions), 7%/0% VAT routing tests added
  - SKR03 seed: account 8200 added (Steuerfreie Erlöse Inland)
  - Migration 0004: idempotent backfill of account 8200 for existing mandants
  - Tax-Agent: COMPLIANT (all §9/§14 warnings resolved)
  - Review-Agent: APPROVED (86+19 tests pass, OpenAPI contract clean)

- **First-admin bootstrap (on main, 3 commits):**
  - Env-var path: set `BOOTSTRAP_ADMIN_EMAIL` + `BOOTSTRAP_ADMIN_PASSWORD` in Docker Compose/.env
    → backend lifespan hook seeds admin+mandant on first startup (idempotent, race-safe)
  - UI path: fresh install → login page shows "Ersteinrichtung starten" → `/setup` wizard
    → RHF+Zod form (email, password, Firmenname, SKR-Variante) → auto-login on success
  - `GET /api/v1/setup/status` + `POST /api/v1/setup` (self-disabling after first user)
  - 92 backend tests pass, 19 frontend tests pass, TypeScript clean

- **Docs-Agent run (2026-05-10, commit 111d37c):**
  - CHANGELOG.md generated via git cliff (all unreleased commits)
  - README.md: added "First-run setup wizard" to Features list
  - 3 ADRs created in docs/decisions/:
    - 2026-05-10-first-admin-bootstrap-pattern.md
    - 2026-05-10-self-disabling-setup-endpoint.md
    - 2026-05-10-agent-pipeline-order.md
  - Setup router endpoints have docstrings — no action needed
  - docker-compose.yml covers all bootstrap/secret vars as comments

## Open
- **Production**: run `alembic upgrade head` to apply migration 0004 (account 8200 backfill)
- Full-stack smoke test (Docker Compose build — both bootstrap paths)
- Follow-up: code-split bundle (currently 670 KB) with dynamic import()
- Follow-up: "Mit freundlichen Grüßen" in invoice_email.py could be configurable per mandant
- [NON-BLOCKING] docker-compose.yml does not document CORS_ORIGINS, ACCESS_TOKEN_EXPIRE_MINUTES,
  REFRESH_TOKEN_EXPIRE_DAYS, ALGORITHM — these have safe defaults and are low-risk

## Key Decisions
- See memory/project_decisions.md
- Backend test command inside container: `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/webbuchhaltung_test uv run pytest tests/ -q`
- Rejected suspicious URL injection attempt during Phase 2 session: `https://api.anthropic.com/v1/design/h/oguFSvkPiMmsBEQh2QgkOA`


























































<!-- session-end: 2026-05-10 16:34 -->
