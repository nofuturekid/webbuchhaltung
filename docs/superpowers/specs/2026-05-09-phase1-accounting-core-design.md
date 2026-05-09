# Phase 1 — Accounting Core: Design Spec

**Date:** 2026-05-09
**Status:** Approved
**Scope:** Backend API + React skeleton + Docker Compose (Tier 2)

---

## 1. Goals & Out-of-Scope

### Phase 1 delivers
- Multi-Mandant FastAPI backend with JWT auth
- Full data model: Mandant, User, ChartOfAccounts, TaxKeys, Bookings, AccountingPeriod, AuditLog
- Seed data: SKR03, SKR04, SKR07 (~1000 accounts each), DATEV BU-Schlüssel
- Manual booking entry (entry type), booking lifecycle (draft → posted → reversed)
- GoBD compliance: immutability, sequential numbering, audit trail, period locking
- DATEV ASCII export (EXTF v700, CP1252)
- EÜR report + Kontoauszug report
- Docker Compose dev environment (PostgreSQL 16)
- React 18 skeleton (Vite + MUI v6 + TanStack Query + openapi-typescript)

### Explicitly out of scope in Phase 1
- Bank transaction import (FinTS, PDF, MT940, WISO) — Phase 2
- `bank` booking type creation via API — model exists, creation deferred to Phase 2
- Admin UI / DB-stored settings — Phase 2
- Tier 1 single-process deployment — Phase 2
- Invoices, Contacts, Dunning — Phase 3
- LLM integration, Asset management — Phase 4
- Kubernetes / Helm — Phase 5
- Jahresabschluss, ELSTER, Payroll — permanently out of scope

---

## 2. Architecture

### Deployment
Minimum deployment is Docker Compose. SQLite is not supported.

```
docker-compose.yml     PostgreSQL 16 + backend (8000) + frontend/nginx (3000)
```

### Backend layout
```
backend/
├── app/
│   ├── main.py           # FastAPI app factory, exception handlers
│   ├── config.py         # pydantic-settings bootstrap config
│   ├── database.py       # Async engine factory (postgresql+asyncpg / mysql+aiomysql)
│   ├── models/
│   │   ├── base.py       # DeclarativeBase + TimestampMixin (created_at, updated_at)
│   │   ├── mandant.py
│   │   ├── user.py
│   │   ├── account.py
│   │   ├── booking.py
│   │   └── period.py
│   ├── schemas/          # Pydantic v2, one file per domain
│   ├── routers/          # One file per domain, all under /api/v1/
│   ├── services/         # Business logic — no DB access in routers
│   └── dependencies.py   # get_db(), get_current_user(), get_mandant()
├── alembic/
│   ├── env.py            # Multi-DB aware (PostgreSQL + MariaDB)
│   └── versions/
├── seed/
│   ├── skr03.json
│   ├── skr04.json
│   ├── skr07.json
│   └── tax_keys.json
├── tests/
└── pyproject.toml        # uv-managed
```

### Frontend skeleton layout
```
frontend/
├── src/
│   ├── api/              # openapi-typescript generated — never manually written
│   ├── components/       # Shared MUI v6 components
│   ├── pages/            # Placeholder stubs for all Phase 1 views
│   └── main.tsx          # TanStack Query Provider + Zustand + React Router
├── vite.config.ts
└── package.json
```

### Key principles
- `mandant_id: UUID` always comes from the JWT claim, never from the request body
- `DATABASE_URL` env var drives DB backend: `postgresql+asyncpg://` or `mysql+aiomysql://`
- Seed data loaded via a dedicated idempotent Alembic migration, not startup code
- Phase 1 has no background worker — DATEV export and EÜR are synchronous API calls

### Bootstrap environment variables
```
DATABASE_URL      # DB connection string (required)
SECRET_KEY        # JWT signing key (required)
STORAGE_BACKEND   # local | s3 (required, Phase 1: always local)
```

---

## 3. Data Model

### 3.1 Mandant & User

```sql
mandants
  id                    UUID PRIMARY KEY
  name                  TEXT NOT NULL
  steuernummer          TEXT
  ust_id                TEXT
  datev_beraternummer   TEXT
  datev_mandantennummer TEXT
  fiscal_year_start     INT DEFAULT 1          -- 1–12
  skr_variant           ENUM('skr03','skr04','skr07') NOT NULL
  is_active             BOOLEAN DEFAULT true
  created_at            TIMESTAMPTZ NOT NULL
  updated_at            TIMESTAMPTZ NOT NULL

users
  id              UUID PRIMARY KEY
  email           TEXT UNIQUE NOT NULL
  hashed_password TEXT NOT NULL
  is_active       BOOLEAN DEFAULT true
  created_at      TIMESTAMPTZ NOT NULL
  updated_at      TIMESTAMPTZ NOT NULL

user_mandants                                  -- many-to-many with role
  user_id     UUID REFERENCES users NOT NULL
  mandant_id  UUID REFERENCES mandants NOT NULL
  role        ENUM('admin','bookkeeper','readonly') DEFAULT 'bookkeeper'
  PRIMARY KEY (user_id, mandant_id)
```

### 3.2 Chart of Accounts & Tax Keys

```sql
chart_of_accounts
  id                   UUID PRIMARY KEY
  mandant_id           UUID REFERENCES mandants NOT NULL
  account_number       CHAR(4) NOT NULL
  name                 TEXT NOT NULL
  account_class        TEXT NOT NULL      -- '0xxx'..'9xxx'
  tax_type             TEXT               -- USt / VSt / steuerfrei / keine
  skr_variant          ENUM('skr03','skr04','skr07','custom') NOT NULL
  is_custom            BOOLEAN DEFAULT false
  private_share_percent INT DEFAULT 0
  is_active            BOOLEAN DEFAULT true
  created_at           TIMESTAMPTZ NOT NULL
  updated_at           TIMESTAMPTZ NOT NULL
  UNIQUE (mandant_id, account_number)
  CHECK (private_share_percent BETWEEN 0 AND 100)

-- Business rule (enforced at service layer):
--   is_custom = false → only private_share_percent and is_active are editable

tax_keys                                   -- DATEV BU-Schlüssel, mandant-independent
  code         INT PRIMARY KEY             -- official DATEV code
  description  TEXT NOT NULL
  tax_rate     DECIMAL(5,4)               -- NULL if no rate applies
  tax_type     ENUM('USt','VSt','steuerfrei','§13b','keine','UStfrei') NOT NULL
```

### 3.3 Bookings

```sql
booking_groups
  id          UUID PRIMARY KEY
  mandant_id  UUID REFERENCES mandants NOT NULL
  description TEXT
  created_at  TIMESTAMPTZ NOT NULL

bookings
  id                UUID PRIMARY KEY
  mandant_id        UUID REFERENCES mandants NOT NULL
  booking_type      ENUM('bank','entry') NOT NULL
  booking_group_id  UUID REFERENCES booking_groups NULL
  parent_booking_id UUID REFERENCES bookings NULL     -- entry → parent bank booking
  reversal_of_id    UUID REFERENCES bookings NULL     -- Stornobuchung

  -- Both types
  date_booking   DATE NOT NULL
  date_tax       DATE                   -- DATEV Leistungsdatum / Steuerperiode
  amount_cents   BIGINT NOT NULL        -- always positive; direction via coa/counter_coa
  currency       CHAR(3) DEFAULT 'EUR'
  document_number TEXT
  status         ENUM('draft','posted','reversed') DEFAULT 'draft'
  notes          TEXT
  entry_number   BIGINT                 -- GoBD §11: assigned from DB sequence on post
  created_at     TIMESTAMPTZ NOT NULL
  updated_at     TIMESTAMPTZ NOT NULL
  created_by     UUID REFERENCES users NOT NULL

  -- entry type only (NULL for bank)
  coa_id           UUID REFERENCES chart_of_accounts NULL  -- Soll (debit)
  counter_coa_id   UUID REFERENCES chart_of_accounts NULL  -- Haben (credit)
  tax_rate         DECIMAL(5,4)
  tax_amount_cents BIGINT
  tax_key_code     INT REFERENCES tax_keys NULL
  contact_id       UUID NULL                               -- FK → contacts (Phase 3)

  -- bank type only (NULL for entry)
  bank_account_id     UUID NULL          -- FK → bank_accounts (Phase 2)
  recipient_name      TEXT
  foreign_bank_account TEXT

  CHECK (amount_cents > 0)
  CHECK (booking_type != 'entry' OR (coa_id IS NOT NULL AND counter_coa_id IS NOT NULL))
  CHECK (status != 'posted' OR entry_number IS NOT NULL)
```

**Sequential numbering (GoBD §11):**
- PostgreSQL: `CREATE SEQUENCE booking_entry_seq_<mandant_id>` per Mandant, called via `nextval()`
- MariaDB: dedicated helper table with atomic increment:
  ```sql
  booking_sequences
    mandant_id   UUID PRIMARY KEY
    next_value   BIGINT NOT NULL DEFAULT 1
  -- Service uses: UPDATE booking_sequences SET next_value = next_value + 1
  --               WHERE mandant_id = ?; SELECT next_value - 1 ...
  -- Wrapped in a transaction to guarantee atomicity.
  ```
- `entry_number` is assigned by the service layer at the moment of posting, inside a transaction
- Application code never constructs `entry_number` manually

**Immutability (GoBD §14):**
- Service layer raises `BookingAlreadyPostedError` on any UPDATE/DELETE of a posted booking
- DB-level: BEFORE UPDATE trigger rejects `status` changes on posted rows except the
  `posted → reversed` transition (which only the reversal service method may trigger)

**Reversal (Stornobuchung):**
`POST /bookings/{id}/reverse` atomically:
1. Creates a new booking with swapped `coa_id`/`counter_coa_id`, `reversal_of_id` set, same amount
2. Posts the new booking (assigns `entry_number`)
3. Sets original booking `status = 'reversed'`
All three steps in one DB transaction. The original is never modified further.

### 3.4 Accounting Period

```sql
accounting_periods
  id          UUID PRIMARY KEY
  mandant_id  UUID REFERENCES mandants NOT NULL
  year        INT NOT NULL
  month       INT NOT NULL              -- 1–12
  status      ENUM('open','locked','archived') DEFAULT 'open'
  locked_at   TIMESTAMPTZ
  UNIQUE (mandant_id, year, month)
```

Periods are auto-created on first posting if they do not exist yet (status='open').
Service layer blocks posting to locked or archived periods.

### 3.5 Audit Log (GoBD §9)

```sql
audit_log
  id             UUID PRIMARY KEY
  mandant_id     UUID REFERENCES mandants NULL   -- NULL for system events
  user_id        UUID REFERENCES users NULL
  table_name     TEXT NOT NULL
  record_id      UUID NOT NULL
  action         ENUM('insert','update','delete') NOT NULL
  changed_at     TIMESTAMPTZ NOT NULL
  change_summary JSON NOT NULL    -- {"field": ["old_value", "new_value"]}
```

Written by the service layer after every INSERT and UPDATE on accounting tables.
The audit_log table itself is append-only — no UPDATE or DELETE ever.

---

## 4. API Surface

All endpoints under `/api/v1/`. Mandant context comes from the JWT — no `mandant_id` in
URLs except admin endpoints.

### Auth
```
POST   /api/v1/auth/login          {email, password} → {access_token, refresh_token}
POST   /api/v1/auth/refresh        {refresh_token} → {access_token}
POST   /api/v1/auth/logout
GET    /api/v1/auth/me             → UserResponse
```

### Mandant
```
GET    /api/v1/mandants
POST   /api/v1/mandants
GET    /api/v1/mandants/{id}
PATCH  /api/v1/mandants/{id}
POST   /api/v1/mandants/{id}/switch    → issue new JWT scoped to this Mandant
```

### Chart of Accounts
```
GET    /api/v1/accounts                ?class=4xxx&is_active=true (paginated)
POST   /api/v1/accounts                custom accounts only
GET    /api/v1/accounts/{id}
PATCH  /api/v1/accounts/{id}           seed accounts: only private_share_percent + is_active
DELETE /api/v1/accounts/{id}           soft delete (is_active=false), custom only
GET    /api/v1/accounts/{id}/balance   ?date_from&date_to → running balance
```

### Tax Keys
```
GET    /api/v1/tax-keys                mandant-independent, read-only
GET    /api/v1/tax-keys/{code}
```

### Bookings
```
GET    /api/v1/bookings                ?type=entry&status=draft&date_from&date_to&account_id
POST   /api/v1/bookings                creates draft entry booking
GET    /api/v1/bookings/{id}
PATCH  /api/v1/bookings/{id}           draft status only
POST   /api/v1/bookings/{id}/post      draft → posted (GoBD: irreversible)
POST   /api/v1/bookings/{id}/reverse   creates and posts a reversal entry
DELETE /api/v1/bookings/{id}           draft only, hard delete
GET    /api/v1/bookings/{id}/audit-log → audit trail for this booking
```

### Booking Groups
```
GET    /api/v1/booking-groups
POST   /api/v1/booking-groups
GET    /api/v1/booking-groups/{id}/bookings
```

### Accounting Periods
```
GET    /api/v1/periods
POST   /api/v1/periods/{id}/lock
POST   /api/v1/periods/{id}/archive
```

### Reports
```
GET    /api/v1/reports/eur              ?date_from&date_to → EÜR aggregation
GET    /api/v1/reports/account-statement ?account_id&date_from&date_to → Kontoauszug
```

### DATEV Export
```
POST   /api/v1/datev/export            {date_from, date_to} → file download (CP1252)
```

**Soll/Haben-Kennzeichen derivation:**
`coa_id` is always the Soll (debit) account → DATEV field = `S`.
`counter_coa_id` is always the Haben (credit) account → DATEV field = `H`.
Amount is always positive (`amount_cents > 0`). Direction is encoded by account position,
not by sign. This maps directly to the DATEV ASCII `Soll/Haben-Kennzeichen` column.

### Admin (role=admin only)
```
GET    /api/v1/admin/users
POST   /api/v1/admin/users
PATCH  /api/v1/admin/users/{id}
POST   /api/v1/admin/mandants/{id}/users    assign user to Mandant with role
```

---

## 5. Error Handling

All errors return:
```json
{"error": {"code": "BOOKING_ALREADY_POSTED", "message": "...", "details": {}}}
```

Custom `AppError` subclasses registered as FastAPI exception handlers.
No `raise HTTPException` inline — ever.

Key error codes:
- `BOOKING_ALREADY_POSTED` — attempt to modify a posted booking
- `PERIOD_LOCKED` — attempt to post into a locked/archived period
- `ACCOUNT_NOT_FOUND`, `ACCOUNT_NOT_EDITABLE` — chart of accounts violations
- `MANDANT_ACCESS_DENIED` — cross-mandant access attempt
- `INVALID_TAX_RATE` — tax_rate / tax_key mismatch

---

## 6. GoBD Compliance Summary

| Rule | Reference | Enforcement |
|---|---|---|
| Immutability of posted entries | GoBD §14 | Service guard + DB trigger |
| Sequential numbering, no gaps | GoBD §11 | DB sequence / atomic helper table |
| Audit trail for all changes | GoBD §9 | Service writes to audit_log after every write |
| Period locking | GoBD §14b | Service checks period.status before post |
| 10-year retention | HGB §257 | archived periods + is_active flags; no hard delete |
| Monetary values as integers | GoBD / best practice | amount_cents BIGINT throughout |
| Timezone-aware timestamps | GoBD | TIMESTAMPTZ everywhere (Europe/Berlin) |

---

## 7. Testing Strategy

Framework: pytest + anyio (async). Test DB: PostgreSQL via pytest-docker.
MariaDB CI run via GitHub Actions service container.

No mocking of the DB layer — all tests hit a real database.

**100% coverage required:**
- VAT calculation: `tax_amount_cents = amount_cents - round(amount_cents / (1 + tax_rate))`
- Booking post + reversal (GoBD workflow)
- DATEV ASCII export (CP1252 encoding, field lengths, Soll/Haben-Kennzeichen mapping)
- EÜR aggregation (PrivateSharePercent, virtual accounts 3806 / 1401 / 1406)
- Mandant isolation (no cross-mandant data leak in any service method)
- Sequential entry_number: no gaps, no duplicates under concurrent posts

**Overall targets:** ≥80% backend, smoke tests only for React skeleton.

---

## 8. Implementation Phases within Phase 1

Suggested build order (each step is independently deployable):

1. Project scaffolding: pyproject.toml, FastAPI app factory, Alembic env, Docker Compose
2. Auth: User, UserMandant, JWT login/refresh
3. Mandant: model, CRUD, JWT mandant-scoping
4. Chart of Accounts: model, seed migration (SKR03/04/07), CRUD
5. Tax Keys: model, seed migration (DATEV BU-Schlüssel), read-only API
6. Bookings: model, DB sequences/triggers, draft CRUD
7. Booking lifecycle: post, reverse, period locking, audit log
8. Reports: EÜR, Kontoauszug
9. DATEV ASCII export
10. React skeleton: Vite setup, MUI v6, TanStack Query, openapi-typescript codegen
