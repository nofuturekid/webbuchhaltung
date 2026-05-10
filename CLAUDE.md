# CLAUDE.md - Basic Rules

These rules apply to every task in this project unless explicitly overridden.
Bias: caution over speed on non-trivial work. Use judgment on trivial tasks.

## Rule 1 — Think Before Coding
State assumptions explicitly. If uncertain, ask rather than guess.
Present multiple interpretations when ambiguity exists.
Push back when a simpler approach exists.
Stop when confused. Name what's unclear.

## Rule 2 — Simplicity First
Minimum code that solves the problem. Nothing speculative.
No features beyond what was asked. No abstractions for single-use code.
Test: would a senior engineer say this is overcomplicated? If yes, simplify.

## Rule 3 — Surgical Changes
Touch only what you must. Clean up only your own mess.
Don't "improve" adjacent code, comments, or formatting.
Don't refactor what isn't broken. Match existing style.

## Rule 4 — Goal-Driven Execution
Define success criteria. Loop until verified.
Don't follow steps. Define success and iterate.
Strong success criteria let you loop independently.

## Rule 5 — Use the model only for judgment calls
Use me for: classification, drafting, summarization, extraction.
Do NOT use me for: routing, retries, deterministic transforms.
If code can answer, code answers.

## Rule 6 — Token budgets are not advisory
Per-task: 4,000 tokens. Per-session: 30,000 tokens.
If approaching budget, summarize and start fresh.
Surface the breach. Do not silently overrun.

## Rule 7 — Surface conflicts, don't average them
If two patterns contradict, pick one (more recent / more tested).
Explain why. Flag the other for cleanup.
Don't blend conflicting patterns.

## Rule 8 — Read before you write
Before adding code, read exports, immediate callers, shared utilities.
"Looks orthogonal" is dangerous. If unsure why code is structured a way, ask.

## Rule 9 — Tests verify intent, not just behavior
Tests must encode WHY behavior matters, not just WHAT it does.
A test that can't fail when business logic changes is wrong.

## Rule 10 — Checkpoint after every significant step
Summarize what was done, what's verified, what's left.
Don't continue from a state you can't describe back.
If you lose track, stop and restate.

## Rule 11 — Match the codebase's conventions, even if you disagree
Conformance > taste inside the codebase.
If you genuinely think a convention is harmful, surface it. Don't fork silently.

## Rule 12 — Fail loud
"Completed" is wrong if anything was skipped silently.
"Tests pass" is wrong if any were skipped.
Default to surfacing uncertainty, not hiding it.

# Project

## WebBuchhaltung — Orchestrator

German accounting software (Buchhaltungssoftware) targeting small and medium businesses.
Tax jurisdiction: Germany — HGB, GoBD, UStG, DATEV SKR03/SKR04.

Stack: FastAPI + Python 3.12 | React 18 + TypeScript 5 |
PostgreSQL 16 | MariaDB 10.11 / MySQL 8 (both fully supported) |
Docker | Kubernetes | GitHub Actions + GitLab CI.

Minimum deployment: Docker Compose. No SQLite — requires a real DB server.

## Language Rule — MANDATORY
ALL code artifacts must be written in English: code, comments, commits, branch names,
variable/function names, API endpoints, docstrings, test descriptions, design docs.

Exceptions (remain German):
- UI text visible to end users (target audience is German-speaking)
- Legal terms: HGB, GoBD, UStG, §13b, SKR03, SKR04, Buchungssatz, Vorsteuer, etc.

## Session Start — ALWAYS run these steps first
1. Read all files in `memory/` — project status, decisions, preferences, references
2. Read all files in `.claude/state/` — open agent tasks and in-progress work
3. Read the 3 most recent files in `docs/decisions/` — current architecture decisions
4. Run `git log --oneline -10` — understand what changed recently

## Session End — ALWAYS run these steps last
1. Update `memory/project_status.md` with what was completed and what is still open
2. Write open tasks to `.claude/state/<agent>-current.md`
3. For any new architecture decision: create `docs/decisions/NNNN-<title>.md` (next sequential number)

## Orchestration — How the Orchestrator Works

The orchestrator (this Claude instance) **plans and coordinates only**.
It never writes domain code itself. All implementation is delegated to sub-agents.

### Orchestrator responsibilities
1. Read the plan, break it into domain tasks
2. Spawn the correct agent(s) with the agent template + task description as prompt
3. Save each agent's output to `.claude/state/<agent>-current.md`
4. Read the output, decide next steps, spawn next agent(s)
5. **After every implementation**: spawn QA-Agent to run smoke test + contract test
6. **After QA passes**: spawn Docs-Agent to update README, CHANGELOG, and ADRs
7. Gate agents (Security, Tax) must pass before push/merge

### How to spawn an agent
```python
# Read the template file, append the specific task, pass as prompt
Agent(
    description="Backend Phase 3 Tasks 1-2: DB migration + schemas",
    prompt=open("agents/backend.md").read() + """

## Your Task
Branch: feature/backend-phase3-rechnungen
Worktree: /path/to/worktree

Implement Task 1 (DB migration) and Task 2 (Pydantic schemas) from
docs/superpowers/plans/2026-05-09-phase3-rechnungen.md.
Commit after each task. All 66 existing tests must still pass.
""")
```

### Agent Delegation Rules

Spawn an agent when work is clearly within one domain and would benefit from
focused context. Do NOT spawn agents for trivial one-liners or config tweaks.

| When | Agent | Template |
|------|-------|----------|
| FastAPI routes, business logic, Pydantic schemas | Backend | `agents/backend.md` |
| React components, hooks, UI, state | Frontend | `agents/frontend.md` |
| Schema changes, migrations, SKR03 logic | Database | `agents/database.md` |
| Docker, Kubernetes, CI/CD pipelines | DevOps | `agents/devops.md` |
| Tests, coverage, smoke tests, API contract checks | QA | `agents/qa.md` |
| Security review, vulnerability scan | Security | `agents/security.md` |
| Accounting logic, GoBD compliance check | Tax | `agents/tax.md` |
| Import/export formats (DATEV, SEPA, XRechnung) | Data-Exchange | `agents/data-exchange.md` |
| Pre-merge cross-domain review | Review | `agents/review.md` |
| README, CHANGELOG, ADRs, API prose | Docs | `agents/docs.md` |

### Parallel vs. sequential spawning
- **Parallel**: spawn multiple agents in one message when tasks are independent
  (e.g. Backend-Agent + DevOps-Agent can run simultaneously)
- **Sequential**: spawn next agent only after the previous one's output is saved
  (e.g. Database-Agent must finish migration before Backend-Agent writes services)

## Worktree Strategy
Use worktrees when: task > 2h AND touches 2+ domains (e.g., backend + frontend).

```bash
# Create parallel worktrees OUTSIDE the project root (not inside .claude/)
git worktree add ../WebBuchhaltung-backend feature/backend-<ticket>
git worktree add ../WebBuchhaltung-frontend feature/frontend-<ticket>

# Spawn Backend-Agent on ../WebBuchhaltung-backend
# Spawn Frontend-Agent on ../WebBuchhaltung-frontend (parallel)

# When both done: spawn Review-Agent, then open PR to develop
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
- Only the owner agent may modify shared artifacts (OpenAPI schema, Pydantic models)
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
main              # production-ready, protected — PRs come from develop only
develop           # integration branch — feature branches merge here first
feature/<scope>-<ticket>   # feature work → PR to develop
hotfix/<ticket>   # urgent fix on main base → PR directly to main
release/<version> # release prep → PR to main
```

## Local Testing — ALWAYS verify in this order

### 1. Unit/integration tests (requires PostgreSQL)
```bash
TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/webbuchhaltung_test" \
  uv run pytest tests/ -q
```
84+ tests, ~15s. Requires a running PostgreSQL instance (use `docker compose up -d db`
and create the test DB once: `docker compose exec db psql -U postgres -c "CREATE DATABASE webbuchhaltung_test;"`).
Run after every backend change.

### 2. Full stack with Docker Compose
```bash
docker compose up --build -d
```
Migrations run automatically on backend startup via the lifespan hook.

Seed the first admin user (only needed on a fresh database):
```bash
docker compose exec backend uv run python -c "
import asyncio
from app.database import engine
from app.models.user import User, UserMandant
from app.models.mandant import Mandant
from app.services.auth import hash_password
from app.services.account import seed_skr_for_mandant
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

async def seed():
    s = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with s() as session:
        user = User(email='admin@example.com', hashed_password=hash_password('admin123'))
        session.add(user)
        mandant = Mandant(name='Muster GmbH', skr_variant='skr03',
                          datev_beraternummer='70000', datev_mandantennummer='12345')
        session.add(mandant)
        await session.flush()
        session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role='admin'))
        await session.flush()
        await seed_skr_for_mandant(session, mandant.id, 'skr03')
        await session.commit()
        print('seeded mandant_id=' + str(mandant.id))

asyncio.run(seed())
"
```

### 3. Smoke test (end-to-end curl)

Run after every full-stack build to verify the golden path works end-to-end.

```bash
# Health
curl http://localhost:8000/health  # → {"status":"ok"}
curl http://localhost:3000         # → HTML login page

# Login → switch mandant (replace MANDANT_ID from seed output above)
TOKEN1=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

TOKEN=$(curl -s -X POST -H "Authorization: Bearer $TOKEN1" \
  "http://localhost:8000/api/v1/mandants/<MANDANT_ID>/switch" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Verify accounts seeded (should return 23 SKR03 accounts)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/accounts | \
  python3 -c "import sys,json; a=json.load(sys.stdin); print(len(a), 'accounts')"

# Phase 3 — Rechnungen golden path
CUSTOMER_ID=$(curl -s -X POST "http://localhost:8000/api/v1/customers/" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Test AG","city":"Berlin","email":"test@example.com"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

INVOICE_ID=$(curl -s -X POST "http://localhost:8000/api/v1/invoices/" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"$CUSTOMER_ID\",\"line_items\":[{\"description\":\"Beratung\",\"quantity\":1,\"unit_price_cents\":10000,\"vat_rate\":0.19,\"position\":1}]}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -s -X POST "http://localhost:8000/api/v1/invoices/$INVOICE_ID/issue" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('status:', d['status'], '| booking:', d['booking_id'])"

curl -s -o /tmp/invoice.pdf -w "PDF: HTTP %{http_code}, %{size_download} bytes\n" \
  "http://localhost:8000/api/v1/invoices/$INVOICE_ID/pdf" \
  -H "Authorization: Bearer $TOKEN"

# API docs
open http://localhost:8000/docs
```

### 4. Contract test (API schema vs. frontend types)

Run when backend router files change — catches breaking API changes before they
reach the frontend. Spawn the **Review-Agent** which runs this automatically, or
run manually:

```bash
# Generate current OpenAPI schema from running backend
curl -s http://localhost:8000/openapi.json -o /tmp/openapi-current.json

# Re-generate frontend TypeScript types from it
cd src/frontend && npx openapi-typescript /tmp/openapi-current.json -o src/types/api-generated.ts

# Diff against the committed types — any new field is a potential contract gap
diff src/types/api.ts src/types/api-generated.ts
```

**When to run:** any time a Pydantic schema or router signature changes.
**Owner:** Review-Agent checks this automatically before every merge.
If drift is found: update `src/frontend/src/types/api.ts` to match — never ignore the diff.

### Known Docker gotchas
- Running `uv run pytest` on the host rebuilds `.venv` with the system Python,
  which the Docker volume mount then exposes inside the container. This makes
  uvicorn's watchfiles hang scanning thousands of venv files.
  Fix: `--reload-dir app` in docker-compose.yml (already set).
- `get_db` must commit after yield — without it writes are rolled back on session
  close. Tests pass anyway because they use savepoint sessions.
