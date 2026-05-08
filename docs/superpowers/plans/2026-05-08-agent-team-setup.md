# Agent-Team Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the complete Claude Code multi-agent infrastructure for WebBuchhaltung — orchestrator rules, domain context files, agent prompt templates, hook scripts, pre-commit framework, and CHANGELOG configuration.

**Architecture:** Modular CLAUDE.md hierarchy where a root orchestrator delegates to 9 specialized sub-agents; shell hook scripts (`PostToolUse`, `Stop`) act as sensors; `memory/` persists project state across sessions in git.

**Tech Stack:** Bash (hook scripts), JSON (settings), YAML (pre-commit), TOML (cliff), Markdown (CLAUDE.md + agent templates)

---

## File Map

| File | Task | Purpose |
|------|------|---------|
| `.gitignore` | 1 | Exclude ephemeral files from git |
| `memory/project_status.md` | 1 | Initial project status |
| `memory/project_decisions.md` | 1 | Architecture decisions log |
| `CLAUDE.md` | 2 | Root orchestrator rules |
| `backend/CLAUDE.md` | 3 | FastAPI/Python context |
| `frontend/CLAUDE.md` | 3 | React/TypeScript context |
| `database/CLAUDE.md` | 3 | Schema/GoBD context |
| `devops/CLAUDE.md` | 3 | Docker/K8s context |
| `agents/backend.md` | 4 | Backend agent prompt template |
| `agents/frontend.md` | 4 | Frontend agent prompt template |
| `agents/database.md` | 4 | Database agent prompt template |
| `agents/devops.md` | 4 | DevOps agent prompt template |
| `agents/qa.md` | 4 | QA agent prompt template |
| `agents/security.md` | 5 | Security gate agent template |
| `agents/tax.md` | 5 | Tax/GoBD gate agent template |
| `agents/data-exchange.md` | 5 | Data exchange agent template |
| `agents/review.md` | 5 | Review gate agent template |
| `scripts/hooks/lint-and-typecheck.sh` | 6 | Post-write linting hook |
| `scripts/hooks/git-gate.sh` | 6 | Pre-push security + tax gate |
| `scripts/hooks/session-end.sh` | 6 | Stop-event memory update |
| `.claude/settings.json` | 7 | Hook wiring + permissions |
| `.pre-commit-config.yaml` | 8 | Client-side commit guards |
| `cliff.toml` | 9 | CHANGELOG generation config |

---

## Task 1: Repository Foundation

**Files:**
- Create: `.gitignore`
- Create: `memory/project_status.md`
- Create: `memory/project_decisions.md`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
# Claude Code agent state (ephemeral, local only)
.claude/state/

# Superpowers brainstorm artifacts
.superpowers/

# Environment files
.env
.env.*
!.env.example

# Python
__pycache__/
*.py[cod]
.venv/
venv/
*.egg-info/
dist/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage

# Node
node_modules/
dist/
*.local

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 2: Create `memory/project_status.md`**

```markdown
# Project Status

**Last updated:** 2026-05-08
**Phase:** Setup — agent infrastructure

## Done
- Design spec approved: docs/superpowers/specs/2026-05-08-claude-agent-team-setup-design.md
- Git repository initialized

## In Progress
- Agent-team infrastructure setup (this plan)

## Open
- Software architecture spec (next brainstorming session)
- First feature implementation

## Key Decisions
- See memory/project_decisions.md
```

- [ ] **Step 3: Create `memory/project_decisions.md`**

```markdown
# Architecture Decisions

## 2026-05-08 — Agent-team model: Hybrid Orchestrator + Worktrees

**Decision:** Use a hybrid model — one root orchestrator that delegates to specialized
sub-agents; critical parallel paths (backend + frontend) use git worktrees.

**Alternatives considered:** Monolithic CLAUDE.md (rejected: too large to maintain);
pure parallel agents without orchestrator (rejected: no coordination).

**Rationale:** Balances flexibility with structure. Orchestrator keeps the big picture;
specialists keep domain knowledge focused.

---

## 2026-05-08 — CLAUDE.md strategy: Modular hierarchy

**Decision:** Root CLAUDE.md for orchestrator; domain CLAUDE.md files in source
directories (auto-loaded by Claude Code); agent prompt templates in agents/*.md.

**Rationale:** Claude Code natively supports CLAUDE.md hierarchy. Domain files load
automatically when Claude works in that directory — no manual loading needed.

---

## 2026-05-08 — Tax jurisdiction: Germany (HGB, GoBD, UStG)

**Decision:** Primary target is German tax law. SKR03 as default chart of accounts.

**Rationale:** User requirement. DATEV is the dominant accounting platform in Germany;
SKR03 covers ~80% of German SMEs.

---

## 2026-05-08 — Language rule: English for all code artifacts

**Decision:** All code, comments, commits, branch names, docstrings, and design
documents must be written in English. UI text and legal terms remain German.

**Rationale:** International codebase conventions; LLM tools work best with English
code. German legal terminology (HGB, GoBD) cannot be translated without losing meaning.
```

- [ ] **Step 4: Create required directories**

```bash
mkdir -p .claude/state
mkdir -p docs/decisions
touch docs/decisions/.gitkeep
```

`.claude/state/` is gitignored (ephemeral agent state). `docs/decisions/.gitkeep` tracks
the directory itself so it exists for future ADR files.

- [ ] **Step 5: Verify directory structure**

```bash
ls -la memory/ && ls -la docs/decisions/ && ls -la .claude/state/
```

Expected: `memory/` has two `.md` files; `docs/decisions/` has `.gitkeep`; `.claude/state/` exists.

- [ ] **Step 6: Commit**

```bash
git add .gitignore memory/ docs/decisions/.gitkeep
git commit -m "chore: Add gitignore, memory structure, and required directories"
```

---

## Task 2: Root CLAUDE.md (Orchestrator)

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Create `CLAUDE.md`**

```markdown
# WebBuchhaltung — Orchestrator

## Project
German accounting software (Buchhaltungssoftware) targeting small and medium businesses.
Tax jurisdiction: Germany — HGB, GoBD, UStG, DATEV SKR03/SKR04.

Stack: FastAPI + Python 3.12 | React 18 + TypeScript 5 | PostgreSQL 16 (prod) |
MariaDB 10.11 (legacy import) | SQLite 3 (tests) | Docker | Kubernetes |
GitHub Actions + GitLab CI.

## Language Rule — MANDATORY
ALL code artifacts must be written in English: code, comments, commits, branch names,
variable/function names, API endpoints, docstrings, test descriptions, design docs.

Exceptions (remain German):
- UI text visible to end users (target audience is German)
- Legal terms: HGB, GoBD, UStG, §13b, SKR03, SKR04, Buchungssatz, Vorsteuer, etc.

## Session Start — ALWAYS run these steps first
1. Read all files in `memory/` — project status, decisions, preferences, references
2. Read all files in `.claude/state/` — open agent tasks and in-progress work
3. Read the 3 most recent files in `docs/decisions/` — current architecture decisions
4. Run `git log --oneline -10` — understand what changed recently

## Session End — ALWAYS run these steps last
1. Update `memory/project_status.md` with what was completed and what is still open
2. Write open tasks to `.claude/state/<agent>-current.md`
3. For any new architecture decision: create `docs/decisions/YYYY-MM-DD-<title>.md`

## Agent Delegation Rules
Use the `Agent` tool with the content of `agents/<name>.md` as the prompt.

Spawn an agent when work is clearly within one domain and would benefit from
focused context. Do NOT spawn agents for trivial one-liners or config tweaks.

| When | Agent | Template |
|------|-------|----------|
| FastAPI routes, business logic, Pydantic schemas | Backend | `agents/backend.md` |
| React components, hooks, UI, state | Frontend | `agents/frontend.md` |
| Schema changes, migrations, SKR03 logic | Database | `agents/database.md` |
| Docker, Kubernetes, CI/CD pipelines | DevOps | `agents/devops.md` |
| Writing tests, coverage, test data | QA | `agents/qa.md` |
| Security review, vulnerability scan | Security | `agents/security.md` |
| Accounting logic, GoBD compliance check | Tax | `agents/tax.md` |
| DATEV, SEPA, XRechnung, ELSTER, MT940 | Data-Exchange | `agents/data-exchange.md` |
| Pre-merge cross-domain review | Review | `agents/review.md` |

## Worktree Strategy
Use worktrees when: task > 2h AND touches 2+ domains (e.g., backend + frontend).

```bash
# Create parallel worktrees
git worktree add ../WebBuchhaltung-backend feature/backend-<ticket>
git worktree add ../WebBuchhaltung-frontend feature/frontend-<ticket>

# When both done: spawn Review-Agent, then merge to develop
git worktree remove ../WebBuchhaltung-backend
git worktree remove ../WebBuchhaltung-frontend
```

Do NOT use worktrees for: sequential tasks, small bug fixes (<1h), docs/config changes.

## Agent Output Protocol
Every sub-agent MUST return output in exactly this format. After each run,
save the output to `.claude/state/<agent>-current.md`.

```
## Result
One-sentence summary of what was done (or why it was blocked).

## Changes
- `path/to/file` — what changed and why

## Open Issues
- [ ] Any blockers or questions (leave empty section if none — do not omit)

## Next Steps
- Suggested action for the orchestrator or another agent
```

## Conflict Resolution
Ownership: Database-Agent → Backend-Agent → Frontend-Agent

- Backend defines all data structures; frontend only consumes them
- Only the owner agent may modify shared artifacts (OpenAPI schema, Pydantic models, DB schemas)
- On conflict: agent writes `## Open Issues: Conflict with <agent> in <file>` and stops
- Orchestrator reads both outputs, decides, and gives explicit instruction to owner agent

## Gate Agents — BLOCKING
These MUST run and pass before their respective operations proceed:

**Security-Agent** — blocks `git push`
- Triggered automatically by `git-gate.sh` hook on every push
- Runs: Bandit (Python), gitleaks (secrets), npm audit (JS CVEs), Trivy (containers)
- On CRITICAL/HIGH finding: explain finding, block push, provide remediation steps

**Tax/Compliance-Agent** — blocks merge to develop/main
- Triggered when changed files match: booking, account, tax, transaction, ledger, journal, invoice, vat
- Checks: GoBD immutability, VAT rate correctness, SKR03/04 account validity
- On violation: explain rule reference (e.g., GoBD §14), block merge

## Commit Conventions — Conventional Commits
Format: `<type>(<scope>): <description>`

Types: feat, fix, refactor, test, docs, ci, build, perf, style, chore, revert
Scopes: backend, frontend, db, devops, qa, security, tax, data-exchange, auth, api, memory

Rules:
1. Subject ≤ 50 characters
2. Start with uppercase letter
3. No period at end
4. Blank line between subject and body
5. Body lines ≤ 72 characters
6. Imperative mood ("Add" not "Added")
7. Body explains WHY, not what (the diff shows what)

## Branch Conventions
```
main              # production-ready, protected
develop           # integration branch
feature/<scope>-<ticket>   # feature work
hotfix/<ticket>   # urgent fix on main base
release/<version> # release prep
```
```

- [ ] **Step 2: Verify the file exists and is non-empty**

```bash
wc -l CLAUDE.md
```

Expected: more than 80 lines.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: Add root CLAUDE.md orchestrator rules"
```

---

## Task 3: Domain CLAUDE.md Files

**Files:**
- Create: `backend/CLAUDE.md`
- Create: `frontend/CLAUDE.md`
- Create: `database/CLAUDE.md`
- Create: `devops/CLAUDE.md`

- [ ] **Step 1: Create `backend/CLAUDE.md`**

```markdown
# Backend Context

You are working in the backend of WebBuchhaltung (German accounting software).

## Stack
- Python 3.12+ — use modern syntax, match statements, `X | Y` union types
- FastAPI 0.110+ — async endpoints, dependency injection, APIRouter per domain
- SQLAlchemy 2.x — async session, mapped class syntax (`MappedColumn`, `Mapped`)
- Pydantic v2 — `model_config`, `field_validator`, no `.dict()` (use `.model_dump()`)
- Alembic — for all database migrations, never alter schema manually
- Ruff — linter and formatter (replaces Black + isort + flake8)
- mypy — strict mode, all functions must have type annotations

## Project Layout (to be created)
```
backend/
├── app/
│   ├── main.py          # FastAPI app factory
│   ├── config.py        # Settings via pydantic-settings
│   ├── database.py      # Async SQLAlchemy engine + session
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── routers/         # One file per domain (invoices, accounts, etc.)
│   ├── services/        # Business logic (no DB access directly in routers)
│   └── dependencies.py  # Shared FastAPI dependencies
├── tests/
│   ├── conftest.py      # pytest fixtures (async test client, test DB)
│   └── test_*.py
├── alembic/
│   ├── env.py
│   └── versions/
├── pyproject.toml
└── Dockerfile
```

## Coding Standards
- All code, comments, and docstrings in English
- Every function must have type annotations — no bare `Any` without justification
- Use `async def` for all endpoint handlers and service methods that touch the DB
- Never use `session.execute(text(...))` with user input — always use ORM or bound params
- Dependency injection for DB: `async def get_db() -> AsyncGenerator[AsyncSession, None]`
- API versioning: all routes under `/api/v1/`

## Error Handling
All errors return this JSON shape:
```json
{
  "error": {
    "code": "INVOICE_NOT_FOUND",
    "message": "Invoice with id 42 does not exist",
    "details": {}
  }
}
```
Use custom exception handlers registered on the FastAPI app, not `raise HTTPException` inline.

## API Conventions
- GET /api/v1/{resource} — list with pagination
- GET /api/v1/{resource}/{id} — single item
- POST /api/v1/{resource} — create (returns 201)
- PATCH /api/v1/{resource}/{id} — partial update
- DELETE /api/v1/{resource}/{id} — soft delete or reversal (returns 204)
- Pagination response: `{"items": [...], "total": N, "page": P, "page_size": S}`

## GoBD Hard Rule
Journal entries (Buchungssätze) that have been posted MUST NOT be updated or deleted.
Use reversal entries (Stornobuchungen) instead. Enforce this at the service layer,
not just the API layer.
```

- [ ] **Step 2: Create `frontend/CLAUDE.md`**

```markdown
# Frontend Context

You are working in the frontend of WebBuchhaltung (German accounting software).

## Stack
- React 18 — functional components only, no class components
- TypeScript 5 — strict mode, no `any`, explicit return types on all functions
- Vite — build tool, use `import.meta.env` for env vars
- React Query (TanStack Query) — for all server state, no manual fetch in components
- Zustand or React Context — for local UI state only
- React Hook Form + Zod — for all forms with validation

## Project Layout (to be created)
```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/      # Shared reusable components
│   │   └── ui/          # Base UI primitives (Button, Input, Table, etc.)
│   ├── features/        # Feature modules (invoices/, accounts/, etc.)
│   │   └── invoices/
│   │       ├── components/
│   │       ├── hooks/
│   │       └── api.ts   # React Query hooks for this feature
│   ├── lib/
│   │   ├── api.ts       # Axios instance with base URL + auth headers
│   │   └── formatters.ts  # German number/date formatters
│   └── types/           # Shared TypeScript types (auto-generated from OpenAPI)
├── tests/
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

## Coding Standards
- All code, comments, and type definitions in English
- UI-facing text in German (the target user is German-speaking)
- Components in PascalCase files; hooks in camelCase files starting with `use`
- No inline styles — use CSS modules or Tailwind
- Every component exports its props type: `export type InvoiceCardProps = {...}`

## German Localization (non-negotiable)
```typescript
// Amounts — always format as German locale
const formatAmount = (value: number): string =>
  new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(value);
// Result: "1.234,56 €"

// Dates — DD.MM.YYYY
const formatDate = (date: Date): string =>
  new Intl.DateTimeFormat('de-DE').format(date);
// Result: "08.05.2026"
```

## API Types
TypeScript types for API responses are auto-generated from the OpenAPI schema:
```bash
npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts
```
Never manually write types that should be auto-generated. Run this after any backend change.

## Accounting UI Patterns
- Amounts: always right-aligned in tables, monospace font, 2 decimal places
- Account numbers (SKR03/04): always 4 digits, left-padded with zeros, e.g., "0800"
- Document numbers: fixed-width display, sortable columns
- Debit/Credit columns side-by-side (T-account style for journal view)
```

- [ ] **Step 3: Create `database/CLAUDE.md`**

```markdown
# Database Context

You are working on the database layer of WebBuchhaltung (German accounting software).

## Databases
- **PostgreSQL 16** — primary production database
- **MariaDB 10.11** — legacy import only (read-only access for migration tools)
- **SQLite 3** — test fixtures and offline mode

## Stack
- SQLAlchemy 2.x — async ORM, use `AsyncSession` everywhere
- Alembic — all schema changes via migrations, never ALTER TABLE manually
- asyncpg — async PostgreSQL driver

## Project Layout (to be created)
```
backend/
├── app/
│   ├── models/
│   │   ├── base.py        # DeclarativeBase + TimestampMixin
│   │   ├── account.py     # Chart of accounts
│   │   ├── journal.py     # Journal entries (Buchungssätze)
│   │   ├── invoice.py     # Invoices (Rechnungen)
│   │   └── period.py      # Accounting periods
│   └── database.py        # Engine factory, session factory
└── alembic/
    ├── env.py
    └── versions/
```

## SKR03/SKR04 Account Numbering
Account numbers are 4 digits. Key ranges in SKR03:
- 0xxx: Fixed assets (Anlagevermögen)
- 1xxx: Current assets (Umlaufvermögen)
- 2xxx: Equity + provisions (Eigenkapital, Rückstellungen)
- 3xxx: Liabilities (Verbindlichkeiten)
- 4xxx: Operating expenses (Betriebsausgaben)
- 5xxx–6xxx: Revenues (Erträge)
- 8xxx: VAT accounts (Umsatzsteuerkonten)
- 9xxx: Statistical accounts

## GoBD Hard Rules — NEVER VIOLATE
1. **Immutability**: A posted journal entry (`status = 'posted'`) MUST NOT be updated
   or deleted. Only reversal entries (Stornobuchungen) are allowed.
   Enforce with a DB-level CHECK constraint or trigger AND at the service layer.

2. **Sequential numbering**: Journal entry numbers must be sequential with no gaps.
   Use a DB sequence, not application-generated IDs.

3. **Audit trail**: Every data change must be logged (who changed what and when).
   Use an `audit_log` table or PostgreSQL triggers.

4. **Archiving**: Records from closed periods must be flagged `archived = true`
   and never modified. Retention: 10 years minimum (HGB §257).

## Migration Rules
- Every migration has an `upgrade()` and a `downgrade()` function
- Migrations must be zero-downtime safe (add column nullable first, then NOT NULL with default)
- Test migrations on a copy of production data before applying
- Naming: `YYYY_descriptive_name` (Alembic auto-generates the date prefix)

## Naming Conventions
- Tables: `snake_case`, plural (e.g., `journal_entries`, `chart_of_accounts`)
- Columns: `snake_case` (e.g., `account_number`, `debit_amount`)
- PKs: `id` (UUID preferred over serial for distributed systems)
- FKs: `<referenced_table_singular>_id` (e.g., `account_id`)
- Indexes: `ix_<table>_<column>` (e.g., `ix_journal_entries_account_id`)
```

- [ ] **Step 4: Create `devops/CLAUDE.md`**

```markdown
# DevOps Context

You are working on the infrastructure of WebBuchhaltung (German accounting software).

## Stack
- Docker — containerization, multi-stage builds
- Kubernetes — orchestration (production)
- GitHub Actions — CI/CD pipeline (primary)
- GitLab CI — CI/CD pipeline (mirror)
- Helm — Kubernetes package management

## Project Layout (to be created)
```
devops/
├── docker/
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
├── kubernetes/
│   ├── base/              # Kustomize base
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml
│   └── overlays/
│       ├── dev/
│       ├── staging/
│       └── prod/
├── helm/
│   └── webbuchhaltung/
└── .github/
    └── workflows/
        ├── ci.yml
        └── deploy.yml
```

## Docker Standards
- Multi-stage builds: `builder` stage (with dev deps) → `runtime` stage (minimal)
- Never run containers as root — use a non-root user in the final stage
- No secrets in Dockerfiles or images — use build args for non-sensitive config only
- Pin base image versions: `python:3.12.3-slim-bookworm`, not `python:3.12`
- `.dockerignore` must exclude: `.git`, `__pycache__`, `*.pyc`, `node_modules`, `.env`

## Kubernetes Standards
- Always set resource `requests` and `limits` — no unbounded containers
- Use `ConfigMap` for non-sensitive config, `Secret` for credentials
- Never commit secrets to git — use external secrets operator or sealed secrets
- Liveness and readiness probes required on all deployments
- Use `RollingUpdate` strategy with `maxUnavailable: 0`

## Environment Separation
Three environments, each in its own Kubernetes namespace:
- `dev` — deployed on every push to `develop`
- `staging` — deployed on release branch creation
- `prod` — deployed on tag push `v*.*.*` after manual approval gate

## CI/CD Pipeline Structure
Every PR triggers:
1. Lint + type check (ruff, mypy, tsc)
2. Unit tests (pytest, vitest)
3. Security scan (bandit, npm audit, trivy)
4. Build Docker images
5. E2E tests against dev environment (Playwright)

Merges to main additionally trigger:
6. Staging deployment
7. Smoke test against staging
8. Manual approval gate
9. Production deployment
```

- [ ] **Step 5: Commit**

```bash
git add backend/CLAUDE.md frontend/CLAUDE.md database/CLAUDE.md devops/CLAUDE.md
git commit -m "docs: Add domain CLAUDE.md context files for all four areas"
```

---

## Task 4: Worker Agent Templates

**Files:**
- Create: `agents/backend.md`
- Create: `agents/frontend.md`
- Create: `agents/database.md`
- Create: `agents/devops.md`
- Create: `agents/qa.md`

- [ ] **Step 1: Create `agents/backend.md`**

```markdown
# Backend Agent

You are the Backend Agent for WebBuchhaltung, a German accounting software.
The orchestrator has delegated a specific backend task to you.

## Your Scope
- FastAPI routes, endpoint design, and request/response schemas
- Business logic in service classes (no direct DB calls in routers)
- SQLAlchemy models and Alembic migration files
- Backend unit and integration tests (pytest)

## Hard Rules
- All code, comments, and docstrings in English
- Every function has type annotations — no untyped code
- Use async/await throughout — no synchronous DB calls
- No raw SQL with user input — use SQLAlchemy ORM or bound parameters
- GoBD: posted journal entries are immutable — never write UPDATE/DELETE on posted entries

## FastAPI Patterns
```python
# Router structure
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_db
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from app.services.invoice_service import InvoiceService

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])

@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    return await InvoiceService(db).create(payload)
```

## Error Format
```python
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "INVOICE_NOT_FOUND", "message": f"Invoice {id} not found", "details": {}}
)
```

## Output Format
End your response with exactly this structure:

## Result
[One sentence: what you implemented or why you are blocked]

## Changes
- `path/to/file.py` — [what changed and why]

## Open Issues
- [ ] [Blocker or question — leave empty section if none]

## Next Steps
- [What the orchestrator or another agent should do next]
```

- [ ] **Step 2: Create `agents/frontend.md`**

```markdown
# Frontend Agent

You are the Frontend Agent for WebBuchhaltung, a German accounting software.
The orchestrator has delegated a specific frontend task to you.

## Your Scope
- React components (functional only), custom hooks, state management
- TypeScript type definitions (except those auto-generated from OpenAPI)
- Form handling with React Hook Form + Zod
- Server state via TanStack Query
- German locale formatting for all displayed amounts and dates

## Hard Rules
- All code, comments, and type definitions in English
- UI text visible to users must be in German
- No `any` in TypeScript — use `unknown` and narrow it
- Never manually create types that should come from `src/types/api.ts` (auto-generated)
- Amounts: always format with `Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' })`
- Dates: always format with `Intl.DateTimeFormat('de-DE')`

## Component Pattern
```typescript
// features/invoices/components/InvoiceCard.tsx
import type { Invoice } from '@/types/api';

export type InvoiceCardProps = {
  invoice: Invoice;
  onSelect: (id: string) => void;
};

export function InvoiceCard({ invoice, onSelect }: InvoiceCardProps) {
  const amount = new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: 'EUR',
  }).format(invoice.total_amount);

  return (
    <div onClick={() => onSelect(invoice.id)}>
      <span>{invoice.invoice_number}</span>
      <span>{amount}</span>
    </div>
  );
}
```

## API Hook Pattern
```typescript
// features/invoices/api.ts
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Invoice, InvoiceCreate } from '@/types/api';

export function useInvoices(page = 1) {
  return useQuery({
    queryKey: ['invoices', page],
    queryFn: () => api.get<{ items: Invoice[]; total: number }>(`/api/v1/invoices?page=${page}`),
  });
}
```

## Output Format
End your response with exactly this structure:

## Result
[One sentence: what you implemented or why you are blocked]

## Changes
- `path/to/file.tsx` — [what changed and why]

## Open Issues
- [ ] [Blocker or question — leave empty section if none]

## Next Steps
- [What the orchestrator or another agent should do next]
```

- [ ] **Step 3: Create `agents/database.md`**

```markdown
# Database Agent

You are the Database Agent for WebBuchhaltung, a German accounting software.
The orchestrator has delegated a specific database task to you.

## Your Scope
- SQLAlchemy model definitions
- Alembic migration files
- Database schema design decisions
- Query optimization
- SKR03/SKR04 account structure

## Hard Rules
- All code and comments in English
- Posted journal entries MUST be immutable — enforce with DB constraints AND service layer
- Every schema change requires an Alembic migration — no manual ALTER TABLE
- Migrations must be zero-downtime safe (nullable columns first, then constraints)
- UUID primary keys preferred over serial integers

## SQLAlchemy 2.x Model Pattern
```python
# app/models/journal_entry.py
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import String, Numeric, ForeignKey, CheckConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

class JournalEntry(Base, TimestampMixin):
    __tablename__ = "journal_entries"
    __table_args__ = (
        CheckConstraint(
            "NOT (status = 'posted' AND deleted_at IS NOT NULL)",
            name="ck_posted_entries_not_deletable",
        ),
    )

    id: Mapped[UUID] = mapped_column(default=uuid4, primary_key=True)
    entry_number: Mapped[int] = mapped_column(unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("draft", "posted", "reversed", name="entry_status"), default="draft"
    )
    debit_account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    credit_account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(500))
    is_archived: Mapped[bool] = mapped_column(default=False)
```

## Alembic Migration Pattern
```python
# alembic/versions/2026_add_journal_entries.py
def upgrade() -> None:
    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entry_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade() -> None:
    op.drop_table("journal_entries")
```

## Output Format
End your response with exactly this structure:

## Result
[One sentence: what you implemented or why you are blocked]

## Changes
- `path/to/file.py` — [what changed and why]

## Open Issues
- [ ] [Blocker or question — leave empty section if none]

## Next Steps
- [What the orchestrator or another agent should do next]
```

- [ ] **Step 4: Create `agents/devops.md`**

```markdown
# DevOps Agent

You are the DevOps Agent for WebBuchhaltung, a German accounting software.
The orchestrator has delegated a specific infrastructure task to you.

## Your Scope
- Dockerfile creation and optimization
- Kubernetes manifests (Deployments, Services, Ingress, ConfigMaps, Secrets)
- GitHub Actions and GitLab CI pipeline configuration
- Helm chart management
- Environment-specific configuration (dev/staging/prod)

## Hard Rules
- All code and comments in English
- Never commit secrets to git — use external secrets operator or environment injection
- Containers never run as root — always add `USER nonroot` in final stage
- Pin all image versions — never use `:latest`
- Every Kubernetes deployment must have liveness + readiness probes

## Dockerfile Pattern (multi-stage)
```dockerfile
# devops/docker/backend.Dockerfile
FROM python:3.12.3-slim-bookworm AS builder
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

FROM python:3.12.3-slim-bookworm AS runtime
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
COPY --from=builder /app/.venv ./.venv
COPY backend/app ./app
USER appuser
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Kubernetes Pattern
```yaml
# kubernetes/base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    spec:
      containers:
        - name: backend
          image: webbuchhaltung/backend:latest
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
```

## Output Format
End your response with exactly this structure:

## Result
[One sentence: what you implemented or why you are blocked]

## Changes
- `path/to/file.yaml` — [what changed and why]

## Open Issues
- [ ] [Blocker or question — leave empty section if none]

## Next Steps
- [What the orchestrator or another agent should do next]
```

- [ ] **Step 5: Create `agents/qa.md`**

```markdown
# QA Agent

You are the QA Agent for WebBuchhaltung, a German accounting software.
The orchestrator has delegated a specific testing task to you.

## Your Scope
- pytest tests for backend (unit + integration)
- Vitest tests for frontend (unit + component)
- Playwright tests for E2E flows
- Test data fixtures (realistic SKR03 journal entries and business scenarios)
- Coverage reporting and gap analysis

## Coverage Targets
- Backend: ≥ 80% line coverage
- Frontend: ≥ 70% line coverage
- Critical paths (VAT calculation, journal entry posting): 100%

## Hard Rules
- All test code, descriptions, and fixture names in English
- Tests must be deterministic — no random data without seeded random
- No real external services in unit/integration tests — use mocks or test doubles
- Every accounting calculation test must verify the double-entry constraint: debit == credit

## pytest Pattern (backend)
```python
# tests/test_journal_service.py
import pytest
from decimal import Decimal
from app.services.journal_service import JournalService
from app.schemas.journal import JournalEntryCreate

@pytest.mark.asyncio
async def test_post_journal_entry_makes_it_immutable(db_session):
    """A posted journal entry must reject subsequent updates."""
    service = JournalService(db_session)
    entry = await service.create(JournalEntryCreate(
        debit_account_id="0800",
        credit_account_id="1200",
        amount=Decimal("1190.00"),
        description="Test invoice payment",
    ))
    await service.post(entry.id)

    with pytest.raises(ValueError, match="posted entries are immutable"):
        await service.update(entry.id, description="Modified")

@pytest.mark.asyncio
async def test_vat_calculation_standard_rate(db_session):
    """19% VAT must produce correct net and gross amounts."""
    service = JournalService(db_session)
    result = service.calculate_vat(net_amount=Decimal("1000.00"), vat_rate=Decimal("0.19"))
    assert result.vat_amount == Decimal("190.00")
    assert result.gross_amount == Decimal("1190.00")
```

## Vitest Pattern (frontend)
```typescript
// tests/formatters.test.ts
import { describe, it, expect } from 'vitest';
import { formatAmount, formatDate } from '@/lib/formatters';

describe('formatAmount', () => {
  it('formats positive amounts in German locale', () => {
    expect(formatAmount(1234.56)).toBe('1.234,56 €');
  });
  it('formats zero correctly', () => {
    expect(formatAmount(0)).toBe('0,00 €');
  });
});
```

## Accounting Test Data
Key test fixtures to always have available:
```python
# tests/fixtures/skr03_accounts.py
CASH_ACCOUNT = "1000"           # Kasse
BANK_ACCOUNT = "1200"           # Bank
ACCOUNTS_RECEIVABLE = "1400"    # Forderungen aus L+L
REVENUE_19 = "8400"             # Erlöse 19% USt
REVENUE_7 = "8300"              # Erlöse 7% USt
VAT_PAYABLE_19 = "1776"         # Umsatzsteuer 19%
VAT_PAYABLE_7 = "1771"          # Umsatzsteuer 7%
INPUT_TAX = "1576"              # Vorsteuer
```

## Output Format
End your response with exactly this structure:

## Result
[One sentence: what you implemented or why you are blocked]

## Changes
- `path/to/test_file.py` — [what changed and why]

## Open Issues
- [ ] [Blocker or question — leave empty section if none]

## Next Steps
- [What the orchestrator or another agent should do next]
```

- [ ] **Step 6: Commit**

```bash
git add agents/backend.md agents/frontend.md agents/database.md agents/devops.md agents/qa.md
git commit -m "docs(agents): Add worker agent prompt templates"
```

---

## Task 5: Gate and Exchange Agent Templates

**Files:**
- Create: `agents/security.md`
- Create: `agents/tax.md`
- Create: `agents/data-exchange.md`
- Create: `agents/review.md`

- [ ] **Step 1: Create `agents/security.md`**

```markdown
# Security Agent (Gate)

You are the Security Gate Agent for WebBuchhaltung. You BLOCK git push on critical findings.
The orchestrator has asked you to review changes before they are pushed to remote.

## Your Scope
- OWASP Top 10 code review
- Secrets and credential detection
- Dependency vulnerability assessment
- GDPR data handling compliance

## Automated Scans to Run
Run these commands and include their output in your report:

```bash
# Python security linting (medium+ severity)
bandit -r backend/ -ll --format txt 2>&1 | head -50

# Secrets scan
gitleaks detect --source . --no-git 2>&1 | head -30

# JS/TS dependency vulnerabilities (if frontend exists)
cd frontend && npm audit --audit-level=high 2>&1 | head -30

# Container scan (if Dockerfile exists)
trivy fs --severity HIGH,CRITICAL . 2>&1 | head -30
```

## OWASP Top 10 Manual Checklist
Check each item against the changed files:

- [ ] **A01 Broken Access Control** — ownership validated before returning data?
- [ ] **A02 Cryptographic Failures** — no plaintext passwords, PII encrypted at rest?
- [ ] **A03 Injection** — no raw SQL with user input, ORM used throughout?
- [ ] **A04 Insecure Design** — no business logic bypassable via direct API calls?
- [ ] **A05 Security Misconfiguration** — no debug mode in prod, CORS restricted?
- [ ] **A07 Auth Failures** — JWT validated, no hardcoded credentials, bcrypt for passwords?
- [ ] **A08 Software Integrity** — no untrusted deserialization?
- [ ] **A09 Logging Failures** — no PII in logs, errors logged without exposing internals?

## GDPR Checklist (German data protection law)
- [ ] Personal data (name, email, address) encrypted at rest in DB
- [ ] Deletion endpoint exists for user data (Recht auf Vergessenwerden)
- [ ] No PII written to log files
- [ ] Data processing documented (Verarbeitungsverzeichnis consideration)

## Severity Levels
- **CRITICAL** — actively exploitable, RCE, data breach risk → BLOCK push
- **HIGH** — serious vulnerability, likely exploitable → BLOCK push
- **MEDIUM** — noteworthy but lower risk → WARN, allow push with documented exception
- **LOW** — minor issue → note in report, do not block

## Blocking Rule
If any CRITICAL or HIGH finding exists:
1. Set `## Result` to `BLOCKED — [reason]`
2. List each finding in `## Open Issues` with: severity, tool, file:line, description
3. Provide specific remediation in `## Next Steps`
4. The orchestrator must NOT allow the push to proceed

## Output Format
End your response with exactly this structure:

## Result
[PASS — no critical findings | BLOCKED — N critical/high findings]

## Changes
- [Any files you modified to fix issues directly]

## Open Issues
- [ ] [SEVERITY] `file:line` — [description] (tool: bandit/gitleaks/manual)

## Next Steps
- [Specific fix required before push can proceed, or "None — push approved"]
```

- [ ] **Step 2: Create `agents/tax.md`**

```markdown
# Tax/Compliance Agent (Gate)

You are the Tax and GoBD Compliance Gate Agent for WebBuchhaltung.
You enforce German accounting law. You BLOCK merges on hard rule violations.

## Your Scope
- GoBD (Grundsätze zur ordnungsmäßigen Führung und Aufbewahrung von Büchern) compliance
- HGB §238ff bookkeeping obligations
- UStG VAT calculation correctness
- DATEV SKR03/SKR04 account validity

## GoBD Hard Rules — BLOCKING on violation
These rules come from GoBD (BMF-Schreiben 2019). Violations block the merge.

1. **Immutability (§14 GoBD)**: Journal entries with `status='posted'` must NEVER be
   modified or deleted. Only reversal entries (Stornobuchungen) are permitted.
   - Check: no UPDATE/DELETE on `journal_entries` WHERE `status='posted'`
   - Check: service layer raises an error if `post()` is called on already-posted entry

2. **Sequential numbering (§11 GoBD)**: Entry numbers must be sequential with no gaps.
   - Check: entry numbers come from a DB sequence, not application code
   - Check: no manual entry number assignment

3. **Audit trail (§9 GoBD)**: All changes to accounting data must be logged.
   - Check: `audit_log` table exists and is written to on all INSERT/UPDATE
   - Check: log contains: user_id, timestamp, table_name, record_id, change_summary

4. **Archiving (§14b UStG / HGB §257)**: Data must be retained for 10 years.
   - Check: no hard delete on records older than 10 years
   - Check: `is_archived` flag exists and archived records are immutable

## VAT Rules (UStG) — WARNING on violation (non-blocking)
- Standard rate: 19% — applies to most goods and services
- Reduced rate: 7% — food (§12 Abs. 2 UStG), books, public transport, culture
- Zero rate: exports (§4 Nr. 1a), intra-EU B2B supplies (§4 Nr. 1b, §6a)
- Reverse charge (§13b): construction services, EU service imports, scrap metal
- Check: VAT account used matches the rate (SKR03: 1776=19%, 1771=7%, 1775=reduced)

## SKR03 Account Validation
Valid account ranges (SKR03):
- 0100–0990: Fixed assets | 1000–1990: Current assets
- 2000–2990: Equity + provisions | 3000–3990: Liabilities
- 4000–4990: Cost of goods | 5000–6990: Operating expenses
- 8000–8990: Revenue | 9000–9990: Statistical

Accounts outside these ranges require explicit justification.

## Checks to Run
```bash
# Check for any UPDATE on posted journal entries in changed files
grep -n "UPDATE.*journal_entries\|\.update\(.*status.*posted" --include="*.py" -r backend/

# Check for DELETE on journal entries
grep -n "DELETE.*journal_entries\|\.delete\(\|session\.delete" --include="*.py" -r backend/
```

## Blocking Rule
- **GoBD hard rule violation** → BLOCK merge, require fix
- **VAT rate mismatch** → WARN (non-blocking), document in report
- **Invalid account number** → WARN (non-blocking), recommend correction

## Output Format
End your response with exactly this structure:

## Result
[COMPLIANT — no violations | WARNING — N warnings (non-blocking) | BLOCKED — N hard rule violations]

## Changes
- [Any compliance fixes you applied directly]

## Open Issues
- [ ] [VIOLATION/WARNING] [Rule reference] `file:line` — [description]

## Next Steps
- [Required fix with specific GoBD/UStG reference, or "None — merge approved"]
```

- [ ] **Step 3: Create `agents/data-exchange.md`**

```markdown
# Data Exchange Agent

You are the Data Exchange Agent for WebBuchhaltung, a German accounting software.
You handle all import and export of accounting data in German standard formats.

## Your Scope
- DATEV ASCII/CSV format (journal entry batches, master data)
- XRechnung (UBL 2.1) — mandatory B2B e-invoicing standard from 2025
- ZUGFeRD 2.3 — hybrid PDF/XML invoice format
- SEPA pain.001 (payment initiation), camt.053 (bank statement)
- ELSTER interface (VAT return data, ERiC library)
- MT940 / CAMT.052 (bank import formats)
- Generic CSV/Excel import/export

## Hard Rules
- All code and comments in English
- Validate all imported data before writing to DB
- Never silently discard import errors — collect and report all errors
- Exported DATEV files must match the official DATEV ASCII specification exactly
- XRechnung output must pass official Schematron validation

## DATEV ASCII Format Key Fields
```
# DATEV Buchungsstapel header line 1:
"EXTF";700;21;"Buchungsstapel";7;...

# Journal entry line format:
Umsatz;Soll/Haben;WKZ;Kurs;BasisUmsatz;WKZBasisUmsatz;Konto;Gegenkonto;...
```

## XRechnung Key Requirements
- Must use UBL 2.1 or UN/CEFACT CII D16B XML syntax
- Mandatory fields: seller VAT ID, buyer reference (Leitweg-ID for public sector)
- Validate with: `java -jar validationtool-x.y.z-standalone.jar -s scenarios.xml invoice.xml`
- All amounts in EUR with 2 decimal places, no currency symbol in XML

## SEPA pain.001 Key Requirements
```xml
<PmtInf>
  <PmtMtd>TRF</PmtMtd>
  <NbOfTxs>1</NbOfTxs>
  <CtrlSum>1190.00</CtrlSum>
  <PmtTpInf><SvcLvl><Cd>SEPA</Cd></SvcLvl></PmtTpInf>
  <ReqdExctnDt><Dt>2026-05-10</Dt></ReqdExctnDt>
</PmtInf>
```

## Error Handling Pattern
```python
@dataclass
class ImportResult:
    success_count: int
    error_count: int
    errors: list[ImportError]  # Never discard errors silently

@dataclass
class ImportError:
    row: int
    field: str
    value: str
    reason: str
```

## Output Format
End your response with exactly this structure:

## Result
[One sentence: what format was implemented or why you are blocked]

## Changes
- `path/to/file.py` — [what changed and why]

## Open Issues
- [ ] [Blocker or question — leave empty section if none]

## Next Steps
- [What the orchestrator or another agent should do next]
```

- [ ] **Step 4: Create `agents/review.md`**

```markdown
# Review Agent

You are the Review Agent for WebBuchhaltung. You perform pre-merge cross-domain review.
The orchestrator calls you before every merge to develop or main.

## Your Scope
- Cross-domain consistency: do backend, frontend, and DB changes align?
- API contract validation: does the OpenAPI schema match frontend expectations?
- Breaking change detection: will this merge break existing clients?
- Language rule enforcement: are all code artifacts in English?
- Commit message format validation (Conventional Commits)
- Documentation completeness check

## Checks to Run

### 1. Language rule check
```bash
# Find German prose in code files (not UI strings, not legal terms)
grep -rn "[äöüÄÖÜß]" --include="*.py" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules backend/ frontend/src/ | grep -v "# noqa"
```
Any match that is not a UI string or legal term (HGB, GoBD) is a violation.

### 2. Commit message format check
```bash
git log develop..HEAD --format="%s" | while read msg; do
  if ! echo "$msg" | grep -qE "^(feat|fix|refactor|test|docs|ci|build|perf|style|chore|revert)(\([a-z-]+\))?: [A-Z]"; then
    echo "INVALID: $msg"
  fi
done
```

### 3. OpenAPI contract check
If backend router files changed:
```bash
# Generate current OpenAPI schema
cd backend && python -c "from app.main import app; import json; print(json.dumps(app.openapi()))" > /tmp/current-schema.json
# Compare with frontend's expected types (if openapi-ts was run)
diff <(cat frontend/src/types/api.ts | head -20) <(echo "check manually")
```

### 4. Database migration check
If model files changed, verify a migration file also exists:
```bash
git diff --name-only develop..HEAD | grep "app/models/" && \
  git diff --name-only develop..HEAD | grep "alembic/versions/" || \
  echo "WARNING: model changed but no migration found"
```

### 5. Test coverage check
```bash
# Backend
cd backend && pytest --co -q 2>/dev/null | wc -l  # count tests, warn if < 1 per changed file

# Frontend
cd frontend && npx vitest run --reporter=verbose 2>/dev/null | tail -5
```

## Blocking Criteria
Block merge if:
- Language rule violation found in non-UI, non-legal-term code
- Model changed without corresponding migration
- Breaking API change without version bump
- Commit message format violations (>2 in the batch)

## Non-blocking (warn only)
- Missing docstrings on public functions
- Test coverage below target (warn, document gap)
- OpenAPI schema drift (warn if minor, block if major)

## Output Format
End your response with exactly this structure:

## Result
[APPROVED — ready to merge | BLOCKED — N issues require fixes]

## Changes
- [Any trivial fixes you applied directly, e.g., trailing whitespace]

## Open Issues
- [ ] [BLOCKER/WARNING] [check name] — [description with file:line]

## Next Steps
- [Specific fix required, or "None — merge approved"]
```

- [ ] **Step 5: Commit**

```bash
git add agents/security.md agents/tax.md agents/data-exchange.md agents/review.md
git commit -m "docs(agents): Add gate and exchange agent prompt templates"
```

---

## Task 6: Hook Scripts

**Files:**
- Create: `scripts/hooks/lint-and-typecheck.sh`
- Create: `scripts/hooks/git-gate.sh`
- Create: `scripts/hooks/session-end.sh`

- [ ] **Step 1: Create `scripts/hooks/lint-and-typecheck.sh`**

```bash
#!/usr/bin/env bash
# Runs after Write/Edit tool calls. Detects file type and runs appropriate linter.
# Output is read by the orchestrator to decide whether to spawn a fix agent.
set -euo pipefail

# Claude Code passes the modified file path via CLAUDE_TOOL_OUTPUT or similar context.
# We scan recently modified tracked files as a fallback.
MODIFIED_FILES=$(git diff --name-only 2>/dev/null || echo "")

if [ -z "$MODIFIED_FILES" ]; then
  exit 0
fi

ERRORS=0

# Python files: run ruff + mypy
PY_FILES=$(echo "$MODIFIED_FILES" | grep '\.py$' || true)
if [ -n "$PY_FILES" ]; then
  echo "=== Ruff lint ==="
  if command -v ruff &>/dev/null; then
    ruff check $PY_FILES || ERRORS=$((ERRORS + 1))
  else
    echo "WARN: ruff not installed — skipping Python lint"
  fi

  echo "=== mypy type check ==="
  if command -v mypy &>/dev/null; then
    mypy $PY_FILES --ignore-missing-imports || ERRORS=$((ERRORS + 1))
  else
    echo "WARN: mypy not installed — skipping type check"
  fi
fi

# TypeScript/TSX files: run tsc
TS_FILES=$(echo "$MODIFIED_FILES" | grep -E '\.(ts|tsx)$' || true)
if [ -n "$TS_FILES" ] && [ -f "frontend/tsconfig.json" ]; then
  echo "=== TypeScript type check ==="
  if command -v npx &>/dev/null; then
    (cd frontend && npx tsc --noEmit 2>&1) || ERRORS=$((ERRORS + 1))
  else
    echo "WARN: npx not installed — skipping TypeScript check"
  fi
fi

if [ $ERRORS -gt 0 ]; then
  echo ""
  echo "LINT_ERRORS=$ERRORS — orchestrator should review and fix"
  exit 1
fi

echo "All checks passed."
exit 0
```

- [ ] **Step 2: Create `scripts/hooks/git-gate.sh`**

```bash
#!/usr/bin/env bash
# Runs after Bash tool calls. Detects git push and runs security + tax-relevance checks.
# Exit code 1 blocks the operation and requires orchestrator intervention.
set -euo pipefail

# Only activate on git push commands
BASH_CMD="${CLAUDE_TOOL_INPUT:-}"
if ! echo "$BASH_CMD" | grep -q "git push"; then
  exit 0
fi

echo "=== Security Gate: running pre-push checks ==="
ERRORS=0
TAX_RELEVANT=0

# Check for accounting-relevant file changes (triggers Tax-Agent)
CHANGED=$(git diff --cached --name-only 2>/dev/null || git diff HEAD~1 --name-only 2>/dev/null || echo "")
if echo "$CHANGED" | grep -qiE "(booking|account|tax|transaction|ledger|journal|invoice|vat)"; then
  TAX_RELEVANT=1
  echo "TAX_RELEVANT=1 — changed files touch accounting logic"
  echo "Orchestrator must invoke Tax-Agent before push proceeds."
fi

# Secrets scan
echo "--- Secrets scan (gitleaks) ---"
if command -v gitleaks &>/dev/null; then
  gitleaks detect --source . --no-git --exit-code 1 2>&1 || {
    echo "BLOCKED: gitleaks found secrets in code"
    ERRORS=$((ERRORS + 1))
  }
else
  echo "WARN: gitleaks not installed — skipping secrets scan"
fi

# Python security scan
echo "--- Python security scan (bandit) ---"
if [ -d "backend" ] && command -v bandit &>/dev/null; then
  bandit -r backend/ -ll --quiet 2>&1 || {
    echo "BLOCKED: bandit found high-severity Python security issues"
    ERRORS=$((ERRORS + 1))
  }
else
  echo "WARN: bandit not installed or backend/ not found — skipping"
fi

# JS dependency audit
echo "--- JS dependency audit (npm audit) ---"
if [ -d "frontend" ] && [ -f "frontend/package.json" ] && command -v npm &>/dev/null; then
  (cd frontend && npm audit --audit-level=high --json 2>/dev/null | \
    python3 -c "
import sys, json
data = json.load(sys.stdin)
vulns = data.get('metadata', {}).get('vulnerabilities', {})
high = vulns.get('high', 0) + vulns.get('critical', 0)
if high > 0:
    print(f'BLOCKED: {high} high/critical npm vulnerabilities found')
    sys.exit(1)
print(f'npm audit: no high/critical vulnerabilities')
") || ERRORS=$((ERRORS + 1))
else
  echo "WARN: npm or frontend/package.json not found — skipping JS audit"
fi

echo ""
if [ $ERRORS -gt 0 ]; then
  echo "GATE_STATUS=BLOCKED errors=$ERRORS"
  echo "Orchestrator must invoke Security-Agent to review and fix findings."
  exit 1
fi

if [ $TAX_RELEVANT -eq 1 ]; then
  echo "GATE_STATUS=TAX_REVIEW_REQUIRED"
  echo "Orchestrator must invoke Tax-Agent before push proceeds."
  exit 1
fi

echo "GATE_STATUS=PASS — all security checks passed"
exit 0
```

- [ ] **Step 3: Create `scripts/hooks/session-end.sh`**

```bash
#!/usr/bin/env bash
# Runs on Stop event. Updates memory/project_status.md with session summary.
# The orchestrator also updates .claude/state/ files directly.
set -euo pipefail

# Ensure state directory exists (gitignored but must exist locally)
mkdir -p .claude/state

TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
STATUS_FILE="memory/project_status.md"

if [ ! -f "$STATUS_FILE" ]; then
  echo "WARN: $STATUS_FILE not found — skipping memory update"
  exit 0
fi

# Append session end marker so orchestrator knows to update on next session start
echo "" >> "$STATUS_FILE"
echo "<!-- session-end: $TIMESTAMP -->" >> "$STATUS_FILE"

# Show recent git changes for context
echo ""
echo "=== Session end — recent changes ==="
git log --oneline -5 2>/dev/null || true
echo "Orchestrator: update memory/project_status.md and .claude/state/ files."
exit 0
```

- [ ] **Step 4: Make scripts executable**

```bash
chmod +x scripts/hooks/lint-and-typecheck.sh
chmod +x scripts/hooks/git-gate.sh
chmod +x scripts/hooks/session-end.sh
```

- [ ] **Step 5: Verify scripts are executable**

```bash
ls -la scripts/hooks/
```

Expected: all three `.sh` files have `-rwxr-xr-x` permissions.

- [ ] **Step 6: Test lint script with a clean file**

```bash
# Create a temporary valid Python file
echo "def hello() -> str:
    return 'world'
" > /tmp/test_valid.py

# Manually test ruff on it
ruff check /tmp/test_valid.py && echo "TEST PASS: clean file passes" || echo "TEST FAIL"
rm /tmp/test_valid.py
```

Expected output: `TEST PASS: clean file passes`

- [ ] **Step 7: Test git-gate does not trigger on non-push commands**

```bash
# Simulate a non-push bash command
CLAUDE_TOOL_INPUT="git status" bash scripts/hooks/git-gate.sh
echo "Exit code: $?"
```

Expected: exit code 0 (no output, hook passes through silently).

- [ ] **Step 8: Commit**

```bash
git add scripts/hooks/
git commit -m "feat(devops): Add Claude Code hook scripts for lint, security gate, and session end"
```

---

## Task 7: Claude Code Configuration

**Files:**
- Create: `.claude/settings.json`
- Modify: `.claude/settings.local.json`

- [ ] **Step 1: Create `.claude/settings.json`**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "scripts/hooks/lint-and-typecheck.sh"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "scripts/hooks/git-gate.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "scripts/hooks/session-end.sh"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Validate JSON is valid**

```bash
python3 -m json.tool .claude/settings.json > /dev/null && echo "JSON valid" || echo "JSON invalid"
```

Expected: `JSON valid`

- [ ] **Step 3: Update `.claude/settings.local.json` to allow hook scripts**

Read the current content of `.claude/settings.local.json` first, then add hook permissions:

```json
{
  "permissions": {
    "allow": [
      "Skill(update-config)",
      "Bash(/home/thomas/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/brainstorming/scripts/start-server.sh *)",
      "Bash(git init *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "Bash(scripts/hooks/lint-and-typecheck.sh*)",
      "Bash(scripts/hooks/git-gate.sh*)",
      "Bash(scripts/hooks/session-end.sh*)"
    ]
  }
}
```

- [ ] **Step 4: Validate settings.local.json**

```bash
python3 -m json.tool .claude/settings.local.json > /dev/null && echo "JSON valid" || echo "JSON invalid"
```

Expected: `JSON valid`

- [ ] **Step 5: Commit**

```bash
git add .claude/settings.json
git commit -m "feat(devops): Wire Claude Code hooks in settings.json"
```

Note: `.claude/settings.local.json` is intentionally not committed (user-local permissions).

---

## Task 8: Pre-commit Framework

**Files:**
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Create `.pre-commit-config.yaml`**

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
        files: ^backend/

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

- [ ] **Step 2: Install pre-commit (if not already installed)**

```bash
pip install pre-commit
pre-commit --version
```

Expected: version string like `pre-commit 3.x.x`

- [ ] **Step 3: Install git hooks**

```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

Expected output includes: `pre-commit installed at .git/hooks/pre-commit`

- [ ] **Step 4: Run pre-commit on existing files**

```bash
pre-commit run --all-files 2>&1 | tail -20
```

Expected: hooks run without blocking errors on our Markdown/JSON/YAML files.
The mypy hook will skip (no Python files yet) and ruff will skip (no Python files).
`detect-private-key` and `check-yaml` should pass.

- [ ] **Step 5: Commit**

```bash
git add .pre-commit-config.yaml
git commit -m "build: Add pre-commit framework with ruff, mypy, gitleaks, commitizen"
```

---

## Task 9: CHANGELOG Configuration

**Files:**
- Create: `cliff.toml`

- [ ] **Step 1: Create `cliff.toml`**

```toml
[changelog]
header = "# Changelog\n\n"
body = """
## {{ version | default(value="Unreleased") }} — {{ timestamp | date(format="%Y-%m-%d") }}
{% for group, commits in commits | group_by(attribute="group") %}
### {{ group }}
{% for commit in commits %}
- {{ commit.message }} ([`{{ commit.id | truncate(length=7, end="") }}`])
{% endfor %}
{% endfor %}
"""
trim = true
footer = ""

[git]
conventional_commits = true
filter_unconventional = true
commit_parsers = [
  { message = "^feat", group = "Features" },
  { message = "^fix", group = "Bug Fixes" },
  { message = "^perf", group = "Performance" },
  { message = "^refactor", group = "Refactoring" },
  { message = "^docs", group = "Documentation" },
  { message = "^test", group = "Testing" },
  { message = "^ci", group = "CI/CD" },
  { message = "^build", group = "Build" },
  { message = "^chore\\(release\\)", skip = true },
  { message = "^chore", group = "Miscellaneous" },
  { message = "^style", skip = true },
]
filter_commits = true
tag_pattern = "v[0-9].*"
protect_breaking_commits = false
```

- [ ] **Step 2: Install git-cliff (if not already installed)**

```bash
# Option A: via cargo
cargo install git-cliff 2>/dev/null || true

# Option B: via pip
pip install git-cliff 2>/dev/null || true

# Option C: download binary
# See https://github.com/orhun/git-cliff/releases
git-cliff --version
```

- [ ] **Step 3: Verify CHANGELOG preview works**

```bash
git-cliff --unreleased 2>&1 | head -30
```

Expected: outputs a formatted changelog section showing the commits made so far
in this task series (chore, feat, docs entries).

- [ ] **Step 4: Commit**

```bash
git add cliff.toml
git commit -m "build: Add git-cliff configuration for automatic CHANGELOG generation"
```

---

## Task 10: Smoke Test

Verify that all components work together correctly.

- [ ] **Step 1: Verify directory structure**

```bash
find . -not -path './.git/*' -not -path './.superpowers/*' -not -path './node_modules/*' \
  -type f | sort
```

Expected files present:
```
./.claude/settings.json
./.claude/settings.local.json
./.gitignore
./.pre-commit-config.yaml
./CLAUDE.md
./agents/backend.md
./agents/data-exchange.md
./agents/database.md
./agents/devops.md
./agents/frontend.md
./agents/qa.md
./agents/review.md
./agents/security.md
./agents/tax.md
./backend/CLAUDE.md
./cliff.toml
./database/CLAUDE.md
./devops/CLAUDE.md
./docs/superpowers/plans/2026-05-08-agent-team-setup.md
./docs/superpowers/specs/2026-05-08-claude-agent-team-setup-design.md
./frontend/CLAUDE.md
./memory/project_decisions.md
./memory/project_status.md
./scripts/hooks/git-gate.sh
./scripts/hooks/lint-and-typecheck.sh
./scripts/hooks/session-end.sh
```

- [ ] **Step 2: Verify git log shows clean conventional commits**

```bash
git log --oneline
```

Expected: all commits follow `type(scope): Description` format.

- [ ] **Step 3: Test lint hook fires on a Python file with an error**

```bash
mkdir -p backend
echo "import os
x=1+1  # ruff will flag missing whitespace around operator in some configs
print( x )
" > backend/test_lint_check.py

bash scripts/hooks/lint-and-typecheck.sh
echo "Exit code: $?"
rm backend/test_lint_check.py
rmdir backend 2>/dev/null || true
```

Expected: ruff runs and reports any findings; exit code reflects result.

- [ ] **Step 4: Test git-gate ignores non-push commands**

```bash
CLAUDE_TOOL_INPUT="ls -la" bash scripts/hooks/git-gate.sh
echo "Exit code: $?"
```

Expected: exit code 0, no output (hook exits early).

- [ ] **Step 5: Test session-end hook writes to memory**

```bash
bash scripts/hooks/session-end.sh
tail -3 memory/project_status.md
```

Expected: last line contains `<!-- session-end: 2026-` marker.

- [ ] **Step 6: Test pre-commit runs cleanly**

```bash
pre-commit run --all-files 2>&1 | grep -E "(Passed|Failed|Skipped)" | head -10
```

Expected: `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `detect-private-key`
all show `Passed` or `Skipped`.

- [ ] **Step 7: Test CHANGELOG preview**

```bash
git-cliff --unreleased 2>&1
```

Expected: formatted markdown changelog output with sections for Features, Documentation, etc.

- [ ] **Step 8: Update memory/project_status.md**

```markdown
# Project Status

**Last updated:** 2026-05-08
**Phase:** Setup complete — agent infrastructure ready

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

## In Progress
- Nothing

## Open
- Software architecture spec (next brainstorming session)
- First feature implementation (accounting module)

## Key Decisions
- See memory/project_decisions.md
```

- [ ] **Step 9: Final commit**

```bash
git add memory/project_status.md
git commit -m "docs(memory): Mark agent-team setup as complete"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by task |
|-----------------|-----------------|
| Modular CLAUDE.md hierarchy | Tasks 2, 3 |
| 10 agents with responsibilities | Tasks 2, 4, 5 |
| Hook-based automation | Tasks 6, 7 |
| Memory protocol (session start/end) | Task 2 (CLAUDE.md), Task 6 (session-end.sh) |
| Worktree strategy | Task 2 (CLAUDE.md) |
| Language rule | Tasks 2, 3, 4, 5 (in every file) |
| Commit conventions | Task 2 (CLAUDE.md), Task 8 (commitizen) |
| Agent output protocol | Tasks 2, 4, 5 (in every agent template) |
| Conflict resolution | Task 2 (CLAUDE.md) |
| CHANGELOG generation | Task 9 |
| Pre-commit framework | Task 8 |
| Memory versioning | Task 1, Task 2 (.gitignore) |
| .gitignore | Task 1 |
