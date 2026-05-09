# Project Status

**Last updated:** 2026-05-09
**Phase:** Phase 1 design complete — ready for implementation planning

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

## In Progress
- Nothing

## Open
- Phase 1 implementation plan (invoke writing-plans skill)
- Phase 1 implementation (accounting core MVP)

## Key Decisions (this session)
- SQLite dropped — PostgreSQL + MariaDB only; Docker Compose = minimum deployment
- Multi-Mandant from day one; mandant_id always from JWT, never from request body
- Booking model: flat single table (Approach A) with booking_type enum
- JWT auth in Phase 1 (basic, no OAuth/RBAC)
- Phase 1 = backend API + Docker Compose + React skeleton only (no Tier 1, no full UI)

## Key Decisions
- See memory/project_decisions.md






















<!-- session-end: 2026-05-09 10:29 -->
