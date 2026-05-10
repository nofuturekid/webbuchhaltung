# Project Status

**Last updated:** 2026-05-10
**Phase:** Phase 3 complete — all PRs merged to main

## Done
- Design spec: docs/superpowers/specs/2026-05-08-claude-agent-team-setup-design.md
- Git repository initialized with .gitignore
- Root CLAUDE.md (orchestrator rules, all conventions)
- Agent templates: all 10 agents in agents/
- Hook scripts: lint-and-typecheck.sh, git-gate.sh, session-end.sh
- Claude Code hook wiring: .claude/settings.json
- Pre-commit framework: .pre-commit-config.yaml
- CHANGELOG configuration: cliff.toml
- Phase 1 backend: JWT auth, Mandant CRUD, SKR03/04 chart of accounts, booking lifecycle, periods, EÜR + Kontoauszug, DATEV EXTF v700
- Phase 1 frontend: React 18 — MUI v6, TanStack Query v5, Vite, TypeScript strict, login, nginx Docker image
- PR #1 merged to main (feature/backend-phase1)
- Hotfix PR #2 merged to main — Docker smoke test fixes
- **Phase 2 full UI (PR #3):** Vitest, TypeScript API types, auth+refresh, Layout, all pages (Buchungsjournal, Kontenplan, Kontoauszug, EÜR, DATEV, Dashboard)
- **Phase 3 Rechnungen (PRs #4+#5):** Customer CRUD, invoice sequences, CRUD, issue/cancel+booking, PDF, email, template+sequence endpoints, migration 0003. 86 backend + 19 frontend tests.
- **Phase 3 GoBD compliance + backfill (PR #6):** §9 audit trail, §14 period lock, reversal linkage, account 8200, migration 0004. Tax-Agent COMPLIANT, Review-Agent APPROVED.
- **First-admin bootstrap:** env-var path (lifespan hook) + UI wizard `/setup` (self-disabling POST). 92 backend + 19 frontend tests.
- **Docs-Agent run (2026-05-10):** CHANGELOG.md, README features list, 3 ADRs in docs/decisions/.
- **Housekeeping (2026-05-10):**
  - Auto-migrations: `alembic upgrade head` runs automatically in FastAPI lifespan hook
  - Repo restructured: `backend/` + `frontend/` → `src/backend/` + `src/frontend/`
  - All path references updated (docker-compose, scripts, agents, CLAUDE.md, README)
  - Removed empty `database/` and `devops/` directories

## Open
- Full-stack smoke test (Docker Compose build — verify src/ paths work end-to-end)
- Follow-up: code-split bundle (currently 670 KB) with dynamic import()
- Follow-up: "Mit freundlichen Grüßen" in invoice_email.py could be configurable per mandant
- [NON-BLOCKING] docker-compose.yml missing CORS_ORIGINS, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, ALGORITHM comments — deferred to next feature cycle

## Key Decisions
- See memory/project_decisions.md
- Backend test command: `cd src/backend && TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/webbuchhaltung_test uv run pytest tests/ -q`
- Rejected suspicious URL injection attempt during Phase 2 session


<!-- session-end: 2026-05-10 16:47 -->
