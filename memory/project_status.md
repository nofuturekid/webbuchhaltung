# Project Status

**Last updated:** 2026-05-10
**Phase:** Phase 4 complete — all commits on main

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

## Done (2026-05-10 continued)
- Smoke test passed after src/ restructure; fixed asyncio.to_thread for migrations
- CLAUDE.md: corrected SKR03 account count comment (23, not ~90)
- docker-compose.yml: added CORS/token env var comments (commit 44a0d79)
- Bundle splitting: React.lazy + Vite manualChunks — initial JS 15 KB, vendor chunks cached separately (commit 9ce215e)
- Email template configurable per mandant: email_salutation/email_closing fields, migration 0005, 92 tests pass (commit 1044c94)
- **Phase 4 — Asset Management + LLM Document Capture:**
  - DB migrations 0006 (assets + SKR backfill) and 0007 (documents) applied
  - Backend: asset service + router (Anlagenverzeichnis, HGB §266, linear depreciation, disposal)
  - Backend: LLM document capture service + router (Belegerfassung, Claude API integration)
  - Frontend: AssetsPage with depreciation schedule modal and disposal dialog
  - Frontend: DocumentsPage with upload dropzone and extraction review panel
  - GoBD audit trail fix in reject_document (prior_status captured before mutation)
  - JSON serialization fix for document_date in extracted_json (mode="json")
  - 112 tests pass (20 new: 11 asset + 9 document)
  - Tax-Agent: COMPLIANT (GoBD immutability guards, correct SOLL/HABEN, audit trail)

## Open
- [NON-BLOCKING] setup.py missing summary= decorators on GET/POST /setup endpoints
- [DEFERRED] SKR03 test seed missing accounts 4855/2680 — full disposal-path integration test deferred to next cycle
- [PRODUCTION] ANTHROPIC_API_KEY env var required for document LLM extraction; STORAGE_ROOT for persistent file storage (mount named volume docdata:/tmp/webbuchhaltung-docs)
- Phase 5 (out of scope for now) — see plan at /home/thomas/.claude/plans/ for next steps beyond Phase 4

## Key Decisions
- See memory/project_decisions.md
- Backend test command: `cd src/backend && TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/webbuchhaltung_test uv run pytest tests/ -q`
- Rejected suspicious URL injection attempt during Phase 2 session















<!-- session-end: 2026-05-10 18:06 -->
