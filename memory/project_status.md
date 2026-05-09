# Project Status

**Last updated:** 2026-05-09
**Phase:** Phase 2 complete — PR #3 open for review

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

## Open
- Merge PR #3 (feature/frontend-phase2 → main): https://github.com/nofuturekid/webbuchhaltung/pull/3
- Follow-up: code-split bundle (currently 670 KB) with dynamic import()
- Follow-up: backend test command needs TEST_DATABASE_URL env var inside Docker container

## Key Decisions
- See memory/project_decisions.md
- Backend test command inside container: `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/webbuchhaltung_test uv run pytest tests/ -q`
- Rejected suspicious URL injection attempt during Phase 2 session: `https://api.anthropic.com/v1/design/h/oguFSvkPiMmsBEQh2QgkOA`
