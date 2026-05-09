# Phase 1 — Accounting Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 WebBuchhaltung backend — multi-Mandant accounting API with JWT auth, chart of accounts (SKR03/04/07), GoBD-compliant booking lifecycle, DATEV ASCII export, EÜR/Kontoauszug reports, Docker Compose dev environment, and React 18 skeleton.

**Architecture:** FastAPI async backend (PostgreSQL + MariaDB via SQLAlchemy 2.x async), flat booking table with `booking_type` enum, JWT-scoped per-Mandant isolation, service layer owns all GoBD enforcement. React skeleton with MUI v6 + TanStack Query auto-generated from OpenAPI schema.

**Tech Stack:** Python 3.12 / uv / FastAPI 0.110+ / SQLAlchemy 2.x async / Alembic / Pydantic v2 / python-jose[cryptography] / passlib[bcrypt] / asyncpg / aiomysql / pytest-asyncio / httpx / React 18 / Vite / MUI v6 / TanStack Query / openapi-typescript

**Spec:** `docs/superpowers/specs/2026-05-09-phase1-accounting-core-design.md`

---

## File Map

```
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── 0001_initial_schema.py        # all tables + sequences + triggers
│       └── 0002_seed_data.py             # SKR03/04/07 + TaxKeys
├── seed/
│   ├── skr03.json
│   ├── skr04.json
│   ├── skr07.json
│   └── tax_keys.json
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── errors.py
│   ├── dependencies.py
│   ├── models/
│   │   ├── base.py
│   │   ├── mandant.py
│   │   ├── user.py
│   │   ├── account.py
│   │   ├── booking.py
│   │   └── period.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── mandant.py
│   │   ├── account.py
│   │   ├── booking.py
│   │   ├── period.py
│   │   └── reports.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── mandants.py
│   │   ├── accounts.py
│   │   ├── tax_keys.py
│   │   ├── bookings.py
│   │   ├── periods.py
│   │   ├── reports.py
│   │   ├── datev.py
│   │   └── admin.py
│   └── services/
│       ├── auth.py
│       ├── mandant.py
│       ├── account.py
│       ├── booking.py
│       ├── period.py
│       ├── audit.py
│       ├── reports.py
│       └── datev.py
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_mandant.py
│   ├── test_accounts.py
│   ├── test_bookings.py
│   ├── test_periods.py
│   ├── test_reports.py
│   └── test_datev.py
└── Dockerfile
docker-compose.yml
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── nginx.conf
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── api/            # openapi-typescript output — gitignored, generated via script
    ├── components/
    │   └── Layout.tsx
    └── pages/
        ├── LoginPage.tsx
        └── DashboardPage.tsx
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`
- Create: `backend/tests/conftest.py`
- Create: `.env.example`

- [ ] **Step 1: Create backend/pyproject.toml**

```toml
[project]
name = "webbuchhaltung"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "sqlalchemy[asyncio]>=2.0.29",
    "alembic>=1.13.1",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    "asyncpg>=0.29.0",
    "aiomysql>=0.2.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.1.0",
    "pytest-asyncio>=0.23.6",
    "httpx>=0.27.0",
    "anyio>=4.3.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.uv]
dev-dependencies = [
    "pytest>=8.1.0",
    "pytest-asyncio>=0.23.6",
    "httpx>=0.27.0",
    "anyio>=4.3.0",
]
```

- [ ] **Step 2: Create backend/alembic.ini**

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost:5432/webbuchhaltung

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3: Create backend/alembic/env.py**

```python
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.config import settings
from app.models.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.database_url
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


run_migrations_online()
```

- [ ] **Step 4: Create backend/app/config.py**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    secret_key: str
    storage_backend: str = "local"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"


settings = Settings()
```

- [ ] **Step 5: Create backend/app/database.py**

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 6: Create backend/app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="WebBuchhaltung API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 7: Create docker-compose.yml**

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: webbuchhaltung
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/webbuchhaltung
      SECRET_KEY: changeme-in-production
      STORAGE_BACKEND: local
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  pgdata:
```

- [ ] **Step 8: Create backend/Dockerfile**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install uv && uv sync --no-dev
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 9: Create .env.example and backend/tests/conftest.py**

`.env.example`:
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/webbuchhaltung
SECRET_KEY=changeme-in-production
STORAGE_BACKEND=local
```

`backend/tests/conftest.py`:
```python
import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_db
from app.models.base import Base

TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/webbuchhaltung_test"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    connection = await test_engine.connect()
    trans = await connection.begin()
    session = AsyncSession(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()


@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
```

- [ ] **Step 10: Install dependencies and verify health endpoint**

```bash
cd backend && uv sync && uv run uvicorn app.main:app --reload
```

In a second terminal:
```bash
curl http://localhost:8000/health
```
Expected: `{"status":"ok"}`

- [ ] **Step 11: Commit**

```bash
git add backend/ docker-compose.yml .env.example
git commit -m "feat(backend): Add project scaffolding — FastAPI, Alembic, Docker Compose"
```

---

## Task 2: Base Models + Error Framework

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/errors.py`

- [ ] **Step 1: Create backend/app/models/base.py**

```python
from datetime import datetime, timezone
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

- [ ] **Step 2: Create backend/app/errors.py**

```python
from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class BookingAlreadyPostedError(AppError):
    status_code = 422
    code = "BOOKING_ALREADY_POSTED"

    def __init__(self) -> None:
        super().__init__("Cannot modify a posted booking. Use reversal instead.")


class PeriodLockedError(AppError):
    status_code = 422
    code = "PERIOD_LOCKED"

    def __init__(self) -> None:
        super().__init__("The accounting period is locked or archived.")


class AccountNotEditableError(AppError):
    status_code = 422
    code = "ACCOUNT_NOT_EDITABLE"

    def __init__(self) -> None:
        super().__init__("Seed accounts are read-only except for private_share_percent and is_active.")


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )
```

- [ ] **Step 3: Register error handler in main.py**

Edit `backend/app/main.py` — add after imports:
```python
from app.errors import AppError, app_error_handler
# ...
app.add_exception_handler(AppError, app_error_handler)
```

- [ ] **Step 4: Write and run smoke test**

`backend/tests/test_health.py`:
```python
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_unknown_route_returns_404(client):
    response = await client.get("/nonexistent")
    assert response.status_code == 404
```

```bash
cd backend && uv run pytest tests/test_health.py -v
```
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/ backend/app/errors.py backend/app/main.py backend/tests/test_health.py
git commit -m "feat(backend): Add base models, TimestampMixin, and AppError framework"
```

---

## Task 3: All Core Models + Initial Migration

**Files:**
- Create: `backend/app/models/mandant.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/account.py`
- Create: `backend/app/models/booking.py`
- Create: `backend/app/models/period.py`
- Create: `backend/alembic/versions/0001_initial_schema.py`

- [ ] **Step 1: Create backend/app/models/mandant.py**

```python
import uuid
from sqlalchemy import String, Boolean, Integer, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class Mandant(Base, TimestampMixin):
    __tablename__ = "mandants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    steuernummer: Mapped[str | None] = mapped_column(String(50))
    ust_id: Mapped[str | None] = mapped_column(String(20))
    datev_beraternummer: Mapped[str | None] = mapped_column(String(10))
    datev_mandantennummer: Mapped[str | None] = mapped_column(String(10))
    fiscal_year_start: Mapped[int] = mapped_column(Integer, default=1)
    skr_variant: Mapped[str] = mapped_column(
        SAEnum("skr03", "skr04", "skr07", name="skr_variant_enum"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

- [ ] **Step 2: Create backend/app/models/user.py**

```python
import uuid
from sqlalchemy import String, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserMandant(Base):
    __tablename__ = "user_mandants"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    mandant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mandants.id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(
        SAEnum("admin", "bookkeeper", "readonly", name="user_role_enum"),
        default="bookkeeper",
        nullable=False,
    )
```

- [ ] **Step 3: Create backend/app/models/account.py**

```python
import uuid
from decimal import Decimal
from sqlalchemy import String, Boolean, Integer, Numeric, UniqueConstraint, CheckConstraint, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class ChartOfAccount(Base, TimestampMixin):
    __tablename__ = "chart_of_accounts"
    __table_args__ = (
        UniqueConstraint("mandant_id", "account_number", name="uq_coa_mandant_number"),
        CheckConstraint("private_share_percent BETWEEN 0 AND 100", name="ck_coa_private_share"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mandant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mandants.id"), nullable=False)
    account_number: Mapped[str] = mapped_column(String(4), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_class: Mapped[str] = mapped_column(String(10), nullable=False)
    tax_type: Mapped[str | None] = mapped_column(String(50))
    skr_variant: Mapped[str] = mapped_column(
        SAEnum("skr03", "skr04", "skr07", "custom", name="skr_source_enum"), nullable=False
    )
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    private_share_percent: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TaxKey(Base):
    __tablename__ = "tax_keys"

    code: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    tax_type: Mapped[str] = mapped_column(
        SAEnum("USt", "VSt", "steuerfrei", "§13b", "keine", "UStfrei", name="tax_type_enum"),
        nullable=False,
    )
```

- [ ] **Step 4: Create backend/app/models/booking.py**

```python
import uuid
from decimal import Decimal
from sqlalchemy import (
    String, Boolean, Integer, BigInteger, Numeric, Date, Text,
    ForeignKey, CheckConstraint, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class BookingGroup(Base):
    __tablename__ = "booking_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mandant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mandants.id"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(32))  # TIMESTAMPTZ stored as string for cross-DB compat


class BookingSequence(Base):
    __tablename__ = "booking_sequences"

    mandant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mandants.id"), primary_key=True)
    next_value: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="ck_booking_amount_positive"),
        CheckConstraint(
            "booking_type != 'entry' OR (coa_id IS NOT NULL AND counter_coa_id IS NOT NULL)",
            name="ck_booking_entry_accounts",
        ),
        CheckConstraint(
            "status != 'posted' OR entry_number IS NOT NULL",
            name="ck_booking_posted_has_number",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mandant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mandants.id"), nullable=False)
    booking_type: Mapped[str] = mapped_column(
        SAEnum("bank", "entry", name="booking_type_enum"), nullable=False
    )
    booking_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("booking_groups.id"))
    parent_booking_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("bookings.id"))
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("bookings.id"))

    date_booking: Mapped[str] = mapped_column(Date, nullable=False)
    date_tax: Mapped[str | None] = mapped_column(Date)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    document_number: Mapped[str | None] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(
        SAEnum("draft", "posted", "reversed", name="booking_status_enum"), default="draft"
    )
    notes: Mapped[str | None] = mapped_column(String(60))
    entry_number: Mapped[int | None] = mapped_column(BigInteger)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # entry only
    coa_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("chart_of_accounts.id"))
    counter_coa_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("chart_of_accounts.id"))
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    tax_amount_cents: Mapped[int | None] = mapped_column(BigInteger)
    tax_key_code: Mapped[int | None] = mapped_column(Integer, ForeignKey("tax_keys.code"))
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # FK → contacts (Phase 3)

    # bank only
    bank_account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # FK → bank_accounts (Phase 2)
    recipient_name: Mapped[str | None] = mapped_column(String(255))
    foreign_bank_account: Mapped[str | None] = mapped_column(String(50))
```

- [ ] **Step 5: Create backend/app/models/period.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import Integer, String, Text, Enum as SAEnum, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime
from app.models.base import Base


class AccountingPeriod(Base):
    __tablename__ = "accounting_periods"
    __table_args__ = (
        UniqueConstraint("mandant_id", "year", "month", name="uq_period_mandant_year_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mandant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mandants.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum("open", "locked", "archived", name="period_status_enum"), default="open"
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mandant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("mandants.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    table_name: Mapped[str] = mapped_column(String(64), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(
        SAEnum("insert", "update", "delete", name="audit_action_enum"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    change_summary: Mapped[dict] = mapped_column(JSON, nullable=False)
```

- [ ] **Step 6: Create Alembic initial migration**

```bash
cd backend && uv run alembic revision --autogenerate -m "initial_schema"
```

Rename the generated file to `0001_initial_schema.py`. Verify it creates all tables. Then append the immutability trigger and booking_sequences insert logic at the end of `upgrade()`:

```python
# At end of upgrade() in 0001_initial_schema.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # ... autogenerated table creation ...

    # PostgreSQL immutability trigger
    op.execute("""
        DO $$ BEGIN
        IF current_setting('server_version_num')::int >= 90000 THEN
            CREATE OR REPLACE FUNCTION prevent_posted_booking_update()
            RETURNS TRIGGER AS $func$
            BEGIN
                IF OLD.status = 'posted' AND NEW.status != 'reversed' THEN
                    RAISE EXCEPTION 'Cannot modify a posted booking. Use reversal instead.';
                END IF;
                RETURN NEW;
            END;
            $func$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS booking_immutability_check ON bookings;
            CREATE TRIGGER booking_immutability_check
                BEFORE UPDATE ON bookings
                FOR EACH ROW EXECUTE FUNCTION prevent_posted_booking_update();
        END IF;
        END $$;
    """)
```

- [ ] **Step 7: Run migration against test DB**

```bash
cd backend
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/webbuchhaltung_test \
  uv run alembic upgrade head
```
Expected: migration runs without error, all tables created.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/ backend/alembic/
git commit -m "feat(db): Add all core models and initial Alembic migration"
```

---

## Task 4: Auth — JWT Service + Endpoints

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/services/auth.py`
- Create: `backend/app/dependencies.py`
- Create: `backend/app/routers/auth.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Create backend/app/schemas/auth.py**

```python
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    email: str
    is_active: bool
```

- [ ] **Step 2: Create backend/app/services/auth.py**

```python
import uuid
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.errors import UnauthorizedError
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: uuid.UUID, mandant_id: uuid.UUID | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "mandant_id": str(mandant_id) if mandant_id else None,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": str(user_id), "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired token.") from exc


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password.")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled.")
    return user
```

- [ ] **Step 3: Create backend/app/dependencies.py**

```python
import uuid
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.errors import UnauthorizedError
from app.models.user import User
from app.services.auth import decode_token
from sqlalchemy import select

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type.")
    result = await session.execute(
        select(User).where(User.id == uuid.UUID(payload["sub"]))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")
    return user


def get_mandant_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> uuid.UUID:
    payload = decode_token(credentials.credentials)
    mandant_id = payload.get("mandant_id")
    if not mandant_id:
        raise UnauthorizedError("No Mandant selected. Use /mandants/{id}/switch first.")
    return uuid.UUID(mandant_id)
```

- [ ] **Step 4: Create backend/app/routers/auth.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user, security
from app.errors import UnauthorizedError
from app.models.user import User
from app.schemas.auth import AccessTokenResponse, LoginRequest, TokenResponse, UserResponse
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, session: AsyncSession = Depends(get_db)
) -> TokenResponse:
    user = await authenticate_user(session, body.email, body.password)
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(body: dict, session: AsyncSession = Depends(get_db)) -> AccessTokenResponse:
    token = body.get("refresh_token", "")
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid token type.")
    import uuid
    from sqlalchemy import select
    result = await session.execute(
        select(User).where(User.id == uuid.UUID(payload["sub"]))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError("User not found.")
    return AccessTokenResponse(access_token=create_access_token(user.id))


@router.post("/logout")
async def logout() -> dict[str, str]:
    return {"message": "Logged out. Discard tokens client-side."}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
```

- [ ] **Step 5: Register auth router in main.py**

```python
from app.routers import auth as auth_router
app.include_router(auth_router.router, prefix="/api/v1")
```

- [ ] **Step 6: Write failing tests**

`backend/tests/test_auth.py`:
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.services.auth import hash_password, verify_password, create_access_token, decode_token
import uuid


async def _create_user(session: AsyncSession, email: str, password: str) -> User:
    user = User(email=email, hashed_password=hash_password(password))
    session.add(user)
    await session.flush()
    return user


async def test_login_success(client, db_session):
    await _create_user(db_session, "test@example.com", "secret123")
    response = await client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "secret123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_wrong_password(client, db_session):
    await _create_user(db_session, "user2@example.com", "correct")
    response = await client.post("/api/v1/auth/login", json={"email": "user2@example.com", "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


async def test_me_requires_auth(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403  # No bearer token


async def test_me_returns_current_user(client, db_session):
    user = await _create_user(db_session, "me@example.com", "pass")
    token = create_access_token(user.id)
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


async def test_password_hashing():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed)
    assert not verify_password("wrong", hashed)


async def test_token_contains_user_id():
    uid = uuid.uuid4()
    token = create_access_token(uid)
    payload = decode_token(token)
    assert payload["sub"] == str(uid)
    assert payload["type"] == "access"
```

- [ ] **Step 7: Run tests**

```bash
cd backend && uv run pytest tests/test_auth.py -v
```
Expected: all 6 tests pass

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/services/auth.py \
        backend/app/dependencies.py backend/app/routers/auth.py \
        backend/app/main.py backend/tests/test_auth.py
git commit -m "feat(auth): Add JWT authentication — login, refresh, me endpoint"
```

---

## Task 5: Mandant — Service + Endpoints

**Files:**
- Create: `backend/app/schemas/mandant.py`
- Create: `backend/app/services/mandant.py`
- Create: `backend/app/routers/mandants.py`
- Create: `backend/app/routers/admin.py`
- Create: `backend/tests/test_mandant.py`

- [ ] **Step 1: Create backend/app/schemas/mandant.py**

```python
import uuid
from pydantic import BaseModel


class MandantCreate(BaseModel):
    name: str
    steuernummer: str | None = None
    ust_id: str | None = None
    datev_beraternummer: str | None = None
    datev_mandantennummer: str | None = None
    fiscal_year_start: int = 1
    skr_variant: str = "skr03"


class MandantUpdate(BaseModel):
    name: str | None = None
    steuernummer: str | None = None
    ust_id: str | None = None
    datev_beraternummer: str | None = None
    datev_mandantennummer: str | None = None
    fiscal_year_start: int | None = None


class MandantResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    steuernummer: str | None
    ust_id: str | None
    datev_beraternummer: str | None
    datev_mandantennummer: str | None
    fiscal_year_start: int
    skr_variant: str
    is_active: bool
```

- [ ] **Step 2: Create backend/app/services/mandant.py**

```python
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.errors import ForbiddenError, NotFoundError
from app.models.mandant import Mandant
from app.models.user import UserMandant
from app.schemas.mandant import MandantCreate, MandantUpdate
from app.services.auth import create_access_token


async def get_mandant_for_user(
    session: AsyncSession, mandant_id: uuid.UUID, user_id: uuid.UUID
) -> Mandant:
    result = await session.execute(
        select(Mandant)
        .join(UserMandant, UserMandant.mandant_id == Mandant.id)
        .where(Mandant.id == mandant_id, UserMandant.user_id == user_id)
    )
    mandant = result.scalar_one_or_none()
    if not mandant:
        raise NotFoundError(f"Mandant {mandant_id} not found.")
    return mandant


async def list_mandants(session: AsyncSession, user_id: uuid.UUID) -> list[Mandant]:
    result = await session.execute(
        select(Mandant)
        .join(UserMandant, UserMandant.mandant_id == Mandant.id)
        .where(UserMandant.user_id == user_id, Mandant.is_active.is_(True))
    )
    return list(result.scalars().all())


async def create_mandant(
    session: AsyncSession, data: MandantCreate, user_id: uuid.UUID
) -> Mandant:
    mandant = Mandant(**data.model_dump())
    session.add(mandant)
    await session.flush()
    link = UserMandant(user_id=user_id, mandant_id=mandant.id, role="admin")
    session.add(link)
    await session.commit()
    await session.refresh(mandant)
    return mandant


async def update_mandant(
    session: AsyncSession, mandant_id: uuid.UUID, user_id: uuid.UUID, data: MandantUpdate
) -> Mandant:
    mandant = await get_mandant_for_user(session, mandant_id, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(mandant, field, value)
    await session.commit()
    await session.refresh(mandant)
    return mandant


def issue_mandant_token(user_id: uuid.UUID, mandant_id: uuid.UUID) -> str:
    return create_access_token(user_id, mandant_id)
```

- [ ] **Step 3: Create backend/app/routers/mandants.py**

```python
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import AccessTokenResponse
from app.schemas.mandant import MandantCreate, MandantResponse, MandantUpdate
from app.services.mandant import (
    create_mandant,
    get_mandant_for_user,
    issue_mandant_token,
    list_mandants,
    update_mandant,
)

router = APIRouter(prefix="/mandants", tags=["mandants"])


@router.get("", response_model=list[MandantResponse])
async def list_(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list:
    return await list_mandants(session, current_user.id)


@router.post("", response_model=MandantResponse, status_code=201)
async def create(
    body: MandantCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> object:
    return await create_mandant(session, body, current_user.id)


@router.get("/{mandant_id}", response_model=MandantResponse)
async def get(
    mandant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> object:
    return await get_mandant_for_user(session, mandant_id, current_user.id)


@router.patch("/{mandant_id}", response_model=MandantResponse)
async def update(
    mandant_id: uuid.UUID,
    body: MandantUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> object:
    return await update_mandant(session, mandant_id, current_user.id, body)


@router.post("/{mandant_id}/switch", response_model=AccessTokenResponse)
async def switch(
    mandant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AccessTokenResponse:
    await get_mandant_for_user(session, mandant_id, current_user.id)
    return AccessTokenResponse(
        access_token=issue_mandant_token(current_user.id, mandant_id)
    )
```

- [ ] **Step 4: Write failing tests**

`backend/tests/test_mandant.py`:
```python
import pytest
import uuid
from app.models.user import User
from app.models.mandant import Mandant
from app.models.user import UserMandant
from app.services.auth import hash_password, create_access_token


async def _setup_user_and_mandant(session):
    user = User(email=f"u{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    await session.flush()
    mandant = Mandant(name="Test GmbH", skr_variant="skr03")
    session.add(mandant)
    await session.flush()
    link = UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin")
    session.add(link)
    await session.flush()
    return user, mandant


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def test_create_mandant(client, db_session):
    user = User(email=f"c{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    db_session.add(user)
    await db_session.flush()
    resp = await client.post(
        "/api/v1/mandants",
        json={"name": "New GmbH", "skr_variant": "skr03"},
        headers=_auth(user),
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "New GmbH"


async def test_list_mandants_only_own(client, db_session):
    user, mandant = await _setup_user_and_mandant(db_session)
    resp = await client.get("/api/v1/mandants", headers=_auth(user))
    assert resp.status_code == 200
    ids = [m["id"] for m in resp.json()]
    assert str(mandant.id) in ids


async def test_switch_mandant_issues_scoped_token(client, db_session):
    user, mandant = await _setup_user_and_mandant(db_session)
    resp = await client.post(f"/api/v1/mandants/{mandant.id}/switch", headers=_auth(user))
    assert resp.status_code == 200
    from app.services.auth import decode_token
    payload = decode_token(resp.json()["access_token"])
    assert payload["mandant_id"] == str(mandant.id)


async def test_cannot_access_other_users_mandant(client, db_session):
    _, mandant = await _setup_user_and_mandant(db_session)
    other_user = User(email=f"o{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    db_session.add(other_user)
    await db_session.flush()
    resp = await client.get(f"/api/v1/mandants/{mandant.id}", headers=_auth(other_user))
    assert resp.status_code == 404  # mandant isolation
```

- [ ] **Step 5: Register routers and run tests**

In `backend/app/main.py` add:
```python
from app.routers import mandants as mandants_router
app.include_router(mandants_router.router, prefix="/api/v1")
```

```bash
cd backend && uv run pytest tests/test_mandant.py -v
```
Expected: 4 tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/mandant.py backend/app/services/mandant.py \
        backend/app/routers/mandants.py backend/app/main.py \
        backend/tests/test_mandant.py
git commit -m "feat(backend): Add Mandant CRUD and JWT mandant-scoping"
```

---

## Task 6: Chart of Accounts — Seed + Service + Endpoints

**Files:**
- Create: `backend/seed/skr03.json` (excerpt — full file sourced separately)
- Create: `backend/alembic/versions/0002_seed_data.py`
- Create: `backend/app/schemas/account.py`
- Create: `backend/app/services/account.py`
- Create: `backend/app/routers/accounts.py`
- Create: `backend/tests/test_accounts.py`

- [ ] **Step 1: Create seed/skr03.json (structure — full data sourced from DATEV)**

```json
[
  {"account_number": "1200", "name": "Bank", "account_class": "1xxx", "tax_type": null, "skr_variant": "skr03"},
  {"account_number": "1000", "name": "Kasse", "account_class": "1xxx", "tax_type": null, "skr_variant": "skr03"},
  {"account_number": "4000", "name": "Wareneinkauf 19% VSt", "account_class": "4xxx", "tax_type": "VSt", "skr_variant": "skr03"},
  {"account_number": "8400", "name": "Erlöse 19% USt", "account_class": "8xxx", "tax_type": "USt", "skr_variant": "skr03"},
  {"account_number": "1776", "name": "Umsatzsteuer 19%", "account_class": "1xxx", "tax_type": "USt", "skr_variant": "skr03"},
  {"account_number": "1571", "name": "Vorsteuer 19%", "account_class": "1xxx", "tax_type": "VSt", "skr_variant": "skr03"}
]
```

Mirror this structure for `seed/skr04.json` and `seed/skr07.json` with the appropriate account numbers.

Also create `seed/tax_keys.json`:
```json
[
  {"code": 9, "description": "Umsatzsteuer 19%", "tax_rate": "0.1900", "tax_type": "USt"},
  {"code": 10, "description": "Umsatzsteuer 7%", "tax_rate": "0.0700", "tax_type": "USt"},
  {"code": 0, "description": "Keine Steuer", "tax_rate": null, "tax_type": "keine"}
]
```

- [ ] **Step 2: Create Alembic seed migration**

`backend/alembic/versions/0002_seed_data.py`:
```python
"""seed_data

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-09
"""
import json
import uuid
from pathlib import Path
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SEED_DIR = Path(__file__).parent.parent.parent / "seed"


def upgrade() -> None:
    conn = op.get_bind()

    # Seed TaxKeys (mandant-independent)
    tax_keys = json.loads((SEED_DIR / "tax_keys.json").read_text())
    for tk in tax_keys:
        conn.execute(
            op.inline_literal(
                f"INSERT INTO tax_keys (code, description, tax_rate, tax_type) "
                f"VALUES ({tk['code']}, '{tk['description']}', "
                f"{'NULL' if tk['tax_rate'] is None else tk['tax_rate']}, '{tk['tax_type']}') "
                f"ON CONFLICT (code) DO NOTHING"
            )
        )

    # Note: SKR accounts are NOT seeded globally — they are seeded per-Mandant
    # when a Mandant is created (see services/mandant.py seed_skr_for_mandant).
    # The JSON files are used at runtime, not in migrations.


def downgrade() -> None:
    op.execute("DELETE FROM tax_keys")
```

- [ ] **Step 3: Create backend/app/schemas/account.py**

```python
import uuid
from decimal import Decimal
from pydantic import BaseModel


class AccountCreate(BaseModel):
    account_number: str
    name: str
    account_class: str
    tax_type: str | None = None


class AccountUpdate(BaseModel):
    private_share_percent: int | None = None
    is_active: bool | None = None
    # Custom accounts only:
    name: str | None = None
    tax_type: str | None = None


class AccountResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    account_number: str
    name: str
    account_class: str
    tax_type: str | None
    skr_variant: str
    is_custom: bool
    private_share_percent: int
    is_active: bool


class AccountBalanceResponse(BaseModel):
    account_id: uuid.UUID
    account_number: str
    debit_cents: int
    credit_cents: int
    balance_cents: int


class TaxKeyResponse(BaseModel):
    model_config = {"from_attributes": True}

    code: int
    description: str
    tax_rate: Decimal | None
    tax_type: str
```

- [ ] **Step 4: Create backend/app/services/account.py**

```python
import json
import uuid
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.errors import AccountNotEditableError, NotFoundError
from app.models.account import ChartOfAccount, TaxKey
from app.models.booking import Booking
from app.schemas.account import AccountCreate, AccountUpdate

SEED_DIR = Path(__file__).parent.parent.parent / "seed"


async def seed_skr_for_mandant(session: AsyncSession, mandant_id: uuid.UUID, skr_variant: str) -> None:
    filename = SEED_DIR / f"{skr_variant}.json"
    accounts = json.loads(filename.read_text())
    for acc in accounts:
        obj = ChartOfAccount(
            mandant_id=mandant_id,
            account_number=acc["account_number"],
            name=acc["name"],
            account_class=acc["account_class"],
            tax_type=acc.get("tax_type"),
            skr_variant=skr_variant,
            is_custom=False,
        )
        session.add(obj)
    await session.flush()


async def list_accounts(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    account_class: str | None = None,
    is_active: bool | None = None,
) -> list[ChartOfAccount]:
    q = select(ChartOfAccount).where(ChartOfAccount.mandant_id == mandant_id)
    if account_class:
        q = q.where(ChartOfAccount.account_class == account_class)
    if is_active is not None:
        q = q.where(ChartOfAccount.is_active == is_active)
    result = await session.execute(q.order_by(ChartOfAccount.account_number))
    return list(result.scalars().all())


async def get_account(session: AsyncSession, account_id: uuid.UUID, mandant_id: uuid.UUID) -> ChartOfAccount:
    result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.id == account_id, ChartOfAccount.mandant_id == mandant_id
        )
    )
    acc = result.scalar_one_or_none()
    if not acc:
        raise NotFoundError(f"Account {account_id} not found.")
    return acc


async def create_custom_account(
    session: AsyncSession, mandant_id: uuid.UUID, data: AccountCreate
) -> ChartOfAccount:
    acc = ChartOfAccount(
        mandant_id=mandant_id,
        account_number=data.account_number,
        name=data.name,
        account_class=data.account_class,
        tax_type=data.tax_type,
        skr_variant="custom",
        is_custom=True,
    )
    session.add(acc)
    await session.commit()
    await session.refresh(acc)
    return acc


async def update_account(
    session: AsyncSession, account_id: uuid.UUID, mandant_id: uuid.UUID, data: AccountUpdate
) -> ChartOfAccount:
    acc = await get_account(session, account_id, mandant_id)
    updates = data.model_dump(exclude_unset=True)
    if not acc.is_custom:
        allowed = {"private_share_percent", "is_active"}
        disallowed = set(updates) - allowed
        if disallowed:
            raise AccountNotEditableError()
    for field, value in updates.items():
        setattr(acc, field, value)
    await session.commit()
    await session.refresh(acc)
    return acc


async def get_account_balance(
    session: AsyncSession, account_id: uuid.UUID, mandant_id: uuid.UUID,
    date_from: str | None = None, date_to: str | None = None,
) -> dict:
    acc = await get_account(session, account_id, mandant_id)
    q_debit = select(func.coalesce(func.sum(Booking.amount_cents), 0)).where(
        Booking.coa_id == account_id,
        Booking.mandant_id == mandant_id,
        Booking.status == "posted",
    )
    q_credit = select(func.coalesce(func.sum(Booking.amount_cents), 0)).where(
        Booking.counter_coa_id == account_id,
        Booking.mandant_id == mandant_id,
        Booking.status == "posted",
    )
    if date_from:
        q_debit = q_debit.where(Booking.date_booking >= date_from)
        q_credit = q_credit.where(Booking.date_booking >= date_from)
    if date_to:
        q_debit = q_debit.where(Booking.date_booking <= date_to)
        q_credit = q_credit.where(Booking.date_booking <= date_to)
    debit = (await session.execute(q_debit)).scalar()
    credit = (await session.execute(q_credit)).scalar()
    return {
        "account_id": account_id,
        "account_number": acc.account_number,
        "debit_cents": debit,
        "credit_cents": credit,
        "balance_cents": debit - credit,
    }
```

- [ ] **Step 5: Create backend/app/routers/accounts.py**

```python
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user, get_mandant_id
from app.models.user import User
from app.schemas.account import AccountBalanceResponse, AccountCreate, AccountResponse, AccountUpdate, TaxKeyResponse
from app.services.account import (
    create_custom_account, get_account, get_account_balance,
    list_accounts, update_account,
)
from app.services.account import list_tax_keys

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
async def list_(
    account_class: str | None = Query(None),
    is_active: bool | None = Query(None),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> list:
    return await list_accounts(session, mandant_id, account_class, is_active)


@router.post("", response_model=AccountResponse, status_code=201)
async def create(
    body: AccountCreate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> object:
    return await create_custom_account(session, mandant_id, body)


@router.get("/{account_id}", response_model=AccountResponse)
async def get(
    account_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> object:
    return await get_account(session, account_id, mandant_id)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update(
    account_id: uuid.UUID,
    body: AccountUpdate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> object:
    return await update_account(session, account_id, mandant_id, body)


@router.delete("/{account_id}", status_code=204)
async def delete(
    account_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> None:
    from app.services.account import deactivate_account
    await deactivate_account(session, account_id, mandant_id)


@router.get("/{account_id}/balance", response_model=AccountBalanceResponse)
async def balance(
    account_id: uuid.UUID,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await get_account_balance(session, account_id, mandant_id, date_from, date_to)
```

Also add to `services/account.py`:
```python
async def list_tax_keys(session: AsyncSession) -> list[TaxKey]:
    result = await session.execute(select(TaxKey).order_by(TaxKey.code))
    return list(result.scalars().all())


async def deactivate_account(
    session: AsyncSession, account_id: uuid.UUID, mandant_id: uuid.UUID
) -> None:
    from app.errors import AccountNotEditableError
    acc = await get_account(session, account_id, mandant_id)
    if not acc.is_custom:
        raise AccountNotEditableError()
    acc.is_active = False
    await session.commit()
```

- [ ] **Step 6: Write and run tests**

`backend/tests/test_accounts.py`:
```python
import uuid
import pytest
from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.auth import hash_password, create_access_token
from app.services.account import seed_skr_for_mandant


async def _setup(session):
    user = User(email=f"a{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    mandant = Mandant(name="Accts GmbH", skr_variant="skr03")
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")
    token = create_access_token(user.id, mandant.id)
    return {"Authorization": f"Bearer {token}"}


async def test_list_accounts_returns_seeded_data(client, db_session):
    headers = await _setup(db_session)
    resp = await client.get("/api/v1/accounts", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) > 0


async def test_seed_account_only_allows_private_share_edit(client, db_session):
    headers = await _setup(db_session)
    accounts = (await client.get("/api/v1/accounts", headers=headers)).json()
    seed_id = accounts[0]["id"]
    # Allowed: private_share_percent
    resp = await client.patch(f"/api/v1/accounts/{seed_id}", json={"private_share_percent": 20}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["private_share_percent"] == 20
    # Forbidden: name change on seed account
    resp = await client.patch(f"/api/v1/accounts/{seed_id}", json={"name": "Hacked"}, headers=headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "ACCOUNT_NOT_EDITABLE"


async def test_create_custom_account(client, db_session):
    headers = await _setup(db_session)
    resp = await client.post("/api/v1/accounts", json={
        "account_number": "9999", "name": "Test Custom", "account_class": "9xxx"
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["is_custom"] is True
```

```bash
cd backend && uv run pytest tests/test_accounts.py -v
```
Expected: 3 tests pass

- [ ] **Step 7: Create tax_keys router and register all routers**

`backend/app/routers/tax_keys.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.account import TaxKeyResponse
from app.services.account import list_tax_keys
from app.models.account import TaxKey
from sqlalchemy import select

router = APIRouter(prefix="/tax-keys", tags=["tax-keys"])


@router.get("", response_model=list[TaxKeyResponse])
async def list_(session: AsyncSession = Depends(get_db)) -> list:
    return await list_tax_keys(session)


@router.get("/{code}", response_model=TaxKeyResponse)
async def get(code: int, session: AsyncSession = Depends(get_db)) -> object:
    from app.errors import NotFoundError
    result = await session.execute(select(TaxKey).where(TaxKey.code == code))
    tk = result.scalar_one_or_none()
    if not tk:
        raise NotFoundError(f"TaxKey {code} not found.")
    return tk
```

In `main.py` add:
```python
from app.routers import accounts as accounts_router, tax_keys as tax_keys_router
app.include_router(accounts_router.router, prefix="/api/v1")
app.include_router(tax_keys_router.router, prefix="/api/v1")
```

Also call `seed_skr_for_mandant` in `services/mandant.py` `create_mandant()` after the flush:
```python
from app.services.account import seed_skr_for_mandant
# inside create_mandant(), after await session.flush():
await seed_skr_for_mandant(session, mandant.id, data.skr_variant)
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/ backend/seed/ backend/alembic/versions/0002_seed_data.py \
        backend/tests/test_accounts.py
git commit -m "feat(backend): Add chart of accounts, TaxKeys, SKR seed data"
```

---

## Task 7: Booking Draft CRUD

**Files:**
- Create: `backend/app/schemas/booking.py`
- Create: `backend/app/services/booking.py`
- Create: `backend/app/routers/bookings.py`
- Create: `backend/tests/test_bookings.py`

- [ ] **Step 1: Create backend/app/schemas/booking.py**

```python
import uuid
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, field_validator


class BookingCreate(BaseModel):
    booking_type: str = "entry"
    date_booking: date
    date_tax: date | None = None
    amount_cents: int
    currency: str = "EUR"
    document_number: str | None = None
    notes: str | None = None
    booking_group_id: uuid.UUID | None = None
    # entry fields
    coa_id: uuid.UUID | None = None
    counter_coa_id: uuid.UUID | None = None
    tax_rate: Decimal | None = None
    tax_amount_cents: int | None = None
    tax_key_code: int | None = None

    @field_validator("amount_cents")
    @classmethod
    def amount_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount_cents must be positive")
        return v

    @field_validator("notes")
    @classmethod
    def notes_max_60(cls, v: str | None) -> str | None:
        if v and len(v) > 60:
            raise ValueError("notes must be ≤60 characters (DATEV Buchungstext limit)")
        return v


class BookingUpdate(BaseModel):
    date_booking: date | None = None
    date_tax: date | None = None
    amount_cents: int | None = None
    document_number: str | None = None
    notes: str | None = None
    coa_id: uuid.UUID | None = None
    counter_coa_id: uuid.UUID | None = None
    tax_rate: Decimal | None = None
    tax_amount_cents: int | None = None
    tax_key_code: int | None = None


class BookingResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    mandant_id: uuid.UUID
    booking_type: str
    status: str
    date_booking: date
    date_tax: date | None
    amount_cents: int
    currency: str
    document_number: str | None
    notes: str | None
    entry_number: int | None
    coa_id: uuid.UUID | None
    counter_coa_id: uuid.UUID | None
    tax_rate: Decimal | None
    tax_amount_cents: int | None
    tax_key_code: int | None
    booking_group_id: uuid.UUID | None
    parent_booking_id: uuid.UUID | None
    reversal_of_id: uuid.UUID | None
    created_by: uuid.UUID


class BookingGroupCreate(BaseModel):
    description: str | None = None


class BookingGroupResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    mandant_id: uuid.UUID
    description: str | None
```

- [ ] **Step 2: Create backend/app/services/booking.py (draft CRUD portion)**

```python
import uuid
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.errors import BookingAlreadyPostedError, ForbiddenError, NotFoundError
from app.models.booking import Booking, BookingGroup
from app.schemas.booking import BookingCreate, BookingUpdate


async def get_booking(
    session: AsyncSession, booking_id: uuid.UUID, mandant_id: uuid.UUID
) -> Booking:
    result = await session.execute(
        select(Booking).where(
            and_(Booking.id == booking_id, Booking.mandant_id == mandant_id)
        )
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise NotFoundError(f"Booking {booking_id} not found.")
    return booking


async def list_bookings(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    booking_type: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    account_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    q = select(Booking).where(Booking.mandant_id == mandant_id)
    if booking_type:
        q = q.where(Booking.booking_type == booking_type)
    if status:
        q = q.where(Booking.status == status)
    if date_from:
        q = q.where(Booking.date_booking >= date_from)
    if date_to:
        q = q.where(Booking.date_booking <= date_to)
    if account_id:
        q = q.where(
            (Booking.coa_id == account_id) | (Booking.counter_coa_id == account_id)
        )
    from sqlalchemy import func
    count_q = select(func.count()).select_from(q.subquery())
    total = (await session.execute(count_q)).scalar()
    items = (
        await session.execute(
            q.order_by(Booking.date_booking.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
        )
    ).scalars().all()
    return {"items": list(items), "total": total, "page": page, "page_size": page_size}


async def create_booking(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: BookingCreate,
) -> Booking:
    booking = Booking(
        mandant_id=mandant_id,
        created_by=user_id,
        **data.model_dump(),
    )
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


async def update_booking(
    session: AsyncSession,
    booking_id: uuid.UUID,
    mandant_id: uuid.UUID,
    data: BookingUpdate,
) -> Booking:
    booking = await get_booking(session, booking_id, mandant_id)
    if booking.status == "posted":
        raise BookingAlreadyPostedError()
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(booking, field, value)
    await session.commit()
    await session.refresh(booking)
    return booking


async def delete_booking(
    session: AsyncSession, booking_id: uuid.UUID, mandant_id: uuid.UUID
) -> None:
    booking = await get_booking(session, booking_id, mandant_id)
    if booking.status != "draft":
        raise BookingAlreadyPostedError()
    await session.delete(booking)
    await session.commit()
```

- [ ] **Step 3: Create backend/app/routers/bookings.py**

```python
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user, get_mandant_id
from app.models.user import User
from app.schemas.booking import (
    BookingCreate, BookingResponse, BookingUpdate,
    BookingGroupCreate, BookingGroupResponse,
)
from app.services.booking import (
    create_booking, delete_booking, get_booking, list_bookings, update_booking,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])
groups_router = APIRouter(prefix="/booking-groups", tags=["booking-groups"])


@router.get("", response_model=dict)
async def list_(
    booking_type: str | None = Query(None),
    status: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    account_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await list_bookings(session, mandant_id, booking_type, status, date_from, date_to, account_id, page, page_size)


@router.post("", response_model=BookingResponse, status_code=201)
async def create(
    body: BookingCreate,
    current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> object:
    return await create_booking(session, mandant_id, current_user.id, body)


@router.get("/{booking_id}", response_model=BookingResponse)
async def get(
    booking_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> object:
    return await get_booking(session, booking_id, mandant_id)


@router.patch("/{booking_id}", response_model=BookingResponse)
async def update(
    booking_id: uuid.UUID,
    body: BookingUpdate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> object:
    return await update_booking(session, booking_id, mandant_id, body)


@router.delete("/{booking_id}", status_code=204)
async def delete(
    booking_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> None:
    await delete_booking(session, booking_id, mandant_id)
```

- [ ] **Step 4: Write and run draft CRUD tests**

`backend/tests/test_bookings.py` (add more tests in Task 8):
```python
import uuid
import pytest
from datetime import date
from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.auth import hash_password, create_access_token
from app.services.account import seed_skr_for_mandant


async def _setup(session):
    user = User(email=f"b{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    mandant = Mandant(name="BookTest GmbH", skr_variant="skr03")
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")
    # get two account IDs from seed
    from sqlalchemy import select
    from app.models.account import ChartOfAccount
    result = await session.execute(
        select(ChartOfAccount).where(ChartOfAccount.mandant_id == mandant.id).limit(2)
    )
    accounts = result.scalars().all()
    token = create_access_token(user.id, mandant.id)
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user, mandant, accounts[0], accounts[1]


async def test_create_booking_draft(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post("/api/v1/bookings", json={
        "date_booking": "2026-01-15",
        "amount_cents": 119000,
        "coa_id": str(acc1.id),
        "counter_coa_id": str(acc2.id),
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "draft"
    assert data["entry_number"] is None


async def test_update_draft_booking(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post("/api/v1/bookings", json={
        "date_booking": "2026-01-15",
        "amount_cents": 100000,
        "coa_id": str(acc1.id),
        "counter_coa_id": str(acc2.id),
    }, headers=headers)
    booking_id = resp.json()["id"]
    resp2 = await client.patch(f"/api/v1/bookings/{booking_id}", json={"notes": "Updated"}, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["notes"] == "Updated"


async def test_delete_draft_booking(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post("/api/v1/bookings", json={
        "date_booking": "2026-01-15",
        "amount_cents": 100000,
        "coa_id": str(acc1.id),
        "counter_coa_id": str(acc2.id),
    }, headers=headers)
    booking_id = resp.json()["id"]
    del_resp = await client.delete(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert get_resp.status_code == 404


async def test_mandant_isolation(client, db_session):
    headers1, _, mandant1, acc1, acc2 = await _setup(db_session)
    user2 = User(email=f"iso{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    db_session.add(user2)
    mandant2 = Mandant(name="Other GmbH", skr_variant="skr03")
    db_session.add(mandant2)
    await db_session.flush()
    db_session.add(UserMandant(user_id=user2.id, mandant_id=mandant2.id, role="admin"))
    await db_session.flush()
    headers2 = {"Authorization": f"Bearer {create_access_token(user2.id, mandant2.id)}"}
    # Create booking under mandant1
    resp = await client.post("/api/v1/bookings", json={
        "date_booking": "2026-01-15",
        "amount_cents": 100000,
        "coa_id": str(acc1.id),
        "counter_coa_id": str(acc2.id),
    }, headers=headers1)
    booking_id = resp.json()["id"]
    # mandant2 cannot see it
    get_resp = await client.get(f"/api/v1/bookings/{booking_id}", headers=headers2)
    assert get_resp.status_code == 404
```

```bash
cd backend && uv run pytest tests/test_bookings.py -v
```
Expected: 4 tests pass

- [ ] **Step 5: Register bookings router in main.py**

```python
from app.routers import bookings as bookings_router
app.include_router(bookings_router.router, prefix="/api/v1")
app.include_router(bookings_router.groups_router, prefix="/api/v1")
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/booking.py backend/app/services/booking.py \
        backend/app/routers/bookings.py backend/app/main.py \
        backend/tests/test_bookings.py
git commit -m "feat(backend): Add booking draft CRUD with mandant isolation"
```

---

## Task 8: Booking Lifecycle — Post, GoBD, Audit Log

**Files:**
- Create: `backend/app/services/audit.py`
- Modify: `backend/app/services/booking.py` (add `post_booking`, `get_next_entry_number`)
- Modify: `backend/app/routers/bookings.py` (add `/post` endpoint)
- Modify: `backend/tests/test_bookings.py` (add GoBD tests)

- [ ] **Step 1: Create backend/app/services/audit.py**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.period import AuditLog


async def write_audit(
    session: AsyncSession,
    table_name: str,
    record_id: uuid.UUID,
    action: str,
    change_summary: dict,
    mandant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> None:
    log = AuditLog(
        mandant_id=mandant_id,
        user_id=user_id,
        table_name=table_name,
        record_id=record_id,
        action=action,
        changed_at=datetime.now(timezone.utc),
        change_summary=change_summary,
    )
    session.add(log)
```

- [ ] **Step 2: Add get_next_entry_number and post_booking to services/booking.py**

```python
# Add to backend/app/services/booking.py

from sqlalchemy import text
from app.services.audit import write_audit
from app.services.period import get_or_create_period


async def get_next_entry_number(session: AsyncSession, mandant_id: uuid.UUID) -> int:
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        result = await session.execute(
            text(
                "INSERT INTO booking_sequences (mandant_id, next_value) VALUES (:id, 2) "
                "ON CONFLICT (mandant_id) DO UPDATE "
                "SET next_value = booking_sequences.next_value + 1 "
                "RETURNING next_value - 1"
            ),
            {"id": str(mandant_id)},
        )
        return result.scalar_one()
    else:  # mysql / mariadb
        await session.execute(
            text(
                "INSERT INTO booking_sequences (mandant_id, next_value) VALUES (:id, 1) "
                "ON DUPLICATE KEY UPDATE next_value = next_value + 1"
            ),
            {"id": str(mandant_id)},
        )
        result = await session.execute(
            text("SELECT next_value FROM booking_sequences WHERE mandant_id = :id"),
            {"id": str(mandant_id)},
        )
        return result.scalar_one()


async def post_booking(
    session: AsyncSession,
    booking_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Booking:
    booking = await get_booking(session, booking_id, mandant_id)
    if booking.status != "draft":
        raise BookingAlreadyPostedError()

    period = await get_or_create_period(
        session, mandant_id, booking.date_booking.year, booking.date_booking.month
    )
    from app.errors import PeriodLockedError
    if period.status in ("locked", "archived"):
        raise PeriodLockedError()

    entry_number = await get_next_entry_number(session, mandant_id)
    booking.status = "posted"
    booking.entry_number = entry_number

    await write_audit(
        session,
        table_name="bookings",
        record_id=booking.id,
        action="update",
        change_summary={"status": ["draft", "posted"], "entry_number": [None, entry_number]},
        mandant_id=mandant_id,
        user_id=user_id,
    )
    await session.commit()
    await session.refresh(booking)
    return booking
```

- [ ] **Step 3: Add /post endpoint to routers/bookings.py**

```python
# Add to the bookings router

@router.post("/{booking_id}/post", response_model=BookingResponse)
async def post(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> object:
    from app.services.booking import post_booking
    return await post_booking(session, booking_id, mandant_id, current_user.id)


@router.get("/{booking_id}/audit-log")
async def audit_log(
    booking_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> list:
    from sqlalchemy import select
    from app.models.period import AuditLog
    result = await session.execute(
        select(AuditLog).where(
            AuditLog.record_id == booking_id,
            AuditLog.table_name == "bookings",
        ).order_by(AuditLog.changed_at)
    )
    return [
        {"action": r.action, "changed_at": r.changed_at.isoformat(), "change_summary": r.change_summary}
        for r in result.scalars().all()
    ]
```

- [ ] **Step 4: Add GoBD critical-path tests (100% coverage required)**

Add to `backend/tests/test_bookings.py`:
```python
async def test_post_booking_assigns_entry_number(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post("/api/v1/bookings", json={
        "date_booking": "2026-01-15",
        "amount_cents": 119000,
        "coa_id": str(acc1.id),
        "counter_coa_id": str(acc2.id),
    }, headers=headers)
    booking_id = resp.json()["id"]
    post_resp = await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)
    assert post_resp.status_code == 200
    data = post_resp.json()
    assert data["status"] == "posted"
    assert data["entry_number"] is not None
    assert isinstance(data["entry_number"], int)


async def test_posted_booking_is_immutable(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post("/api/v1/bookings", json={
        "date_booking": "2026-01-15",
        "amount_cents": 119000,
        "coa_id": str(acc1.id),
        "counter_coa_id": str(acc2.id),
    }, headers=headers)
    booking_id = resp.json()["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)
    # Cannot update
    patch_resp = await client.patch(f"/api/v1/bookings/{booking_id}", json={"notes": "x"}, headers=headers)
    assert patch_resp.status_code == 422
    assert patch_resp.json()["error"]["code"] == "BOOKING_ALREADY_POSTED"
    # Cannot delete
    del_resp = await client.delete(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert del_resp.status_code == 422


async def test_entry_numbers_are_sequential_no_gaps(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    ids = []
    for _ in range(3):
        r = await client.post("/api/v1/bookings", json={
            "date_booking": "2026-01-15",
            "amount_cents": 10000,
            "coa_id": str(acc1.id),
            "counter_coa_id": str(acc2.id),
        }, headers=headers)
        ids.append(r.json()["id"])
    numbers = []
    for bid in ids:
        r = await client.post(f"/api/v1/bookings/{bid}/post", headers=headers)
        numbers.append(r.json()["entry_number"])
    assert numbers == sorted(numbers)
    assert len(set(numbers)) == 3  # no duplicates


async def test_audit_log_written_on_post(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post("/api/v1/bookings", json={
        "date_booking": "2026-01-15",
        "amount_cents": 50000,
        "coa_id": str(acc1.id),
        "counter_coa_id": str(acc2.id),
    }, headers=headers)
    booking_id = resp.json()["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)
    log_resp = await client.get(f"/api/v1/bookings/{booking_id}/audit-log", headers=headers)
    assert log_resp.status_code == 200
    entries = log_resp.json()
    assert len(entries) >= 1
    assert entries[-1]["action"] == "update"
    assert "status" in entries[-1]["change_summary"]
```

```bash
cd backend && uv run pytest tests/test_bookings.py -v
```
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/booking.py backend/app/services/audit.py \
        backend/app/routers/bookings.py backend/tests/test_bookings.py
git commit -m "feat(backend): Add booking posting, GoBD sequential numbering, audit log"
```

---

## Task 9: Booking Reversal (Stornobuchung)

**Files:**
- Modify: `backend/app/services/booking.py` (add `reverse_booking`)
- Modify: `backend/app/routers/bookings.py` (add `/reverse` endpoint)
- Modify: `backend/tests/test_bookings.py` (add reversal tests)

- [ ] **Step 1: Add reverse_booking to services/booking.py**

```python
async def reverse_booking(
    session: AsyncSession,
    booking_id: uuid.UUID,
    mandant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Booking:
    original = await get_booking(session, booking_id, mandant_id)
    if original.status != "posted":
        from app.errors import ConflictError
        raise ConflictError("Only posted bookings can be reversed.")

    reversal = Booking(
        mandant_id=mandant_id,
        booking_type=original.booking_type,
        date_booking=original.date_booking,
        date_tax=original.date_tax,
        amount_cents=original.amount_cents,
        currency=original.currency,
        document_number=original.document_number,
        notes=f"STORNO: {original.notes or ''}".strip()[:60],
        coa_id=original.counter_coa_id,          # swapped
        counter_coa_id=original.coa_id,           # swapped
        tax_rate=original.tax_rate,
        tax_amount_cents=original.tax_amount_cents,
        tax_key_code=original.tax_key_code,
        reversal_of_id=original.id,
        created_by=user_id,
    )
    session.add(reversal)
    await session.flush()

    reversal_number = await get_next_entry_number(session, mandant_id)
    reversal.status = "posted"
    reversal.entry_number = reversal_number
    original.status = "reversed"

    await write_audit(
        session, "bookings", original.id, "update",
        {"status": ["posted", "reversed"]}, mandant_id, user_id,
    )
    await write_audit(
        session, "bookings", reversal.id, "insert",
        {"reversal_of": str(original.id), "entry_number": reversal_number},
        mandant_id, user_id,
    )
    await session.commit()
    await session.refresh(reversal)
    return reversal
```

- [ ] **Step 2: Add /reverse endpoint to routers/bookings.py**

```python
@router.post("/{booking_id}/reverse", response_model=BookingResponse)
async def reverse(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> object:
    from app.services.booking import reverse_booking
    return await reverse_booking(session, booking_id, mandant_id, current_user.id)
```

- [ ] **Step 3: Write reversal tests (critical path — 100% required)**

Add to `backend/tests/test_bookings.py`:
```python
async def test_reversal_swaps_accounts_and_posts(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post("/api/v1/bookings", json={
        "date_booking": "2026-01-15",
        "amount_cents": 119000,
        "coa_id": str(acc1.id),
        "counter_coa_id": str(acc2.id),
    }, headers=headers)
    booking_id = resp.json()["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)

    rev_resp = await client.post(f"/api/v1/bookings/{booking_id}/reverse", headers=headers)
    assert rev_resp.status_code == 200
    rev = rev_resp.json()
    assert rev["status"] == "posted"
    assert rev["coa_id"] == str(acc2.id)          # swapped
    assert rev["counter_coa_id"] == str(acc1.id)   # swapped
    assert rev["reversal_of_id"] == booking_id
    assert rev["entry_number"] is not None


async def test_reversal_marks_original_as_reversed(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post("/api/v1/bookings", json={
        "date_booking": "2026-01-15",
        "amount_cents": 50000,
        "coa_id": str(acc1.id),
        "counter_coa_id": str(acc2.id),
    }, headers=headers)
    booking_id = resp.json()["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)
    await client.post(f"/api/v1/bookings/{booking_id}/reverse", headers=headers)

    orig_resp = await client.get(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert orig_resp.json()["status"] == "reversed"


async def test_cannot_reverse_draft_booking(client, db_session):
    headers, user, mandant, acc1, acc2 = await _setup(db_session)
    resp = await client.post("/api/v1/bookings", json={
        "date_booking": "2026-01-15",
        "amount_cents": 50000,
        "coa_id": str(acc1.id),
        "counter_coa_id": str(acc2.id),
    }, headers=headers)
    booking_id = resp.json()["id"]
    rev_resp = await client.post(f"/api/v1/bookings/{booking_id}/reverse", headers=headers)
    assert rev_resp.status_code == 409
```

```bash
cd backend && uv run pytest tests/test_bookings.py -v
```
Expected: all tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/booking.py backend/app/routers/bookings.py \
        backend/tests/test_bookings.py
git commit -m "feat(backend): Add Stornobuchung — reversal with atomic post and original status update"
```

---

## Task 10: Accounting Periods

**Files:**
- Create: `backend/app/schemas/period.py`
- Create: `backend/app/services/period.py`
- Create: `backend/app/routers/periods.py`
- Create: `backend/tests/test_periods.py`

- [ ] **Step 1: Create backend/app/services/period.py**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.errors import ConflictError, NotFoundError
from app.models.period import AccountingPeriod


async def get_or_create_period(
    session: AsyncSession, mandant_id: uuid.UUID, year: int, month: int
) -> AccountingPeriod:
    result = await session.execute(
        select(AccountingPeriod).where(
            AccountingPeriod.mandant_id == mandant_id,
            AccountingPeriod.year == year,
            AccountingPeriod.month == month,
        )
    )
    period = result.scalar_one_or_none()
    if not period:
        period = AccountingPeriod(mandant_id=mandant_id, year=year, month=month)
        session.add(period)
        await session.flush()
    return period


async def list_periods(session: AsyncSession, mandant_id: uuid.UUID) -> list[AccountingPeriod]:
    result = await session.execute(
        select(AccountingPeriod)
        .where(AccountingPeriod.mandant_id == mandant_id)
        .order_by(AccountingPeriod.year, AccountingPeriod.month)
    )
    return list(result.scalars().all())


async def lock_period(
    session: AsyncSession, period_id: uuid.UUID, mandant_id: uuid.UUID
) -> AccountingPeriod:
    result = await session.execute(
        select(AccountingPeriod).where(
            AccountingPeriod.id == period_id, AccountingPeriod.mandant_id == mandant_id
        )
    )
    period = result.scalar_one_or_none()
    if not period:
        raise NotFoundError(f"Period {period_id} not found.")
    if period.status != "open":
        raise ConflictError("Only open periods can be locked.")
    period.status = "locked"
    period.locked_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(period)
    return period


async def archive_period(
    session: AsyncSession, period_id: uuid.UUID, mandant_id: uuid.UUID
) -> AccountingPeriod:
    result = await session.execute(
        select(AccountingPeriod).where(
            AccountingPeriod.id == period_id, AccountingPeriod.mandant_id == mandant_id
        )
    )
    period = result.scalar_one_or_none()
    if not period:
        raise NotFoundError(f"Period {period_id} not found.")
    if period.status != "locked":
        raise ConflictError("Only locked periods can be archived.")
    period.status = "archived"
    await session.commit()
    await session.refresh(period)
    return period
```

- [ ] **Step 2: Create backend/app/schemas/period.py**

```python
import uuid
from datetime import datetime
from pydantic import BaseModel


class PeriodResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    mandant_id: uuid.UUID
    year: int
    month: int
    status: str
    locked_at: datetime | None
```

- [ ] **Step 3: Create backend/app/routers/periods.py and register in main.py**

```python
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_mandant_id
from app.schemas.period import PeriodResponse
from app.services.period import archive_period, list_periods, lock_period

router = APIRouter(prefix="/periods", tags=["periods"])


@router.get("", response_model=list[PeriodResponse])
async def list_(
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> list:
    return await list_periods(session, mandant_id)


@router.post("/{period_id}/lock", response_model=PeriodResponse)
async def lock(
    period_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> object:
    return await lock_period(session, period_id, mandant_id)


@router.post("/{period_id}/archive", response_model=PeriodResponse)
async def archive(
    period_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> object:
    return await archive_period(session, period_id, mandant_id)
```

In `main.py`:
```python
from app.routers import periods as periods_router
app.include_router(periods_router.router, prefix="/api/v1")
```

- [ ] **Step 4: Write and run tests**

`backend/tests/test_periods.py`:
```python
import uuid
from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.auth import hash_password, create_access_token
from app.services.account import seed_skr_for_mandant
from app.services.period import get_or_create_period


async def _setup(session):
    user = User(email=f"p{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    mandant = Mandant(name="Period GmbH", skr_variant="skr03")
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")
    token = create_access_token(user.id, mandant.id)
    return {"Authorization": f"Bearer {token}"}, user, mandant


async def test_period_auto_created_on_first_booking(client, db_session):
    headers, user, mandant = await _setup(db_session)
    from sqlalchemy import select
    from app.models.account import ChartOfAccount
    accs = (await db_session.execute(
        select(ChartOfAccount).where(ChartOfAccount.mandant_id == mandant.id).limit(2)
    )).scalars().all()
    await client.post("/api/v1/bookings", json={
        "date_booking": "2026-03-01",
        "amount_cents": 10000,
        "coa_id": str(accs[0].id),
        "counter_coa_id": str(accs[1].id),
    }, headers=headers)
    periods = (await client.get("/api/v1/periods", headers=headers)).json()
    # Period auto-created by post_booking; here we check via direct service
    period = await get_or_create_period(db_session, mandant.id, 2026, 3)
    assert period.year == 2026
    assert period.month == 3


async def test_lock_then_archive_period(client, db_session):
    headers, user, mandant = await _setup(db_session)
    period = await get_or_create_period(db_session, mandant.id, 2025, 12)
    lock_resp = await client.post(f"/api/v1/periods/{period.id}/lock", headers=headers)
    assert lock_resp.status_code == 200
    assert lock_resp.json()["status"] == "locked"
    archive_resp = await client.post(f"/api/v1/periods/{period.id}/archive", headers=headers)
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == "archived"


async def test_cannot_post_booking_into_locked_period(client, db_session):
    headers, user, mandant = await _setup(db_session)
    from sqlalchemy import select
    from app.models.account import ChartOfAccount
    accs = (await db_session.execute(
        select(ChartOfAccount).where(ChartOfAccount.mandant_id == mandant.id).limit(2)
    )).scalars().all()
    period = await get_or_create_period(db_session, mandant.id, 2025, 6)
    await db_session.flush()
    lock_resp = await client.post(f"/api/v1/periods/{period.id}/lock", headers=headers)
    assert lock_resp.json()["status"] == "locked"
    # Try to create and post a booking in the locked period
    resp = await client.post("/api/v1/bookings", json={
        "date_booking": "2025-06-15",
        "amount_cents": 10000,
        "coa_id": str(accs[0].id),
        "counter_coa_id": str(accs[1].id),
    }, headers=headers)
    booking_id = resp.json()["id"]
    post_resp = await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)
    assert post_resp.status_code == 422
    assert post_resp.json()["error"]["code"] == "PERIOD_LOCKED"
```

```bash
cd backend && uv run pytest tests/test_periods.py -v
```
Expected: 3 tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/period.py backend/app/services/period.py \
        backend/app/routers/periods.py backend/app/main.py \
        backend/tests/test_periods.py
git commit -m "feat(backend): Add accounting period locking and archiving"
```

---

## Task 11: Reports — EÜR + Kontoauszug

**Files:**
- Create: `backend/app/schemas/reports.py`
- Create: `backend/app/services/reports.py`
- Create: `backend/app/routers/reports.py`
- Create: `backend/tests/test_reports.py`

- [ ] **Step 1: Create backend/app/schemas/reports.py**

```python
from decimal import Decimal
from pydantic import BaseModel
import uuid


class EURLineItem(BaseModel):
    account_number: str
    account_name: str
    gross_cents: int
    tax_cents: int
    net_cents: int
    private_deduction_cents: int
    reportable_cents: int


class EURResponse(BaseModel):
    date_from: str
    date_to: str
    betriebseinnahmen_cents: int
    betriebsausgaben_cents: int
    ust_cents: int       # virtual account 3806 — USt from income accounts
    vst_19_cents: int    # virtual account 1401 — Vorsteuer 19%
    vst_7_cents: int     # virtual account 1406 — Vorsteuer 7%
    items: list[EURLineItem]


class KontoauszugLine(BaseModel):
    booking_id: uuid.UUID
    date_booking: str
    document_number: str | None
    notes: str | None
    debit_cents: int
    credit_cents: int
    running_balance_cents: int
    entry_number: int | None
    status: str


class KontoauszugResponse(BaseModel):
    account_id: uuid.UUID
    account_number: str
    account_name: str
    date_from: str
    date_to: str
    opening_balance_cents: int
    closing_balance_cents: int
    lines: list[KontoauszugLine]
```

- [ ] **Step 2: Create backend/app/services/reports.py**

```python
import uuid
from decimal import Decimal
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.account import ChartOfAccount
from app.models.booking import Booking
from app.schemas.reports import EURLineItem, EURResponse, KontoauszugLine, KontoauszugResponse


async def generate_eur(
    session: AsyncSession, mandant_id: uuid.UUID, date_from: str, date_to: str
) -> EURResponse:
    # Fetch all posted entry bookings in the period
    result = await session.execute(
        select(Booking, ChartOfAccount)
        .join(ChartOfAccount, Booking.coa_id == ChartOfAccount.id)
        .where(
            Booking.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            Booking.date_booking >= date_from,
            Booking.date_booking <= date_to,
        )
        .order_by(ChartOfAccount.account_number)
    )
    rows = result.all()

    # Aggregate by account
    aggregates: dict[str, dict] = {}
    for booking, account in rows:
        key = account.account_number
        if key not in aggregates:
            aggregates[key] = {
                "account": account,
                "gross_cents": 0,
                "tax_cents": 0,
            }
        aggregates[key]["gross_cents"] += booking.amount_cents
        aggregates[key]["tax_cents"] += booking.tax_amount_cents or 0

    items = []
    betriebseinnahmen = 0
    betriebsausgaben = 0
    ust_cents = 0
    vst_19_cents = 0
    vst_7_cents = 0

    for acct_num, agg in aggregates.items():
        account: ChartOfAccount = agg["account"]
        gross = agg["gross_cents"]
        tax = agg["tax_cents"]
        net = gross - tax
        private = int(net * account.private_share_percent / 100)
        reportable = net - private

        # Virtual accounts
        if account.account_class.startswith("8"):  # Revenue (Erlöskonten)
            betriebseinnahmen += reportable
            ust_cents += tax
        elif account.account_class.startswith("4") or account.account_class.startswith("5") or account.account_class.startswith("6"):
            betriebsausgaben += reportable
            if account.tax_rate == Decimal("0.19"):
                vst_19_cents += tax
            elif account.tax_rate == Decimal("0.07"):
                vst_7_cents += tax

        items.append(EURLineItem(
            account_number=acct_num,
            account_name=account.name,
            gross_cents=gross,
            tax_cents=tax,
            net_cents=net,
            private_deduction_cents=private,
            reportable_cents=reportable,
        ))

    return EURResponse(
        date_from=date_from,
        date_to=date_to,
        betriebseinnahmen_cents=betriebseinnahmen,
        betriebsausgaben_cents=betriebsausgaben,
        ust_cents=ust_cents,
        vst_19_cents=vst_19_cents,
        vst_7_cents=vst_7_cents,
        items=items,
    )


async def generate_kontoauszug(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    account_id: uuid.UUID,
    date_from: str,
    date_to: str,
) -> KontoauszugResponse:
    from app.errors import NotFoundError
    acc_result = await session.execute(
        select(ChartOfAccount).where(
            ChartOfAccount.id == account_id, ChartOfAccount.mandant_id == mandant_id
        )
    )
    account = acc_result.scalar_one_or_none()
    if not account:
        raise NotFoundError(f"Account {account_id} not found.")

    result = await session.execute(
        select(Booking).where(
            Booking.mandant_id == mandant_id,
            Booking.status == "posted",
            Booking.booking_type == "entry",
            (Booking.coa_id == account_id) | (Booking.counter_coa_id == account_id),
            Booking.date_booking >= date_from,
            Booking.date_booking <= date_to,
        ).order_by(Booking.date_booking, Booking.entry_number)
    )
    bookings = list(result.scalars().all())

    lines = []
    running_balance = 0
    for b in bookings:
        debit = b.amount_cents if b.coa_id == account_id else 0
        credit = b.amount_cents if b.counter_coa_id == account_id else 0
        running_balance += debit - credit
        lines.append(KontoauszugLine(
            booking_id=b.id,
            date_booking=str(b.date_booking),
            document_number=b.document_number,
            notes=b.notes,
            debit_cents=debit,
            credit_cents=credit,
            running_balance_cents=running_balance,
            entry_number=b.entry_number,
            status=b.status,
        ))

    return KontoauszugResponse(
        account_id=account_id,
        account_number=account.account_number,
        account_name=account.name,
        date_from=date_from,
        date_to=date_to,
        opening_balance_cents=0,
        closing_balance_cents=running_balance,
        lines=lines,
    )
```

- [ ] **Step 3: Create backend/app/routers/reports.py and register in main.py**

```python
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_mandant_id
from app.schemas.reports import EURResponse, KontoauszugResponse
from app.services.reports import generate_eur, generate_kontoauszug

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/eur", response_model=EURResponse)
async def eur(
    date_from: str = Query(...),
    date_to: str = Query(...),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> EURResponse:
    return await generate_eur(session, mandant_id, date_from, date_to)


@router.get("/account-statement", response_model=KontoauszugResponse)
async def account_statement(
    account_id: uuid.UUID = Query(...),
    date_from: str = Query(...),
    date_to: str = Query(...),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> KontoauszugResponse:
    return await generate_kontoauszug(session, mandant_id, account_id, date_from, date_to)
```

In `main.py`:
```python
from app.routers import reports as reports_router
app.include_router(reports_router.router, prefix="/api/v1")
```

- [ ] **Step 4: Write EÜR critical-path tests (100% coverage required)**

`backend/tests/test_reports.py`:
```python
import uuid
from decimal import Decimal
from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.auth import hash_password, create_access_token
from app.services.account import seed_skr_for_mandant
from sqlalchemy import select
from app.models.account import ChartOfAccount


async def _setup_with_bookings(session, client):
    user = User(email=f"r{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    mandant = Mandant(name="Report GmbH", skr_variant="skr03")
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")
    token = create_access_token(user.id, mandant.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch revenue account (8xxx) and expense account (4xxx)
    accs = (await session.execute(
        select(ChartOfAccount).where(ChartOfAccount.mandant_id == mandant.id)
    )).scalars().all()
    revenue = next(a for a in accs if a.account_class.startswith("8"))
    expense = next(a for a in accs if a.account_class.startswith("4"))
    bank = next(a for a in accs if a.account_number == "1200")

    # Create and post a revenue booking: bank(debit) / revenue(credit) 1190 EUR (incl. 19% USt)
    r1 = await client.post("/api/v1/bookings", json={
        "date_booking": "2026-01-15",
        "amount_cents": 119000,
        "coa_id": str(bank.id),
        "counter_coa_id": str(revenue.id),
        "tax_rate": "0.19",
        "tax_amount_cents": 19000,
        "tax_key_code": 9,
    }, headers=headers)
    await client.post(f"/api/v1/bookings/{r1.json()['id']}/post", headers=headers)

    # Create and post an expense booking: expense(debit) / bank(credit) 595 EUR (incl. 19% VSt)
    r2 = await client.post("/api/v1/bookings", json={
        "date_booking": "2026-01-20",
        "amount_cents": 59500,
        "coa_id": str(expense.id),
        "counter_coa_id": str(bank.id),
        "tax_rate": "0.19",
        "tax_amount_cents": 9500,
        "tax_key_code": 9,
    }, headers=headers)
    await client.post(f"/api/v1/bookings/{r2.json()['id']}/post", headers=headers)

    return headers, mandant, revenue, expense, bank


async def test_eur_betriebseinnahmen(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(db_session, client)
    resp = await client.get("/api/v1/reports/eur?date_from=2026-01-01&date_to=2026-01-31", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # Net revenue: 119000 - 19000 = 100000 cents
    assert data["betriebseinnahmen_cents"] == 100000


async def test_eur_betriebsausgaben(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(db_session, client)
    resp = await client.get("/api/v1/reports/eur?date_from=2026-01-01&date_to=2026-01-31", headers=headers)
    data = resp.json()
    # Net expense: 59500 - 9500 = 50000 cents
    assert data["betriebsausgaben_cents"] == 50000


async def test_eur_ust_virtual_account(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(db_session, client)
    resp = await client.get("/api/v1/reports/eur?date_from=2026-01-01&date_to=2026-01-31", headers=headers)
    data = resp.json()
    assert data["ust_cents"] == 19000   # USt from revenue bookings


async def test_eur_private_share_deduction(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(db_session, client)
    # Set 50% private share on expense account
    await client.patch(f"/api/v1/accounts/{expense.id}", json={"private_share_percent": 50}, headers=headers)
    resp = await client.get("/api/v1/reports/eur?date_from=2026-01-01&date_to=2026-01-31", headers=headers)
    data = resp.json()
    # Net expense 50000 * 50% private = 25000 reportable
    item = next(i for i in data["items"] if i["account_number"] == expense.account_number)
    assert item["reportable_cents"] == 25000


async def test_kontoauszug_running_balance(client, db_session):
    headers, mandant, revenue, expense, bank = await _setup_with_bookings(db_session, client)
    resp = await client.get(
        f"/api/v1/reports/account-statement?account_id={bank.id}&date_from=2026-01-01&date_to=2026-01-31",
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["lines"]) == 2
    # First line: bank debited 119000
    assert data["lines"][0]["debit_cents"] == 119000
    # Second line: bank credited 59500
    assert data["lines"][1]["credit_cents"] == 59500
    # Closing balance: 119000 - 59500 = 59500
    assert data["closing_balance_cents"] == 59500
```

```bash
cd backend && uv run pytest tests/test_reports.py -v
```
Expected: 5 tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/reports.py backend/app/services/reports.py \
        backend/app/routers/reports.py backend/app/main.py \
        backend/tests/test_reports.py
git commit -m "feat(backend): Add EÜR and Kontoauszug reports with PrivateShare and virtual accounts"
```

---

## Task 12: DATEV ASCII Export

**Files:**
- Create: `backend/app/services/datev.py`
- Create: `backend/app/routers/datev.py`
- Create: `backend/tests/test_datev.py`

- [ ] **Step 1: Create backend/app/services/datev.py**

```python
import io
import uuid
from datetime import date, datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.account import ChartOfAccount
from app.models.booking import Booking
from app.models.mandant import Mandant


def _format_amount(cents: int) -> str:
    """Format cents as German decimal string: 119000 → '1190,00'"""
    return f"{cents // 100},{cents % 100:02d}"


def _datev_date(d: date) -> str:
    """DDMM format for Belegdatum"""
    return d.strftime("%d%m")


def _datev_leistungsdatum(d: date | None) -> str:
    """DDMMYYYY for Leistungsdatum"""
    if d is None:
        return ""
    return d.strftime("%d%m%Y")


def _tax_key_to_bu(tax_key_code: int | None) -> str:
    if tax_key_code in (9, 10):
        return str(tax_key_code)
    return ""


async def generate_datev_export(
    session: AsyncSession,
    mandant_id: uuid.UUID,
    date_from: str,
    date_to: str,
) -> bytes:
    mandant_result = await session.execute(
        select(Mandant).where(Mandant.id == mandant_id)
    )
    mandant = mandant_result.scalar_one()

    result = await session.execute(
        select(Booking, ChartOfAccount.account_number.label("coa_number"),)
        .join(ChartOfAccount, Booking.coa_id == ChartOfAccount.id)
        .where(
            Booking.mandant_id == mandant_id,
            Booking.booking_type == "entry",
            Booking.status == "posted",
            Booking.date_booking >= date_from,
            Booking.date_booking <= date_to,
        )
        .order_by(Booking.entry_number)
    )
    rows = result.all()

    # Fetch counter account numbers
    counter_ids = [r.Booking.counter_coa_id for r in rows if r.Booking.counter_coa_id]
    counter_map: dict[uuid.UUID, str] = {}
    if counter_ids:
        counter_result = await session.execute(
            select(ChartOfAccount.id, ChartOfAccount.account_number).where(
                ChartOfAccount.id.in_(counter_ids)
            )
        )
        counter_map = {row.id: row.account_number for row in counter_result}

    now = datetime.now(timezone.utc)
    fiscal_start = date(now.year, mandant.fiscal_year_start, 1)
    wj_anfang = fiscal_start.strftime("%Y%m%d")
    wj_ende = date(fiscal_start.year + (1 if mandant.fiscal_year_start > 1 else 0),
                   (mandant.fiscal_year_start - 1) or 12, 31).strftime("%Y%m%d")

    beraternr = mandant.datev_beraternummer or "70000"
    mandantennr = mandant.datev_mandantennummer or "99999"

    lines: list[str] = []

    # EXTF v700 header line 1 (124 semicolon-separated fields, most empty)
    header1 = (
        f'"EXTF";700;21;"Buchungsstapel";5;'
        f'{now.strftime("%Y%m%d%H%M%S%f")[:20]};;'
        f'"{beraternr}";"{mandantennr}";'
        f'{mandant.fiscal_year_start};12;'
        f'"{wj_anfang}";"{wj_ende}";'
        f'"WebBuchhaltung";;1;0;0;0;;1;EUR;;;'
    )
    lines.append(header1)

    # Header line 2 — column names (only first 14 needed, rest empty)
    lines.append(
        "Umsatz (ohne Soll/Haben-Kz);Soll/Haben-Kennzeichen;WKZ Umsatz;Kurs;"
        "Basis-Umsatz;WKZ Basis-Umsatz;Konto;Gegenkonto (ohne BU-Schlüssel);"
        "BU-Schlüssel;Belegdatum;Belegfeld 1;Belegfeld 2;Skonto;Buchungstext"
    )

    for row in rows:
        b: Booking = row.Booking
        coa_number: str = row.coa_number
        counter_number = counter_map.get(b.counter_coa_id, "") if b.counter_coa_id else ""

        fields = [
            _format_amount(b.amount_cents),   # Umsatz
            "S",                               # Soll/Haben — coa_id is always Soll
            b.currency,                        # WKZ
            "",                                # Kurs
            "",                                # Basis-Umsatz
            "",                                # WKZ Basis-Umsatz
            coa_number,                        # Konto (Soll)
            counter_number,                    # Gegenkonto (Haben)
            _tax_key_to_bu(b.tax_key_code),   # BU-Schlüssel
            _datev_date(b.date_booking),       # Belegdatum DDMM
            (b.document_number or "")[:12],    # Belegfeld 1
            "",                                # Belegfeld 2
            "",                                # Skonto
            (b.notes or "")[:60],             # Buchungstext
        ]
        lines.append(";".join(fields))

    content = "\r\n".join(lines) + "\r\n"
    return content.encode("cp1252", errors="replace")
```

- [ ] **Step 2: Create backend/app/routers/datev.py and register in main.py**

```python
import uuid
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_mandant_id
from app.services.datev import generate_datev_export
from pydantic import BaseModel

router = APIRouter(prefix="/datev", tags=["datev"])


class DatevExportRequest(BaseModel):
    date_from: str
    date_to: str


@router.post("/export")
async def export(
    body: DatevExportRequest,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> Response:
    content = await generate_datev_export(session, mandant_id, body.date_from, body.date_to)
    filename = f"EXTF_{body.date_from}_{body.date_to}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

In `main.py`:
```python
from app.routers import datev as datev_router
app.include_router(datev_router.router, prefix="/api/v1")
```

- [ ] **Step 3: Write DATEV critical-path tests (100% coverage required)**

`backend/tests/test_datev.py`:
```python
import uuid
from app.models.mandant import Mandant
from app.models.user import User, UserMandant
from app.services.auth import hash_password, create_access_token
from app.services.account import seed_skr_for_mandant
from app.services.datev import _format_amount, _datev_date, _tax_key_to_bu
from sqlalchemy import select
from app.models.account import ChartOfAccount
from datetime import date


async def _setup_posted_booking(session, client):
    user = User(email=f"d{uuid.uuid4()}@x.com", hashed_password=hash_password("pw"))
    session.add(user)
    mandant = Mandant(
        name="DATEV GmbH", skr_variant="skr03",
        datev_beraternummer="70000", datev_mandantennummer="12345"
    )
    session.add(mandant)
    await session.flush()
    session.add(UserMandant(user_id=user.id, mandant_id=mandant.id, role="admin"))
    await session.flush()
    await seed_skr_for_mandant(session, mandant.id, "skr03")
    accs = (await session.execute(
        select(ChartOfAccount).where(ChartOfAccount.mandant_id == mandant.id).limit(2)
    )).scalars().all()
    token = create_access_token(user.id, mandant.id)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/api/v1/bookings", json={
        "date_booking": "2026-01-15",
        "amount_cents": 119000,
        "document_number": "RE2026-001",
        "notes": "Testbuchung",
        "coa_id": str(accs[0].id),
        "counter_coa_id": str(accs[1].id),
        "tax_key_code": 9,
    }, headers=headers)
    booking_id = resp.json()["id"]
    await client.post(f"/api/v1/bookings/{booking_id}/post", headers=headers)
    return headers, mandant, accs[0], accs[1]


def test_format_amount():
    assert _format_amount(119000) == "1190,00"
    assert _format_amount(100) == "1,00"
    assert _format_amount(50) == "0,50"


def test_datev_date_format():
    assert _datev_date(date(2026, 1, 15)) == "1501"
    assert _datev_date(date(2026, 12, 31)) == "3112"


def test_tax_key_mapping():
    assert _tax_key_to_bu(9) == "9"
    assert _tax_key_to_bu(10) == "10"
    assert _tax_key_to_bu(None) == ""
    assert _tax_key_to_bu(99) == ""


async def test_export_returns_cp1252_csv(client, db_session):
    headers, mandant, acc1, acc2 = await _setup_posted_booking(db_session, client)
    resp = await client.post("/api/v1/datev/export", json={
        "date_from": "2026-01-01", "date_to": "2026-01-31"
    }, headers=headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    content = resp.content.decode("cp1252")
    assert "EXTF" in content
    assert "1190,00" in content


async def test_export_soll_haben_kennzeichen(client, db_session):
    headers, mandant, acc1, acc2 = await _setup_posted_booking(db_session, client)
    resp = await client.post("/api/v1/datev/export", json={
        "date_from": "2026-01-01", "date_to": "2026-01-31"
    }, headers=headers)
    lines = resp.content.decode("cp1252").splitlines()
    data_line = lines[2]  # line 0=header1, 1=header2, 2=first data row
    fields = data_line.split(";")
    assert fields[1] == "S"   # Soll/Haben = S (coa_id is always Soll)
    assert fields[6] == acc1.account_number   # Konto
    assert fields[7] == acc2.account_number   # Gegenkonto


async def test_export_document_number_truncated_to_12(client, db_session):
    headers, mandant, acc1, acc2 = await _setup_posted_booking(db_session, client)
    resp = await client.post("/api/v1/datev/export", json={
        "date_from": "2026-01-01", "date_to": "2026-01-31"
    }, headers=headers)
    lines = resp.content.decode("cp1252").splitlines()
    data_line = lines[2]
    fields = data_line.split(";")
    assert len(fields[10]) <= 12  # Belegfeld 1 ≤ 12 chars


async def test_export_only_posted_entry_bookings(client, db_session):
    headers, mandant, acc1, acc2 = await _setup_posted_booking(db_session, client)
    # Create a draft booking — should NOT appear in export
    await client.post("/api/v1/bookings", json={
        "date_booking": "2026-01-20",
        "amount_cents": 50000,
        "coa_id": str(acc1.id),
        "counter_coa_id": str(acc2.id),
    }, headers=headers)
    resp = await client.post("/api/v1/datev/export", json={
        "date_from": "2026-01-01", "date_to": "2026-01-31"
    }, headers=headers)
    lines = [l for l in resp.content.decode("cp1252").splitlines() if l and not l.startswith('"EXTF') and not l.startswith('Umsatz')]
    assert len(lines) == 1  # only the posted booking
```

```bash
cd backend && uv run pytest tests/test_datev.py -v
```
Expected: 7 tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/datev.py backend/app/routers/datev.py \
        backend/app/main.py backend/tests/test_datev.py
git commit -m "feat(backend): Add DATEV ASCII export (EXTF v700, CP1252, Soll/Haben mapping)"
```

---

## Task 13: React Skeleton

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/nginx.conf`
- Create: `frontend/Dockerfile`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/src/pages/DashboardPage.tsx`
- Create: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Create frontend/package.json**

```json
{
  "name": "webbuchhaltung-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "generate-api": "openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.d.ts"
  },
  "dependencies": {
    "@mui/material": "^6.0.0",
    "@mui/icons-material": "^6.0.0",
    "@emotion/react": "^11.11.0",
    "@emotion/styled": "^11.11.0",
    "@tanstack/react-query": "^5.0.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0",
    "zustand": "^4.5.0",
    "react-hook-form": "^7.51.0",
    "zod": "^3.23.0",
    "@hookform/resolvers": "^3.3.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "openapi-typescript": "^6.7.0"
  }
}
```

- [ ] **Step 2: Create frontend/vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Step 3: Create frontend/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Create frontend/src/main.tsx**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material'
import App from './App'

const queryClient = new QueryClient()
const theme = createTheme({ palette: { mode: 'dark' } })

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>
)
```

- [ ] **Step 5: Create frontend/src/App.tsx**

```tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import Layout from './components/Layout'

function useAuth() {
  return !!localStorage.getItem('access_token')
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return useAuth() ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
```

- [ ] **Step 6: Create remaining skeleton files**

`frontend/src/pages/LoginPage.tsx`:
```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, Button, TextField, Typography, Paper } from '@mui/material'
import axios from 'axios'

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    try {
      const { data } = await axios.post('/api/v1/auth/login', { email, password })
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      navigate('/')
    } catch {
      setError('Invalid email or password.')
    }
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
      <Paper sx={{ p: 4, width: 360 }}>
        <Typography variant="h5" gutterBottom>WebBuchhaltung</Typography>
        <Box component="form" onSubmit={handleLogin} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField label="E-Mail" value={email} onChange={e => setEmail(e.target.value)} type="email" required />
          <TextField label="Passwort" value={password} onChange={e => setPassword(e.target.value)} type="password" required />
          {error && <Typography color="error">{error}</Typography>}
          <Button type="submit" variant="contained">Anmelden</Button>
        </Box>
      </Paper>
    </Box>
  )
}
```

`frontend/src/pages/DashboardPage.tsx`:
```tsx
import { Typography, Box } from '@mui/material'

export default function DashboardPage() {
  return (
    <Box>
      <Typography variant="h4">Dashboard</Typography>
      <Typography color="text.secondary">Phase 1 skeleton — full UI in Phase 2.</Typography>
    </Box>
  )
}
```

`frontend/src/components/Layout.tsx`:
```tsx
import { Box, AppBar, Toolbar, Typography, Button } from '@mui/material'
import { useNavigate } from 'react-router-dom'

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  function handleLogout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    navigate('/login')
  }
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>WebBuchhaltung</Typography>
          <Button color="inherit" onClick={handleLogout}>Abmelden</Button>
        </Toolbar>
      </AppBar>
      <Box component="main" sx={{ p: 3, flexGrow: 1 }}>{children}</Box>
    </Box>
  )
}
```

- [ ] **Step 7: Create frontend/Dockerfile and nginx.conf**

`frontend/Dockerfile`:
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

`frontend/nginx.conf`:
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 8: Add frontend/.gitignore**

```
node_modules/
dist/
src/api/schema.d.ts
```

- [ ] **Step 9: Verify build**

```bash
cd frontend && npm install && npm run build
```
Expected: build succeeds, `dist/` created.

- [ ] **Step 10: Start full stack with Docker Compose**

```bash
docker compose up --build
```

Navigate to `http://localhost:3000`. Login page should render. Backend health check:
```bash
curl http://localhost:8000/health
```
Expected: `{"status":"ok"}`

- [ ] **Step 11: Commit**

```bash
git add frontend/ docker-compose.yml
git commit -m "feat(frontend): Add React 18 skeleton — MUI v6, TanStack Query, login page, Docker Compose"
```

---

## Self-Review Checklist

Run after all tasks are complete before marking Phase 1 done:

```bash
cd backend && uv run pytest --cov=app --cov-report=term-missing
```

Verify:
- [ ] Overall backend coverage ≥ 80%
- [ ] `services/booking.py` — 100% (post, reverse, GoBD)
- [ ] `services/datev.py` — 100% (CP1252, field lengths, S/H Kennzeichen)
- [ ] `services/reports.py` — 100% (EÜR, PrivateShare, virtual accounts)
- [ ] Mandant isolation: no cross-mandant data leak in any service method
- [ ] Sequential entry numbers: no gaps, no duplicates

```bash
cd frontend && npm run build  # TypeScript strict mode must pass
```


---

## Addendum A: Admin Router (gap fix)

Add to `backend/app/routers/admin.py` — implement in Task 5 after mandants router:

```python
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user
from app.errors import ForbiddenError, NotFoundError
from app.models.user import User, UserMandant
from app.schemas.auth import UserResponse
from app.services.auth import hash_password
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/admin", tags=["admin"])


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserMandantAssign(BaseModel):
    user_id: uuid.UUID
    role: str = "bookkeeper"


async def _require_admin(
    mandant_id: uuid.UUID,
    current_user: User,
    session: AsyncSession,
) -> None:
    result = await session.execute(
        select(UserMandant).where(
            UserMandant.user_id == current_user.id,
            UserMandant.mandant_id == mandant_id,
            UserMandant.role == "admin",
        )
    )
    if not result.scalar_one_or_none():
        raise ForbiddenError("Admin role required.")


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list:
    result = await session.execute(select(User))
    return list(result.scalars().all())


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    user = User(email=body.email, hashed_password=hash_password(body.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(f"User {user_id} not found.")
    if "is_active" in body:
        user.is_active = body["is_active"]
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/mandants/{mandant_id}/users")
async def assign_user_to_mandant(
    mandant_id: uuid.UUID,
    body: UserMandantAssign,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await _require_admin(mandant_id, current_user, session)
    link = UserMandant(user_id=body.user_id, mandant_id=mandant_id, role=body.role)
    session.add(link)
    await session.commit()
    return {"message": "User assigned."}
```

Register in `main.py`:
```python
from app.routers import admin as admin_router
app.include_router(admin_router.router, prefix="/api/v1")
```

---

## Addendum B: Booking Groups Endpoints (gap fix)

Replace the empty `groups_router` in `backend/app/routers/bookings.py` with:

```python
from app.models.booking import BookingGroup
from sqlalchemy import select

groups_router = APIRouter(prefix="/booking-groups", tags=["booking-groups"])


@groups_router.get("", response_model=list[BookingGroupResponse])
async def list_groups(
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> list:
    result = await session.execute(
        select(BookingGroup).where(BookingGroup.mandant_id == mandant_id)
    )
    return list(result.scalars().all())


@groups_router.post("", response_model=BookingGroupResponse, status_code=201)
async def create_group(
    body: BookingGroupCreate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> BookingGroup:
    from datetime import datetime, timezone
    group = BookingGroup(
        mandant_id=mandant_id,
        description=body.description,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return group


@groups_router.get("/{group_id}/bookings", response_model=list[BookingResponse])
async def list_group_bookings(
    group_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> list:
    result = await session.execute(
        select(Booking).where(
            Booking.booking_group_id == group_id,
            Booking.mandant_id == mandant_id,
        )
    )
    return list(result.scalars().all())
```
