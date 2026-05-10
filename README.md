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
- **First-run setup wizard** — UI wizard or env-var headless bootstrap for zero-touch installs

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI 0.110, SQLAlchemy 2 (async) |
| Frontend | React 18, TypeScript 5, MUI v6, TanStack Query v5 |
| Database | PostgreSQL 16 (primary) · MariaDB 10.11 / MySQL 8 (supported) |
| PDF | WeasyPrint 62 via Jinja2 templates |
| Auth | JWT (python-jose), bcrypt |
| Migrations | Alembic (auto-run on startup) |
| Packaging | uv (Python), npm (frontend) |
| Runtime | Docker Compose (minimum), Kubernetes-ready |

---

## Quickstart (Docker Compose)

**Prerequisites:** Docker with Compose plugin, Git.

```bash
git clone https://github.com/nofuturekid/webbuchhaltung.git
cd webbuchhaltung
docker compose up --build -d
```

Open **http://localhost:3000** — on a fresh database the login page shows a
"Ersteinrichtung starten" link. Click it to open the setup wizard and create
your admin account and first Mandant.

> **Headless / CI alternative:** set `BOOTSTRAP_ADMIN_EMAIL` and
> `BOOTSTRAP_ADMIN_PASSWORD` before starting — the backend seeds the admin
> automatically on first boot:
> ```bash
> BOOTSTRAP_ADMIN_EMAIL=admin@mycompany.de \
> BOOTSTRAP_ADMIN_PASSWORD=secret123 \
> docker compose up --build -d
> ```
> Add `BOOTSTRAP_MANDANT_NAME` and `BOOTSTRAP_SKR_VARIANT` to customise the
> Mandant (defaults: "Meine Firma", skr03).

> **Before any non-local deployment:** set a strong `SECRET_KEY` in your
> environment or Docker secrets. The placeholder value in `docker-compose.yml`
> must never be used in production.

API docs: http://localhost:8000/docs

---

## Documentation

- [DEVELOPMENT.md](DEVELOPMENT.md) — local dev setup, migrations, smoke test, project structure
- [CONTRIBUTING.md](CONTRIBUTING.md) — branching, commit format, test suite, gate agents
- [docs/decisions/](docs/decisions/) — Architecture Decision Records

---

## License

Private — all rights reserved.
