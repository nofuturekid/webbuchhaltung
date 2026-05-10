# Development Guide

## Prerequisites

- Docker with Compose plugin
- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+ with npm
- A running PostgreSQL instance (or use the Docker Compose `db` service)

---

## Backend

```bash
cd src/backend

# Install dependencies
uv sync

# Start database only
docker compose up -d db

# Create the test database (once)
docker compose exec db psql -U postgres -c "CREATE DATABASE webbuchhaltung_test;"

# Run tests
TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/webbuchhaltung_test" \
  uv run pytest tests/ -q

# Run locally with hot reload
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/webbuchhaltung" \
SECRET_KEY="dev-only-secret" \
  uv run uvicorn app.main:app --reload --reload-dir app
```

## Frontend

```bash
cd src/frontend

npm install

# Start dev server (proxies /api → http://localhost:8000)
npm run dev

# Type check
npm run typecheck

# Run unit tests
npm test -- --run
```

## Database migrations

```bash
cd src/backend

# Generate a new migration after model changes
uv run alembic revision --autogenerate -m "describe_change"

# Apply all pending migrations (also runs automatically on backend startup)
uv run alembic upgrade head

# Roll back one step
uv run alembic downgrade -1
```

> Migrations run automatically when the backend container starts — no manual step needed
> in Docker Compose. The `alembic upgrade head` command above is only needed for local
> development outside Docker.

---

## Project structure

```
webbuchhaltung/
├── src/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── main.py          # FastAPI app factory + lifespan hook
│   │   │   ├── models/          # SQLAlchemy ORM models
│   │   │   ├── schemas/         # Pydantic request/response schemas
│   │   │   ├── routers/         # One file per domain
│   │   │   ├── services/        # Business logic
│   │   │   └── templates/       # Jinja2 PDF templates
│   │   ├── alembic/versions/    # Database migrations
│   │   ├── seed/                # SKR03/SKR04/SKR07 account data
│   │   └── tests/
│   └── frontend/
│       └── src/
│           ├── features/        # Domain feature modules (each with api.ts + components)
│           ├── pages/           # Route-level page components
│           ├── components/      # Shared UI components
│           └── types/           # TypeScript API types (generated from OpenAPI)
├── agents/                      # Claude Code sub-agent templates
├── docs/decisions/              # Architecture Decision Records (ADR-NNNN-*.md)
├── scripts/hooks/               # Pre-commit and security gate hooks
└── docker-compose.yml
```

---

## Smoke test (end-to-end)

After `docker compose up --build -d`, run the setup wizard at http://localhost:3000
or use the headless bootstrap env vars (see README), then verify the golden path:

```bash
# Health checks
curl http://localhost:8000/health   # → {"status":"ok"}
curl http://localhost:3000          # → HTML login page

# Login and switch mandant
EMAIL=admin@mycompany.de PASSWORD=secret123

TOKEN1=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

MANDANT_ID=$(curl -s -H "Authorization: Bearer $TOKEN1" \
  http://localhost:8000/api/v1/mandants \
  | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

TOKEN=$(curl -s -X POST -H "Authorization: Bearer $TOKEN1" \
  "http://localhost:8000/api/v1/mandants/$MANDANT_ID/switch" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Verify chart of accounts
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

API docs: http://localhost:8000/docs
