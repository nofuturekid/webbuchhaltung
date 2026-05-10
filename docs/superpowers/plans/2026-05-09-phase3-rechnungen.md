# Phase 3 Rechnungen (Ausgangsrechnungen) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add outbound invoice management — numbered sequences, PDF generation,
automatic double-entry booking on issue, and email delivery — on top of the
completed Phase 1 backend + Phase 2 frontend.

**Design spec:** `docs/superpowers/specs/2026-05-09-rechnungen-design.md`

**Architecture:**
- Backend: new `invoices/`, `customers/` feature modules under `backend/app/`
- PDF: weasyprint + Jinja2 SandboxedEnvironment, server-side rendering
- Email: stdlib smtplib, per-mandant SMTP, Fernet-encrypted password
- Frontend: new `src/features/invoices/`, `src/features/customers/` + pages

**Branch:** `feature/backend-phase3-rechnungen` (backend) then
`feature/frontend-phase3-rechnungen` (frontend) — merge in order

---

## File Map

### Backend — new files
- `backend/app/models/invoice.py` — Customer, InvoiceSequence, Invoice, InvoiceLineItem, InvoiceTemplate ORM models
- `backend/app/schemas/invoice.py` — Pydantic schemas (Create/Update/Response) for all invoice domain objects
- `backend/app/services/invoice_sequence.py` — atomic sequence increment + year-reset logic
- `backend/app/services/invoice_pdf.py` — weasyprint PDF rendering, Jinja2 template loading
- `backend/app/services/invoice_email.py` — SMTP send + Fernet encrypt/decrypt for SMTP password
- `backend/app/services/invoice_booking.py` — booking creation per VAT bucket on issue/cancel
- `backend/app/routers/customers.py` — CRUD router
- `backend/app/routers/invoices.py` — invoice CRUD + action endpoints
- `backend/app/routers/invoice_template.py` — GET/PUT template settings
- `backend/app/templates/invoice_layout_a.html` — Jinja2 HTML for built-in PDF layout
- `backend/tests/test_invoice_sequence.py` — unit tests for sequence numbering
- `backend/tests/test_invoices.py` — integration tests for issue/cancel flow

### Backend — modified files
- `backend/app/models/__init__.py` — import new models so Alembic sees them
- `backend/app/models/mandant.py` — add IBAN, BIC, SMTP columns
- `backend/app/models/booking.py` — add `invoice_id` FK column
- `backend/app/routers/__init__.py` / `backend/app/main.py` — register new routers
- `backend/pyproject.toml` — add `weasyprint`, `jinja2` (if not present), `cryptography`
- `backend/alembic/versions/` — new migration file

### Frontend — new files
- `frontend/src/types/invoice.ts` — TypeScript types for all invoice domain objects
- `frontend/src/features/invoices/api.ts` — TanStack Query hooks (list, detail, create, issue, cancel, pdf, email)
- `frontend/src/features/invoices/InvoiceFormDialog.tsx` — create/edit draft with line items
- `frontend/src/features/invoices/InvoiceDetailPage.tsx` — read-only view + action buttons
- `frontend/src/features/invoices/LineItemsTable.tsx` — dynamic add/remove rows sub-component
- `frontend/src/features/customers/api.ts` — TanStack Query hooks (list, create, update)
- `frontend/src/features/customers/CustomersPage.tsx` — table + inline create/edit dialog
- `frontend/src/features/invoices/__tests__/lineItemCalc.test.ts` — Vitest unit tests
- `frontend/src/pages/InvoicesPage.tsx` — DataGrid wrapper + FAB
- `frontend/src/pages/MandantSettingsPage.tsx` — SMTP + bank details tabs

### Frontend — modified files
- `frontend/src/types/api.ts` — add customer/invoice/mandant-settings interfaces
- `frontend/src/App.tsx` — add `/invoices`, `/invoices/:id`, `/customers`, `/settings/mandant` routes
- `frontend/src/components/Layout.tsx` — add sidebar nav items for Rechnungen, Kunden, Einstellungen

---

## Task 1: Database Migration

**Files:**
- Modify: `backend/app/models/mandant.py`
- Modify: `backend/app/models/booking.py`
- Create: `backend/app/models/invoice.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/<timestamp>_add_invoice_tables.py`

- [ ] **Step 1: Extend Mandant model**
  Add columns: `iban VARCHAR(34)`, `bic VARCHAR(11)`, `smtp_host VARCHAR(253)`,
  `smtp_port SMALLINT DEFAULT 587`, `smtp_user VARCHAR(254)`,
  `smtp_password VARCHAR(500)`, `smtp_from VARCHAR(254)`, `smtp_from_name VARCHAR(200)`.

- [ ] **Step 2: Extend Booking model**
  Add nullable FK column `invoice_id UUID` referencing `invoices.id`.

- [ ] **Step 3: Create invoice.py models**
  Define `Customer`, `InvoiceSequence`, `Invoice`, `InvoiceLineItem`, `InvoiceTemplate`
  SQLAlchemy models exactly matching the data model in the design spec §3.
  Use `Enum('draft','issued','cancelled')` for `Invoice.status`.

- [ ] **Step 4: Register models in `__init__.py`**
  Import all new model classes so Alembic autogenerate picks them up.

- [ ] **Step 5: Generate and verify migration**
  ```bash
  cd backend && uv run alembic revision --autogenerate -m "add_invoice_tables"
  ```
  Review the generated migration. Verify: correct FK constraints, `UNIQUE` on
  `invoice_sequences.mandant_id`, `UNIQUE` on `invoices.invoice_number`,
  `UNIQUE` on `invoice_templates.mandant_id`. Add `SELECT FOR UPDATE` note in comment.

- [ ] **Step 6: Apply migration and run tests**
  ```bash
  uv run alembic upgrade head
  uv run pytest tests/ -q
  ```
  All 66 existing tests must pass.

---

## Task 2: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/invoice.py`

- [ ] **Step 1: Customer schemas**
  `CustomerCreate`, `CustomerUpdate` (all fields optional), `CustomerResponse`.
  Include `id: UUID`, `mandant_id: UUID`, `created_at`, `updated_at` in response.

- [ ] **Step 2: InvoiceLineItem schemas**
  `LineItemCreate` (description, quantity, unit, unit_price_cents, vat_rate, position),
  `LineItemResponse` (adds `id`, `net_total_cents`, `vat_amount_cents`).

- [ ] **Step 3: Invoice schemas**
  `InvoiceCreate` (customer_id, issue_date, due_date, notes, line_items: list[LineItemCreate]),
  `InvoiceUpdate` (same fields, all optional, forbidden once issued),
  `InvoiceResponse` (all fields including `status`, `booking_id`, `line_items: list[LineItemResponse]`),
  `InvoiceListItem` (subset: id, invoice_number, status, customer_id, customer_name, issue_date, due_date, gross_total_cents).

- [ ] **Step 4: Template + sequence schemas**
  `InvoiceTemplateResponse`, `InvoiceTemplateUpdate` (branding fields only, no custom_html_template in Phase A),
  `InvoiceSequenceResponse`, `InvoiceSequenceUpdate` (prefix, year_reset).

- [ ] **Step 5: Email send schema**
  `SendEmailRequest` with optional `override_email: EmailStr`.

---

## Task 3: Customer Service + Router

**Files:**
- Create: `backend/app/routers/customers.py`

- [ ] **Step 1: Implement customer CRUD router**
  All five endpoints: GET list, POST create, GET detail, PUT update, DELETE.
  All are mandant-scoped (`current_mandant` dependency from Phase 1 auth).
  DELETE: return 409 if any `invoices.customer_id` references this customer.

- [ ] **Step 2: Register router in main.py**
  Prefix `/api/v1/customers`, tag `customers`.

---

## Task 4: Invoice Sequence Service

**Files:**
- Create: `backend/app/services/invoice_sequence.py`

- [ ] **Step 1: Implement `get_or_create_sequence(session, mandant_id)`**
  SELECT existing sequence or INSERT default (prefix='RE', next_number=1, year_reset=True).

- [ ] **Step 2: Implement `allocate_invoice_number(session, mandant_id) -> str`**
  Use `SELECT … FOR UPDATE` on the sequence row to prevent concurrent duplicates.
  If `year_reset=True` and current year ≠ `last_reset_year`: set `next_number=1`,
  update `last_reset_year`. Then compute formatted number:
  - `year_reset=True`: `{prefix}-{year}-{next_number:03d}`
  - `year_reset=False`: `{prefix}-{next_number:03d}`
  Increment `next_number`. Commit happens in caller (router).

- [ ] **Step 3: Unit tests in `test_invoice_sequence.py`**
  - Normal increment: RE-2026-001 → RE-2026-002
  - Year rollover: last_reset_year=2025, current=2026 → reset to 001
  - No year_reset mode: RE-001 → RE-002
  Use SQLite in-memory (same as rest of tests via `TEST_DATABASE_URL`).

---

## Task 5: Invoice CRUD Router (draft lifecycle)

**Files:**
- Create: `backend/app/routers/invoices.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: POST /invoices — create draft**
  Call `allocate_invoice_number`, create `Invoice` record (status=draft),
  bulk-create `InvoiceLineItem` records, compute and store
  `net_total_cents`, `vat_total_cents`, `gross_total_cents` from line items.
  Return `InvoiceResponse`.

- [ ] **Step 2: GET /invoices — list**
  Filter by `status` (optional), `customer_id` (optional), `date_from`/`date_to` (optional).
  Return list of `InvoiceListItem`. Order by `issue_date DESC`, `created_at DESC`.

- [ ] **Step 3: GET /invoices/{id} — detail**
  Return full `InvoiceResponse` with nested `line_items`.
  404 if not found or wrong mandant.

- [ ] **Step 4: PUT /invoices/{id} — update draft**
  Return 403 if `status != 'draft'`.
  Replace all line_items (delete existing, insert new), recompute totals.

- [ ] **Step 5: DELETE /invoices/{id} — delete draft**
  Return 403 if `status != 'draft'`.

- [ ] **Step 6: Register router in main.py**
  Prefix `/api/v1/invoices`, tag `invoices`.

---

## Task 6: Issue + Cancel Flow (Booking Integration)

**Files:**
- Create: `backend/app/services/invoice_booking.py`
- Modify: `backend/app/routers/invoices.py`

- [ ] **Step 1: Implement `create_invoice_booking(session, invoice, mandant)`**
  Group line items by VAT rate. For each VAT bucket create one booking:
  - 19%: debit account 1400, credit account 8400
  - 7%: debit account 1200 (or 1400), credit account 8300
  - 0%: debit account 1400, credit account 8200
  Amount = gross total for that bucket (cents).
  Use existing `Booking` model from Phase 1. Set `invoice_id` on booking.
  Return created booking.

- [ ] **Step 2: POST /invoices/{id}/issue**
  - Return 400 if `status != 'draft'`
  - Set `status = 'issued'`, `issue_date = today` (if not already set)
  - Call `create_invoice_booking`, set `booking_id` on invoice
  - Commit. Return updated `InvoiceResponse`.

- [ ] **Step 3: POST /invoices/{id}/cancel**
  - Return 400 if `status != 'issued'`
  - Create reversal booking (negate original amounts) using existing booking reverse logic from Phase 1
  - Set `status = 'cancelled'`
  - Commit. Return updated `InvoiceResponse`.

- [ ] **Step 4: Integration tests in `test_invoices.py`**
  - Create draft → verify invoice_number assigned
  - Issue draft → verify status=issued, booking created with correct accounts and amounts
  - Cancel issued → verify status=cancelled, reversal booking created
  - Attempt PUT on issued → verify 403
  - Attempt issue on already-issued → verify 400

---

## Task 7: PDF Generation

**Files:**
- Create: `backend/app/services/invoice_pdf.py`
- Create: `backend/app/templates/invoice_layout_a.html`
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Add weasyprint + jinja2 to pyproject.toml**
  ```toml
  "weasyprint>=62.0",
  "jinja2>=3.1",
  ```
  Run `uv pip install -e .` inside Docker container or `uv sync`.

- [ ] **Step 2: Create Jinja2 HTML template `invoice_layout_a.html`**
  Layout per design spec §6:
  - Header: logo placeholder + mandant name left; "RECHNUNG" + number/date right
  - Recipient block
  - Line items table: Pos., Beschreibung, Menge, Einheit, Einzelpreis (netto), MwSt, Betrag
  - Totals block: Nettobetrag, MwSt per rate, Bruttobetrag
  - Footer: IBAN/BIC, Zahlungsziel, footer_text
  Use inline CSS (weasyprint renders print-targeted CSS). No external assets.
  Available context variables: `invoice`, `mandant`, `customer`, `line_items`,
  `net_total`, `vat_total`, `gross_total`, `template`.

- [ ] **Step 3: Implement `render_invoice_pdf(invoice, mandant, customer, template) -> bytes`**
  Load template from `backend/app/templates/invoice_layout_a.html` via
  `jinja2.FileSystemLoader`. Use `SandboxedEnvironment`. Render to HTML string.
  Pass to `weasyprint.HTML(string=html_str).write_pdf()`. Return bytes.

- [ ] **Step 4: GET /invoices/{id}/pdf endpoint**
  Call `render_invoice_pdf`, return `Response(content=pdf_bytes, media_type="application/pdf")`
  with header `Content-Disposition: attachment; filename="RE-2026-001.pdf"`.

---

## Task 8: Email + SMTP Config

**Files:**
- Create: `backend/app/services/invoice_email.py`
- Modify: `backend/app/routers/invoices.py`
- Modify: `backend/app/routers/mandants.py` (add smtp-test endpoint)

- [ ] **Step 1: Implement Fernet encrypt/decrypt for SMTP password**
  In `invoice_email.py`:
  ```python
  from cryptography.fernet import Fernet
  import base64, hashlib

  def _fernet(secret_key: str) -> Fernet:
      key = base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode()).digest())
      return Fernet(key)

  def encrypt_smtp_password(password: str, secret_key: str) -> str: ...
  def decrypt_smtp_password(encrypted: str, secret_key: str) -> str: ...
  ```
  Derive Fernet key from `settings.SECRET_KEY` via SHA-256 (deterministic, no key storage).

- [ ] **Step 2: Implement `send_invoice_email(invoice, mandant, pdf_bytes, override_email=None)`**
  - Decrypt SMTP password
  - Build `email.mime.multipart.MIMEMultipart('mixed')`
  - Text part: German body template ("Sehr geehrte Damen und Herren, anbei erhalten Sie Rechnung …")
  - PDF attachment: `MIMEBase('application','pdf')` with filename
  - Connect `smtplib.SMTP(host, port)`, STARTTLS, login, sendmail, quit
  - On `SMTPException`: raise `HTTPException(502, detail=str(e))`

- [ ] **Step 3: POST /invoices/{id}/send-email endpoint**
  Parse `SendEmailRequest`, call `send_invoice_email`.
  On success return `{"sent": true, "recipient": email_used}`.

- [ ] **Step 4: POST /mandants/smtp-test endpoint**
  Send a test email to `smtp_from` (or request body override) with subject "SMTP-Test WebBuchhaltung".
  Return 200 on success, 502 on SMTP error.

- [ ] **Step 5: PUT /mandants/{id} extension**
  Allow updating IBAN, BIC, SMTP fields. Encrypt `smtp_password` before storing if provided.

---

## Task 9: Invoice Template Endpoints

**Files:**
- Create: `backend/app/routers/invoice_template.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: GET /invoice-template**
  Return `InvoiceTemplateResponse` for current mandant.
  If no template row exists, create one with defaults and return it.

- [ ] **Step 2: PUT /invoice-template**
  Update branding fields (`primary_color`, `font_family`, `header_text`,
  `footer_text`, `payment_terms_text`). Phase A: `custom_html_template` and
  `use_custom_template` are NOT exposed (return 422 if sent).

- [ ] **Step 3: GET/PUT /invoice-sequences**
  Return current sequence. Allow updating `prefix` (max 20 chars) and `year_reset`.
  Changing prefix takes effect on next invoice allocation only.

- [ ] **Step 4: Register router in main.py**

---

## Task 10: Frontend — TypeScript Types + API Hooks

**Files:**
- Modify: `frontend/src/types/api.ts`
- Create: `frontend/src/types/invoice.ts`
- Create: `frontend/src/features/invoices/api.ts`
- Create: `frontend/src/features/customers/api.ts`

- [ ] **Step 1: Define TypeScript types in `invoice.ts`**
  `Customer`, `CustomerCreate`, `InvoiceLineItem`, `LineItemCreate`,
  `Invoice`, `InvoiceListItem`, `InvoiceCreate`, `InvoiceUpdate`,
  `InvoiceTemplate`, `InvoiceSequence`, `SendEmailRequest`.
  All amount fields as `number` (cents). Dates as `string` (ISO).
  Status as `'draft' | 'issued' | 'cancelled'`.

- [ ] **Step 2: Extend `api.ts` — MandantSettings type**
  Add IBAN, BIC, SMTP fields to mandant response type.

- [ ] **Step 3: Customer API hooks**
  `useCustomers()` — GET /customers,
  `useCreateCustomer()` — POST,
  `useUpdateCustomer(id)` — PUT.
  Invalidate `['customers']` on mutations.

- [ ] **Step 4: Invoice API hooks**
  `useInvoices(filters)` — GET /invoices with optional status/customer/date params,
  `useInvoice(id)` — GET /invoices/{id},
  `useCreateInvoice()` — POST,
  `useUpdateInvoice(id)` — PUT,
  `useDeleteInvoice()` — DELETE,
  `useIssueInvoice(id)` — POST /invoices/{id}/issue,
  `useCancelInvoice(id)` — POST /invoices/{id}/cancel,
  `useSendInvoiceEmail(id)` — POST /invoices/{id}/send-email.
  PDF download: plain `fetch` + blob URL (not a Query hook).

---

## Task 11: Frontend — CustomersPage

**Files:**
- Create: `frontend/src/features/customers/CustomersPage.tsx`
- Create: `frontend/src/pages/CustomersPage.tsx` (thin wrapper)

- [ ] **Step 1: Customer list table**
  MUI `Table` (not DataGrid — simpler dataset). Columns: Name, Stadt, E-Mail,
  USt-IdNr., Aktionen (Edit / Delete with confirmation).

- [ ] **Step 2: Create/edit dialog**
  MUI `Dialog` with RHF+Zod form. Fields: name (required), street, postal_code,
  city, country (default DE), vat_id, email.

- [ ] **Step 3: Inline "Neuen Kunden anlegen" action**
  Button above table opens create dialog. Edit icon per row opens same dialog
  pre-filled. On save: invalidate `['customers']` query.

---

## Task 12: Frontend — InvoiceFormDialog

**Files:**
- Create: `frontend/src/features/invoices/LineItemsTable.tsx`
- Create: `frontend/src/features/invoices/InvoiceFormDialog.tsx`

- [ ] **Step 1: LineItemsTable sub-component**
  Dynamic array managed via `useFieldArray` (React Hook Form).
  Columns: Pos., Beschreibung, Menge, Einheit, Einzelpreis (€), MwSt (select 19%/7%/0%),
  Betrag (computed, read-only), Delete icon.
  "Position hinzufügen" button appends empty row.
  Compute `net = qty × price`, `vat = net × rate`, `gross = net + vat` per row.

- [ ] **Step 2: Totals preview bar**
  Below the table: sticky footer row showing Netto-Summe, USt-Summe (broken out
  by rate if mixed), Brutto-Summe — recalculated on every field change via `watch`.

- [ ] **Step 3: InvoiceFormDialog**
  Full-screen MUI `Drawer` (not modal dialog — content is too tall).
  Fields:
  - Customer: `Autocomplete` fetching `useCustomers()`, with "Neuen Kunden anlegen" option
    that opens an inline mini-dialog (reuse CustomersPage dialog)
  - Rechnungsdatum + Fälligkeitsdatum: MUI `DatePicker`
  - Notizen: multiline TextField
  - LineItemsTable
  - Totals preview
  - Action row: "Abbrechen" + "Als Entwurf speichern"
  Zod schema validates: customer required, at least one line item, quantity > 0,
  unit_price >= 0.

---

## Task 13: Frontend — InvoicesPage

**Files:**
- Create: `frontend/src/pages/InvoicesPage.tsx`

- [ ] **Step 1: DataGrid with filter bar**
  MUI `DataGrid` columns: Nummer, Kunde (name), Ausgestellt, Fällig,
  Status (Chip: draft=grey, issued=blue, cancelled=red), Brutto (formatted €).
  Filter bar above: Status-Select (All/Entwurf/Ausgestellt/Storniert),
  two `DatePicker` inputs for date range.
  On row click: navigate to `/invoices/{id}`.

- [ ] **Step 2: FAB + InvoiceFormDialog integration**
  Floating action button "Neue Rechnung" opens `InvoiceFormDialog`.
  On save: invalidate `['invoices']` query, close dialog.

---

## Task 14: Frontend — InvoiceDetailPage

**Files:**
- Create: `frontend/src/features/invoices/InvoiceDetailPage.tsx`
- Create: `frontend/src/pages/InvoiceDetailPage.tsx` (thin wrapper)

- [ ] **Step 1: Read-only invoice display**
  Two-column layout: left = invoice metadata (Nummer, Kunde, Datum, Fälligkeit,
  Status chip, Notizen), right = Mandant info.
  Below: line items in a read-only MUI Table.
  Below: totals block (Netto, USt per rate, Brutto).
  Booking reference link if `booking_id` is set.

- [ ] **Step 2: Action buttons — draft state**
  "Bearbeiten" → opens InvoiceFormDialog pre-filled with current data.
  "Ausstellen" → MUI `Dialog` confirmation → calls `useIssueInvoice()`.
  "Löschen" → confirmation → calls `useDeleteInvoice()` → navigate to /invoices.

- [ ] **Step 3: Action buttons — issued state**
  "PDF herunterladen" → fetch `/invoices/{id}/pdf` as blob, create object URL,
  trigger `<a download>` click, revoke URL.
  "E-Mail senden" → MUI Dialog with optional override email TextField + Send button
  → calls `useSendInvoiceEmail()`.
  "Stornieren" → confirmation dialog → calls `useCancelInvoice()`.

- [ ] **Step 4: Cancelled state**
  Show read-only view only. No action buttons.
  Display "STORNIERT" watermark chip prominently.

---

## Task 15: Frontend — MandantSettingsPage + Routing

**Files:**
- Create: `frontend/src/pages/MandantSettingsPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: MandantSettingsPage — Bankverbindung tab**
  IBAN (34 chars max), BIC (11 chars max) TextFields with RHF+Zod.
  Save button → PUT /mandants/{id}.

- [ ] **Step 2: MandantSettingsPage — E-Mail (SMTP) tab**
  Fields: SMTP-Host, Port (number), Benutzername, Passwort (type=password, masked),
  Absender-E-Mail, Absendername.
  "Testmail senden" button → POST /mandants/smtp-test → show success snackbar or
  error alert with SMTP error details.

- [ ] **Step 3: Add routes to App.tsx**
  ```tsx
  <Route path="/invoices" element={<InvoicesPage />} />
  <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
  <Route path="/customers" element={<CustomersPage />} />
  <Route path="/settings/mandant" element={<MandantSettingsPage />} />
  ```

- [ ] **Step 4: Add sidebar nav items in Layout.tsx**
  After existing items add:
  - "Rechnungen" → `/invoices` (ReceiptIcon)
  - "Kunden" → `/customers` (PeopleIcon)
  - Divider, then "Einstellungen" → `/settings/mandant` (SettingsIcon)

---

## Task 16: Frontend Tests

**Files:**
- Create: `frontend/src/features/invoices/__tests__/lineItemCalc.test.ts`

- [ ] **Step 1: Line item calculation unit tests**
  Test the calculation functions used in LineItemsTable and totals preview:
  - Single line: qty=2, price=5000 (cents), rate=0.19 → net=10000, vat=1900, gross=11900
  - Mixed rates: 19% + 7% → correct per-bucket and total
  - Zero rate: vat_amount=0
  - Quantity with decimals: 1.5 × 4000 = 6000

- [ ] **Step 2: Run full frontend test suite**
  ```bash
  cd frontend && npm test -- --run
  ```
  All tests (formatters + new line item tests) must pass.

---

## Completion Checklist

- [ ] `uv run pytest tests/ -q` — all tests pass (target: 80+ tests after new ones)
- [ ] `cd frontend && npm test -- --run` — all tests pass
- [ ] `docker compose up --build -d && docker compose exec backend uv run alembic upgrade head`
- [ ] Smoke test: create draft invoice, issue it, verify booking in Buchungsjournal, download PDF
- [ ] Smoke test: update SMTP settings, send test email
- [ ] Update `memory/project_status.md` with Phase 3 status
- [ ] Commit: `feat(backend): Add invoice module — sequences, CRUD, issue/cancel, PDF, email`
- [ ] Commit: `feat(frontend): Add Rechnungen UI — InvoicesPage, InvoiceFormDialog, InvoiceDetailPage`
- [ ] Open PR: `feature/backend-phase3-rechnungen → main`
