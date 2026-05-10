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
