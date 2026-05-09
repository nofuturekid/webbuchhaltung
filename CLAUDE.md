# WebBuchhaltung — Orchestrator

## Project
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
| Import/export formats (DATEV, SEPA, XRechnung) | Data-Exchange | `agents/data-exchange.md` |
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
main              # production-ready, protected
develop           # integration branch
feature/<scope>-<ticket>   # feature work
hotfix/<ticket>   # urgent fix on main base
release/<version> # release prep
```

## Local Testing — ALWAYS verify in this order

### 1. Unit/integration tests (fast, no Docker)
```bash
cd backend && uv run pytest tests/ -q
```
66 tests, ~13s, SQLite in-memory. Run after every backend change.

### 2. Full stack with Docker Compose
```bash
docker compose up --build -d
docker compose exec backend uv run alembic upgrade head
```

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

# Verify accounts seeded (should return ~90 SKR03 accounts)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/accounts | \
  python3 -c "import sys,json; a=json.load(sys.stdin); print(len(a), 'accounts')"

# API docs
open http://localhost:8000/docs
```

### Known Docker gotchas
- Running `uv run pytest` on the host rebuilds `.venv` with the system Python,
  which the Docker volume mount then exposes inside the container. This makes
  uvicorn's watchfiles hang scanning thousands of venv files.
  Fix: `--reload-dir app` in docker-compose.yml (already set).
- `get_db` must commit after yield — without it writes are rolled back on session
  close. Tests pass anyway because they use savepoint sessions.
