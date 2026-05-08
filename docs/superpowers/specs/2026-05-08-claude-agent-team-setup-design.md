# Claude Code Agent-Team Setup — Design Spec
**Date:** 2026-05-08
**Project:** WebBuchhaltung (German accounting software)
**Status:** Approved

---

## Overview

This document describes the Claude Code agent-team setup for WebBuchhaltung. The goal is a structured multi-agent environment where specialized sub-agents are coordinated by an orchestrator, triggered automatically via hooks, and persist their results across sessions.

---

## Tech Stack

| Area | Technology |
|------|------------|
| Backend | FastAPI, Python, SQLAlchemy, Alembic |
| Frontend | React, TypeScript, Vite |
| Databases | PostgreSQL (production), MariaDB (legacy import), SQLite (tests/offline) |
| Infrastructure | Docker, Kubernetes |
| CI/CD | GitHub Actions, GitLab CI |
| Tax law | Germany — HGB, GoBD, UStG, DATEV SKR03/SKR04 |

---

## Architecture Decisions

**Model:** Hybrid — Orchestrator + parallel Git worktrees
- A root orchestrator coordinates and delegates
- Critical paths (backend + frontend) run in parallel in isolated worktrees
- Hooks (shell scripts) act as sensors; orchestrator-Claude acts as reaction logic

**CLAUDE.md strategy:** Modular hierarchy
- Root `CLAUDE.md` = orchestrator rules, project overview, delegation logic
- Domain-specific `CLAUDE.md` in source directories (auto-loaded by context)
- Agent prompt templates in `agents/*.md` (manually loaded by orchestrator)

**Trigger model:** Hook-based automatic
- `PostToolUse` hooks invoke shell scripts (linters, security scanners, type checkers)
- Orchestrator reads hook output and decides whether to spawn a sub-agent
- Security and Tax agents are hard gates (block on finding)

---

## Directory Structure

```
WebBuchhaltung/
├── CLAUDE.md                        # Orchestrator: delegation rules, conventions, memory protocol
├── .claude/
│   ├── settings.json                # Hooks, permissions
│   └── state/                       # Agent state between sessions (not versioned)
│       ├── backend-current.md
│       ├── frontend-current.md
│       └── ...
├── agents/                          # Agent prompt templates (loaded by orchestrator)
│   ├── backend.md
│   ├── frontend.md
│   ├── database.md
│   ├── devops.md
│   ├── qa.md
│   ├── security.md
│   ├── tax.md
│   ├── data-exchange.md
│   └── review.md
├── memory/                          # Persistent cross-session facts (versioned in git)
│   ├── project_status.md
│   ├── project_decisions.md
│   └── feedback_*.md
├── backend/
│   └── CLAUDE.md                    # FastAPI context, Python patterns
├── frontend/
│   └── CLAUDE.md                    # React context, component patterns
├── database/
│   └── CLAUDE.md                    # Schema context, GoBD requirements
├── devops/
│   └── CLAUDE.md                    # K8s, Docker, CI/CD context
├── scripts/
│   └── hooks/                       # Hook shell scripts
│       ├── lint-and-typecheck.sh    # Ruff/ESLint/tsc after Write/Edit
│       ├── git-gate.sh              # Security + Tax gate before git push
│       └── session-end.sh           # Memory update on Stop event
└── docs/
    ├── decisions/                   # Architecture Decision Records (ADRs)
    └── superpowers/specs/           # Design documents (this directory)
```

---

## Agent Roster

### Orchestrator
**Context:** `CLAUDE.md` (root)
**Responsibilities:**
- Know the project overview and current architecture decisions
- Decide when to spawn which sub-agent
- Create and coordinate worktrees for parallel tasks
- Execute session-start/end protocol
- Respect merge gates (Security, Tax)

### Backend Agent
**Context:** `backend/CLAUDE.md` + `agents/backend.md`
**Responsibilities:**
- FastAPI: router structure, dependency injection, Pydantic schemas
- Python conventions: async/await, type hints, Ruff/Black
- Database access via SQLAlchemy ORM, Alembic migrations
- API patterns: versioning, unified error handling, pagination

### Frontend Agent
**Context:** `frontend/CLAUDE.md` + `agents/frontend.md`
**Responsibilities:**
- React: component patterns, custom hooks, state management
- Accounting UI: tables, forms, document number masks
- German localization: date formats (DD.MM.YYYY), number formats (1.234,56 €)
- Design system: component library, accessibility (WCAG)

### Database Agent
**Context:** `database/CLAUDE.md` + `agents/database.md`
**Responsibilities:**
- Schema design for PostgreSQL (production), MariaDB (legacy), SQLite (tests)
- Chart of accounts SKR03/SKR04 — account numbers and posting logic
- GoBD compliance: immutability of journal entries after period close
- Migration strategy: Alembic, zero-downtime migrations

### DevOps Agent
**Context:** `devops/CLAUDE.md` + `agents/devops.md`
**Responsibilities:**
- Docker: multi-stage builds, layer caching, secrets management
- Kubernetes: deployments, services, ingress, ConfigMaps, secrets
- CI/CD: GitHub Actions + GitLab CI configured in parallel
- Environments: dev / staging / prod configuration separation

### QA Agent
**Context:** `agents/qa.md`
**Responsibilities:**
- pytest (backend), Vitest (frontend), Playwright (E2E)
- Coverage targets: ≥80% backend, ≥70% frontend
- Accounting-specific test cases: double-entry bookkeeping, balance checks, VAT calculation
- Realistic test data: SKR03 journal entries, typical business transactions

### Security Agent (Gate)
**Context:** `agents/security.md`
**Trigger:** before every `git push` (blocking)
**Responsibilities:**
- OWASP Top 10: SQL injection, auth weaknesses, IDOR, XSS, CSRF
- Bandit scan (Python), npm audit (critical CVEs), Trivy (containers)
- Secrets scan (gitleaks): no keys or passwords in code
- GDPR: personal data, encryption, deletion obligations

### Tax/Compliance Agent (Gate)
**Context:** `agents/tax.md`
**Trigger:** on changes to accounting-relevant files (blocking on violation)
**Responsibilities:**
- HGB §238ff: bookkeeping obligations, principles of proper accounting (GoB)
- GoBD (2019): immutability, traceability, archiving obligations
- UStG: 19%/7% VAT, input tax deduction, reverse charge (§13b)
- DATEV compatibility: SKR03/SKR04, journal entry batch format

### Data Exchange Agent
**Context:** `agents/data-exchange.md`
**Responsibilities:**
- DATEV ASCII/CSV: journal entry batches, master data import/export
- XRechnung (UBL 2.1) + ZUGFeRD 2.3 (mandatory B2B e-invoicing from 2025)
- SEPA pain.001 (payments), camt.053 (bank statement import)
- ELSTER: VAT return data, interface to ERiC library
- MT940 / CAMT.052: bank import

### Review Agent
**Context:** `agents/review.md`
**Trigger:** before every merge to develop/main
**Responsibilities:**
- Cross-cutting consistency check across backend/frontend/DB
- API contract: OpenAPI schema vs. frontend expectations
- Breaking change detection
- Documentation completeness

---

## Hook Configuration

### `.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          { "type": "command", "command": "scripts/hooks/lint-and-typecheck.sh" }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "scripts/hooks/git-gate.sh" }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "scripts/hooks/session-end.sh" }
        ]
      }
    ]
  }
}
```

### Hook Scripts

| Script | Trigger | Action |
|--------|---------|--------|
| `lint-and-typecheck.sh` | Write/Edit on .py, .ts, .tsx | Ruff, ESLint, mypy, tsc — output for orchestrator |
| `git-gate.sh` | Bash (detects `git push`) | Bandit + gitleaks + tax-relevance check — blocks on finding |
| `session-end.sh` | Stop event | Writes `memory/project_status.md` + `.claude/state/` |

**Detecting accounting-relevant changes in `git-gate.sh`:**
```bash
CHANGED=$(git diff --cached --name-only)
if echo "$CHANGED" | grep -qE "(booking|account|tax|transaction|ledger|journal|invoice|vat)"; then
  # Tax-agent-relevant output — orchestrator invokes Tax-Agent
fi
```

---

## Memory Protocol

### Session Start (Orchestrator Requirement)
1. Read `memory/*.md` → project status, user preferences, past decisions
2. Read `.claude/state/*.md` → open agent tasks, in-progress work
3. Read last 3 entries in `docs/decisions/` → current architecture decisions
4. Run `git log --oneline -10` → what changed recently

### Session End (via `session-end.sh` + Orchestrator)
1. Update `memory/project_status.md` with current status
2. Write open tasks to `.claude/state/<agent>-current.md`
3. New architecture decisions → `docs/decisions/YYYY-MM-DD-<title>.md`

### Memory Types

| File | Content |
|------|---------|
| `memory/project_status.md` | Current sprint status, what is done, what is open |
| `memory/project_decisions.md` | Decisions made with rationale |
| `memory/feedback_*.md` | What worked / did not work |
| `memory/reference_*.md` | Where things live (ticket system, external docs) |
| `.claude/state/<agent>-current.md` | Short-lived agent state (currently running, next steps) |

---

## Worktree Strategy

### When to Use Worktrees
- Task > 2 hours AND touches 2+ domains → create worktrees
- Backend + frontend need to be developed in parallel
- Hotfix on `main` while a feature branch is active

### When Not to Use Worktrees
- Sequential tasks (DB schema first, then API)
- Small bug fixes (< 1 hour)
- Docs/config changes
- Review-Agent (reads only, changes nothing)

### Worktree Layout
```
WebBuchhaltung/               # main branch (orchestrator base)
../WebBuchhaltung-backend/    # feature/backend-<ticket>
../WebBuchhaltung-frontend/   # feature/frontend-<ticket>
../WebBuchhaltung-hotfix/     # hotfix/<ticket> (when needed)
```

### Branch Conventions
```
main                          # production-ready, gate-protected
develop                       # integration branch
feature/backend-<ticket>      # Backend-Agent worktree
feature/frontend-<ticket>     # Frontend-Agent worktree
feature/db-<ticket>           # Database-Agent worktree
hotfix/<ticket>               # direct fix on main base
release/<version>             # release preparation
```

---

## Language Rule

**Conversation language is irrelevant for code artifacts.**

| Artifact | Language |
|----------|----------|
| Code (all languages) | **English** |
| Code comments | **English** |
| Commit messages | **English** |
| Branch names | **English** |
| Variable/function names | **English** |
| API endpoints & fields | **English** |
| Docstrings | **English** |
| Test descriptions | **English** |
| Design documents / specs | **English** |
| Conversation with user | German (or whatever the user chooses) |
| UI text / user interface | German (target audience) |
| Legal terms (HGB, GoBD) | German (mandatory terminology) |

This rule applies to all agents without exception. The Review-Agent actively enforces it.

---

## Commit Conventions

All agents and the orchestrator follow **Conventional Commits**. The Review-Agent validates commit message format before every merge.

### Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer]
```

### Allowed Types

| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behavior change |
| `test` | Add or fix tests |
| `docs` | Documentation |
| `ci` | CI/CD configuration |
| `build` | Build system, dependencies |
| `perf` | Performance improvement |
| `style` | Formatting (no logic change) |
| `chore` | Miscellaneous (tooling, config) |
| `revert` | Revert a previous commit |

### 7 Rules

1. **Subject ≤ 50 characters** — short and precise
2. **Capitalize** — subject line starts with uppercase letter
3. **No period** at end of subject
4. **Blank line** between subject and body
5. **Body ≤ 72 characters** per line
6. **Imperative mood** — "Add unit tests" not "Added unit tests"
7. **Body explains the why** — what changed is in the diff, why it changed is in the body

### Project Scopes

`backend`, `frontend`, `db`, `devops`, `qa`, `security`, `tax`, `data-exchange`, `auth`, `api`, `memory`

### Examples

```
feat(backend): Add DATEV journal entry batch export endpoint

Implements GoBD-compliant export with immutable audit trail.
Supports SKR03 and SKR04 account frameworks.

Closes #42
```

```
fix(tax): Correct reverse charge detection for §13b VAT

VAT was applied incorrectly for EU service imports. The check
now uses the supplier country code from the invoice header.
```

```
feat(frontend): Add German number format mask for amount inputs

Formats as 1.234,56 € using Intl.NumberFormat with locale
'de-DE' and currency 'EUR'.
```

### Enforcement

- **Root CLAUDE.md** contains commit rules as mandatory for all agents
- **Review-Agent** validates commit message format before every merge
- **`git-gate.sh`** can optionally invoke `commitlint`

---

## Agent Output Protocol

Every sub-agent writes its result in a unified Markdown format. The orchestrator reads this format and decides on next steps.

### Required Structure

```markdown
## Result
One-sentence summary of what was done.

## Changes
- `path/to/file.py` — what changed and why
- `path/to/other.py` — what changed and why

## Open Issues
- [ ] Unresolved item that needs follow-up
- [ ] Another blocker or question

## Next Steps
- Suggested action for the orchestrator or another agent
```

### Rules

- `## Result` always present, even on failure
- Leave `## Open Issues` empty when nothing is open — do not omit the section
- When an agent is blocked: `## Result` explains the situation, `## Open Issues` lists the blocker
- The orchestrator updates `.claude/state/<agent>-current.md` with the output after each agent run

---

## Conflict Resolution Between Agents

When Backend and Frontend agents touch shared code simultaneously (e.g., TypeScript types, OpenAPI schema, shared utilities):

### Priority Rule

```
Database-Agent  →  Backend-Agent  →  Frontend-Agent
```

Backend defines data structures, frontend consumes them. Never the other way around.

### Ownership Table

| Shared Artifact | Owner | Consumer |
|----------------|-------|----------|
| OpenAPI schema | Backend-Agent | Frontend-Agent |
| TypeScript API types (auto-generated) | Backend-Agent (via `openapi-ts`) | Frontend-Agent |
| DB schemas / Pydantic models | Database-Agent | Backend-Agent |
| Shared UI constants (enums, labels) | Frontend-Agent | — |

### Escalation Protocol

1. The agent that detects a conflict stops and writes `## Open Issues: Conflict with <other-agent> in <file>`
2. Orchestrator arbitrates: reads both agent outputs, decides, issues a clear instruction
3. Only the owner agent may modify the shared artifact

---

## CHANGELOG Generation

Since Conventional Commits are used, `CHANGELOG.md` is generated automatically via **`git-cliff`**.

### Configuration (`cliff.toml` in root)

```toml
[changelog]
header = "# Changelog\n\n"
body = """
## {{ version }} — {{ timestamp | date(format="%Y-%m-%d") }}
{% for group, commits in commits | group_by(attribute="group") %}
### {{ group }}
{% for commit in commits %}
- {{ commit.message }} ([{{ commit.id | truncate(length=7, end="") }}])
{% endfor %}
{% endfor %}
"""
trim = true

[git]
conventional_commits = true
commit_parsers = [
  { message = "^feat", group = "Features" },
  { message = "^fix", group = "Bug Fixes" },
  { message = "^perf", group = "Performance" },
  { message = "^refactor", group = "Refactoring" },
  { message = "^docs", group = "Documentation" },
  { message = "^test", group = "Testing" },
  { message = "^ci", group = "CI/CD" },
  { message = "^build", group = "Build" },
]
filter_commits = true
tag_pattern = "v[0-9].*"
```

### Workflow

```bash
# Preview before release
git cliff --unreleased

# Generate and write to CHANGELOG.md
git cliff -o CHANGELOG.md

# Bump version + tag + update CHANGELOG in one step
git cliff --bump -o CHANGELOG.md && git add CHANGELOG.md && git commit -m "chore(release): Bump version"
```

- DevOps-Agent runs `git cliff` before every release
- `CHANGELOG.md` is versioned in the repo
- CI/CD pipeline validates that CHANGELOG is current before every release tag

---

## Pre-commit Framework

In addition to Claude Code hooks, a **`pre-commit`** framework runs for all manual `git commit` calls. Closes the gap when commits are not made through Claude Code.

### `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks

  - repo: https://github.com/commitizen-tools/commitizen
    rev: v3.20.0
    hooks:
      - id: commitizen
        stages: [commit-msg]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-merge-conflict
      - id: detect-private-key
```

### Setup

```bash
pip install pre-commit
pre-commit install                             # install git hook
pre-commit install --hook-type commit-msg     # commit message validation
pre-commit run --all-files                    # one-time check across entire repo
```

- **commitizen** validates Conventional Commits format on every `git commit`
- **gitleaks** runs both here and in `git-gate.sh` (double safeguard)
- DevOps-Agent ensures `pre-commit` runs in the CI pipeline

---

## Memory Versioning

`memory/` is versioned in the git repo — project decisions and architecture context should be available across all team sessions and machines.

### What Gets Versioned

| Path | Versioned | Reason |
|------|-----------|--------|
| `memory/project_status.md` | Yes | Shared project status |
| `memory/project_decisions.md` | Yes | Architecture decisions for everyone |
| `memory/reference_*.md` | Yes | External resources, links |
| `memory/feedback_*.md` | Yes | Established patterns, learnings |
| `.claude/state/*.md` | No | Short-lived agent state, local only |
| `.superpowers/` | No | Brainstorming tool build artifacts |

### `.gitignore`

```gitignore
# Claude Code agent state (ephemeral, local only)
.claude/state/

# Superpowers brainstorm artifacts
.superpowers/

# Environment
.env
.env.*
!.env.example
```

### Commit Convention for Memory

```
docs(memory): Update project status — auth module complete
docs(memory): Add decision — PostgreSQL chosen over MariaDB for primary DB
```

---

## Implementation Order

1. Initialize git repo + create `.gitignore`
2. Write root `CLAUDE.md` (orchestrator rules incl. memory protocol, language rule, commit conventions, agent output protocol, conflict resolution)
3. Create `.claude/settings.json` with hooks
4. Write `agents/*.md` templates (all 9 agents)
5. Create domain `CLAUDE.md` files (`backend/`, `frontend/`, `database/`, `devops/`)
6. Implement `scripts/hooks/` scripts (`lint-and-typecheck.sh`, `git-gate.sh`, `session-end.sh`)
7. Create `.pre-commit-config.yaml` + run `pre-commit install`
8. Create `cliff.toml` (CHANGELOG configuration)
9. Create `memory/` structure + write initial `project_status.md`
10. First smoke test: verify hook triggers + pre-commit
