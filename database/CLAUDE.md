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
- 4xxx: Cost of goods + operating expenses (Wareneinkauf, Betriebsausgaben)
- 5xxx–6xxx: Other operating costs (Weitere Betriebsausgaben)
- 8xxx: Revenue accounts (Erlöskonten)
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
