# Changelog

## [0.5.0] — 2026-05-10

### Added — Phase 5

#### Kontoauszugsimport (Bank Import + Matching)
- DB migration 0008: `bank_accounts` and `bank_transactions` tables with GoBD
  audit columns (`created_at`, `updated_at`, `action`, `actor`)
- MT940 and CSV bank statement import with deduplication by `source_ref`
  (SELECT-first + INSERT strategy; see ADR-0006)
- Automatic transaction matching scored by: amount exact match (+0.60),
  date within ±3 days (+0.30) or ±7 days (+0.15), purpose keyword (+0.10);
  auto-applied when score ≥ 0.90 (see ADR-0008)
- Manual match, ignore, and unmatch operations — all GoBD §9 audited
- Frontend: `BankAccountsPage` with MT940 import dialog; `MatchingView` with
  auto-match button and per-transaction confidence display
- 12 new backend API endpoints under `/api/v1/bank-accounts/` and
  `/api/v1/bank-transactions/`

#### Eingangsrechnungen / Accounts Payable
- DB migration 0009: `vendors` and `vendor_invoices` tables; SKR03/SKR04
  accounts payable (1600/1601) backfilled for existing mandants
- Vendor CRUD with IBAN validation via `schwifty`
- Vendor invoice lifecycle: draft → posted → paid / cancelled
- GoBD-compliant posting: `get_next_entry_number`, immutability guards,
  full audit trail on every state transition
- SEPA pain.001.003.03 XML batch payment export using stdlib
  `xml.etree.ElementTree` (see ADR-0007)
- Document integration: `POST /documents/{id}/confirm` extended with
  `create_vendor_invoice` flag to create AP invoice directly from a captured
  document
- Frontend: `VendorsPage` (CRUD table) and `VendorInvoicesPage` with SEPA
  export button

#### Erweiterte Berichte (Advanced Reports)
- Saldenliste (trial balance): opening balance + period movements + closing
  balance per account
- Bilanz (balance sheet, HGB §266): Aktiva / Passiva with `balanced: bool`
  and `imbalance_cents` field; amber imbalance alert in the frontend
- G+V (income statement): revenue accounts (8xxx / 4xxx) vs. expenses
- BWA (business performance analysis): 12 monthly columns
- All four endpoints support `?format=json|csv`; queries are
  MariaDB-compatible (no PostgreSQL-only syntax)
- Frontend: four new report pages (Saldenliste, Bilanz, G+V, BWA)

#### Infrastructure
- Helm chart `helm/webbuchhaltung/` (Chart version 0.5.0): backend and
  frontend Deployments, Ingress, ConfigMap, Secret, PersistentVolumeClaim
  for document storage
- Admin page: audit log viewer filterable by table, action, and date range;
  system info tab
- Backend: `GET /api/v1/admin/audit-log` endpoint (mandant-scoped, paginated)

### Fixed
- GoBD §9: `apply_ignore` and `apply_unmatch` now write audit entries
  (`bank_matching.py`) — previously these operations left no audit trail
- Float-rounding in auto-match score threshold: `round(score, 4)` prevents
  IEEE 754 drift causing scores of 0.8999999… to fall below the 0.90 cutoff

### Tests
- 185 tests total (+73 from Phase 4 baseline of 112), covering bank import,
  vendor invoice lifecycle, SEPA export, and all four advanced report endpoints

---

## Unreleased — Unreleased

### Phase 4 — Asset Management + LLM Document Capture (2026-05-10)

#### Features

- **feat(backend):** Asset management (Anlagenverzeichnis) — HGB §266 fixed assets
  with linear depreciation, GoBD-compliant booking automation, disposal bookings
  (SKR03+SKR04 accounts 2680/4855), immutability guards for posted schedules
- **feat(backend):** LLM document capture (Belegerfassung) — upload PDF/image,
  Claude API extracts structured data (vendor, date, amount, account suggestions),
  user confirms → creates GoBD-compliant Buchungssatz via existing booking pipeline
- **feat(frontend):** Asset management UI (AssetsPage) — data table with
  depreciation schedule modal and disposal dialog
- **feat(frontend):** Document capture UI (DocumentsPage) — drag-and-drop upload
  dropzone, extraction review panel with file preview (PDF iframe / image) and
  editable confirmation form

#### Bug Fixes

- **fix(backend):** GoBD audit trail fix in `reject_document` — captured
  `prior_status` before mutation so the audit record reflects the correct
  previous state (GoBD §9)
- **fix(backend):** JSON serialization of `document_date` in `extracted_json` —
  use `model_dump(mode="json")` so `date` objects serialise to ISO strings
  rather than raising `TypeError`

#### Testing

- **test(qa):** 20 new tests (11 asset + 9 document capture), total now 112

#### Environment Variables (production)

- `ANTHROPIC_API_KEY` — required for LLM document extraction (`process_document`
  endpoint). Without it, document processing raises `LLMExtractionError` (502).
- `STORAGE_ROOT` — filesystem path for uploaded documents
  (default: `/tmp/webbuchhaltung-docs`). Mount a named volume in production to
  avoid data loss on container restart.

#### Known Gap

- SKR03 test seed is missing accounts 4855 (Verluste aus Anlagenabgang) and
  2680 (Erträge aus Anlagenabgang) in the fixture data used by disposal tests.
  Full disposal-path integration testing is deferred to the next cycle.

---

### Bug Fixes

- Resolve cross-file consistency issues in agent templates ([`bdfba73`])

- Fix shell safety issues in hook scripts ([`438bc18`])

- Address code quality issues from Task 1 review ([`da34a50`])

- Fix event loop scope, isolate error tests ([`4a38073`])

- Fix GoBD trigger, ENUM nullable, enum type cleanup on downgrade ([`e446a52`])

- Use auto_error=False to return consistent error format ([`97da532`])

- Fix timing attack, strict dict types, token-type guards ([`5b7989c`])

- Require admin role on all admin user endpoints ([`ac64ec4`])

- Add schema validators, scope admin users query ([`bf17d5f`])

- Add skr_variant to seed JSON, extract get_tax_key to service, scope downgrade ([`0778927`])

- Auth on tax-keys, route ordering, skr guard, date validation ([`ddc7fa0`])

- Type _setup, scalar_one, posted-booking test ([`905f35a`])

- GoBD guard for reversed bookings, BookingUpdate validators ([`5252de2`])

- Move imports to module top, fix MariaDB upsert syntax ([`8d75ba3`])

- Atomic MariaDB sequence, period TOCTOU, audit scope ([`5e6e89a`])

- Auth guard on GET /periods, AwareDatetime, guard tests ([`3691849`])

- Per-booking VSt, mandant guard on join, date types, opening balance ([`421a132`])

- Fix DATEV timestamp to 17-char EXTF format, add isolation test ([`8e8b0e8`])

- Type axios response, add index route, EXPOSE 80, .dockerignore ([`2da4d9a`])

- Docker stack fixes found during smoke testing (#2) ([`d5a1d17`])

- Harden euroToCents, expand formatter tests ([`c8ebde9`])

- Sync Zustand auth store on token refresh ([`63f18ab`])

- Add weasyprint system deps to Dockerfile ([`3ea9cbe`])

- Fix GoBD §9 audit trail and §14 period lock in invoice issue ([`ac8f323`])

- Use axios.isAxiosError for 404 detection in SetupPage ([`6ac2d5c`])


### Build

- Add pre-commit framework with ruff, mypy, gitleaks, commitizen ([`f259268`])

- Add git-cliff configuration for automatic CHANGELOG generation ([`9b4ee0e`])


### Documentation

- Add Claude Code agent-team setup design spec ([`37a739c`])

- Add agent-team setup implementation plan ([`9d90ff3`])

- Add root CLAUDE.md orchestrator rules ([`41aff83`])

- Add domain CLAUDE.md context files for all four areas ([`b45ef90`])

- Add worker agent prompt templates ([`8fbba86`])

- Add gate and exchange agent prompt templates ([`799a01f`])

- Mark agent-team setup as complete ([`faafa93`])

- Add Phase 1 accounting core design spec ([`b962e55`])

- Update project status after Phase 1 design session ([`3f3dfb0`])

- Add Phase 1 accounting core implementation plan ([`fc9e1b8`])

- Update project status — Phase 1 complete, PR #1 open ([`f2a92d4`])

- Sync project status after hotfix merge ([`7844345`])

- Update project status — Task 10 complete, Phase 2 in progress ([`9a24d72`])

- Add Phase 2 full UI implementation plan ([`120720f`])

- Phase 2 complete — PR #3 open ([`03dfa15`])

- Phase 2 merged to main ([`1e2417b`])

- Add Rechnungen (Ausgangsrechnungen) design spec ([`f70173e`])

- Update CLAUDE.md — orchestration, develop branch, test setup ([`a5d7736`])

- Add smoke test golden path and contract test section ([`41d39d4`])

- Add project README with setup, dev, and contributing guide ([`20ee46f`])

- Add smoke test and contract test to QA-Agent scope ([`e91c5aa`])

- Update README — setup wizard as primary onboarding path ([`3306fc8`])

- Generate CHANGELOG, add ADRs, update README features ([`111d37c`])

- Update project status after Docs-Agent run ([`7505e3d`])

- Update project status after housekeeping ([`039ae6d`])

- Number ADRs, split README into DEVELOPMENT + CONTRIBUTING ([`28534fe`])


### Features

- Add Claude Code hook scripts for lint, security gate, and session end ([`ba36669`])

- Wire Claude Code hooks in settings.json ([`b42caff`])

- Add project scaffolding — FastAPI, Alembic, Docker ([`f242b66`])

- Add TimestampMixin and AppError hierarchy with handler ([`63f4113`])

- Add all core models and initial Alembic migration ([`178996f`])

- Add JWT authentication — login, refresh, me endpoint ([`dfdb26e`])

- Add Mandant CRUD and JWT mandant-scoping ([`8f000a6`])

- Add chart of accounts, TaxKeys, SKR seed data ([`7334b1b`])

- Add booking draft CRUD ([`d0e3378`])

- Add booking posting, GoBD numbering, audit ([`b994f5b`])

- Add Stornobuchung — reversal with atomic post and original status update ([`a508c15`])

- Add accounting period locking and archiving ([`5998eae`])

- Add EÜR and Kontoauszug reports with PrivateShare and virtual accounts ([`38f7725`])

- Add DATEV ASCII export (EXTF v700, CP1252, Soll/Haben mapping) ([`66eacc1`])

- Add React 18 skeleton — MUI v6, TanStack Query, login page ([`5b7508d`])

- Add Vitest, German formatters with tests ([`48a3475`])

- Add TypeScript API types from OpenAPI schema ([`825e24c`])

- Add Axios API instance with token refresh and Zustand auth store ([`1cac849`])

- Login with RHF+Zod, mandant auto-switch on login ([`69b9e35`])

- Add sidebar navigation to Layout ([`3c06cf7`])

- Add all page routes and stub pages ([`9828f46`])

- Add Buchungsjournal list with post/reverse/delete actions ([`1aa4ff8`])

- Add Buchungsmaske with account autocomplete and tax calculation ([`8033618`])

- Add Kontenplan with inline private share editing ([`a1d6637`])

- Add Kontoauszug with account selector and date range ([`b8f3142`])

- Add EÜR report with Betriebseinnahmen/ausgaben summary ([`d631e14`])

- Add DATEV EXTF CSV export with download ([`3107617`])

- Add Dashboard with live EÜR summary and booking counts ([`85a69e4`])

- Add invoice module — sequences, CRUD, issue/cancel, PDF, email ([`e80e0ee`])

- Add Rechnungen UI — invoices, customers, settings ([`d3abf7d`])

- Backfill SKR03 account 8200 for existing mandants ([`f7d9171`])

- Add first-admin bootstrap via env-vars and setup endpoint ([`baa11b4`])

- Add first-run setup wizard — SetupPage and login hint ([`462f257`])

- Add Docs-Agent template and integrate into orchestration workflow ([`6b371b3`])


### Miscellaneous

- Add gitignore, memory structure, and required directories ([`3da4840`])

- Fix gitignore duplicates, add missing patterns, clarify status ([`7344ab0`])


### Refactoring

- Move backend/ and frontend/ under src/ ([`b99592e`])


### Testing

- Strengthen GoBD cancel assertions + add 7%/0% VAT tests ([`d130143`])
