# WebBuchhaltung

German accounting software (Buchhaltungssoftware) for small and medium businesses.

Tax jurisdiction: Germany — HGB, GoBD, UStG, DATEV SKR03/SKR04.

## Features

- **Mandant management** — multi-client with role-based access
- **Chart of accounts** — SKR03 and SKR04, fully seeded, customizable
- **Booking journal** — draft/post/reverse lifecycle (GoBD-compliant)
- **Accounting periods** — lock and archive by month
- **Reports** — EÜR (Einnahmen-Überschuss-Rechnung), account statements
- **DATEV export** — EXTF v700 format for tax adviser handoff
- **Invoicing** — customer management, outbound invoices with PDF generation and email delivery
- **Audit trail** — every posting transition is logged (GoBD §9)

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI 0.110, SQLAlchemy 2 (async) |
| Frontend | React 18, TypeScript 5, MUI v6, TanStack Query v5 |
| Database | PostgreSQL 16 (primary) · MariaDB 10.11 / MySQL 8 (supported) |
| PDF | WeasyPrint 62 via Jinja2 templates |
| Auth | JWT (python-jose), bcrypt |
| Migrations | Alembic |
| Packaging | uv (Python), npm (frontend) |
| Runtime | Docker Compose (minimum), Kubernetes-ready |

---

## Quickstart (Docker Compose)

**Prerequisites:** Docker with Compose plugin, Git.

```bash
git clone https://github.com/nofuturekid/webbuchhaltung.git
cd webbuchhaltung
```

Copy and edit the environment file:

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY to a random 32+ character string
```

Start the stack:

```bash
docker compose up --build -d
docker compose exec backend uv run alembic upgrade head
```

Seed the first admin user (fresh database only):

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
        print('Done — login: admin@example.com / admin123')

asyncio.run(seed())
"
```

Open the app: http://localhost:3000 · API docs: http://localhost:8000/docs

> **Before any non-local deployment:** set a strong `SECRET_KEY` in your environment or Docker secrets. The placeholder value in `docker-compose.yml` must never be used in production.

---

## Development

### Backend

```bash
cd backend

# Install dependencies (uv required — https://docs.astral.sh/uv/)
uv sync

# Start a local PostgreSQL (or use the Docker Compose db service)
docker compose up -d db

# Create the test database once
docker compose exec db psql -U postgres -c "CREATE DATABASE webbuchhaltung_test;"

# Run tests
TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/webbuchhaltung_test" \
  uv run pytest tests/ -q

# Run the backend locally (with hot reload)
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/webbuchhaltung" \
SECRET_KEY="dev-only-secret" \
  uv run uvicorn app.main:app --reload --reload-dir app
```

### Frontend

```bash
cd frontend

npm install

# Start dev server (proxies /api to http://localhost:8000)
npm run dev

# Type check
npm run typecheck

# Run unit tests
npm test -- --run
```

### Database migrations

```bash
cd backend

# Generate a new migration after model changes
uv run alembic revision --autogenerate -m "describe_change"

# Apply all pending migrations
uv run alembic upgrade head

# Roll back one step
uv run alembic downgrade -1
```

---

## Smoke test (end-to-end)

After `docker compose up --build -d` and `alembic upgrade head`:

```bash
# Health checks
curl http://localhost:8000/health   # → {"status":"ok"}
curl http://localhost:3000          # → HTML login page

# Obtain a token
TOKEN1=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Switch mandant (replace <MANDANT_ID> with the id printed during seed)
TOKEN=$(curl -s -X POST -H "Authorization: Bearer $TOKEN1" \
  "http://localhost:8000/api/v1/mandants/<MANDANT_ID>/switch" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Verify chart of accounts (~90 SKR03 accounts)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/accounts | \
  python3 -c "import sys,json; a=json.load(sys.stdin); print(len(a), 'accounts')"

# Invoicing golden path
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
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('status:', d['status'], '| booking_id:', d['booking_id'])"

curl -s -o /tmp/invoice.pdf -w "PDF: HTTP %{http_code}, %{size_download} bytes\n" \
  "http://localhost:8000/api/v1/invoices/$INVOICE_ID/pdf" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Project structure

```
webbuchhaltung/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app factory + routers
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── routers/         # One file per domain
│   │   ├── services/        # Business logic
│   │   └── templates/       # Jinja2 PDF templates
│   ├── alembic/versions/    # Database migrations
│   ├── seed/                # SKR03/SKR04 account data
│   └── tests/
├── frontend/
│   └── src/
│       ├── features/        # Domain feature modules
│       ├── pages/           # Route-level page components
│       ├── components/      # Shared UI components
│       └── types/           # TypeScript API types
├── agents/                  # Claude Code sub-agent templates
├── scripts/hooks/           # Pre-commit and gate hooks
└── docker-compose.yml
```

---

## Contributing

1. Branch from `develop`: `git checkout -b feature/<scope>-<short-description>`
2. Implement changes — backend, frontend, or both
3. Write tests; all existing tests must continue to pass
4. Run pre-commit hooks: `pre-commit run --all-files`
5. Open a PR targeting `develop` (not `main`)
6. Gate agents (Tax/Compliance, Security) run automatically — PRs are blocked on violations
7. Merge to `main` only via `develop` after Review-Agent approval

### Commit format (Conventional Commits)

```
feat(backend): Add SEPA export endpoint
fix(frontend): Correct VAT calculation on line item delete
test(qa): Add period lock regression test
```

Types: `feat` `fix` `refactor` `test` `docs` `ci` `build` `perf` `chore`
Scopes: `backend` `frontend` `db` `devops` `qa` `security` `tax` `auth` `api`

### Running the full test suite

```bash
# Backend (requires PostgreSQL — see Development section above)
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/webbuchhaltung_test" \
  uv run pytest tests/ -q

# Frontend
cd frontend && npm test -- --run
```

---

## License

Private — all rights reserved.
