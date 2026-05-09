# Rechnungen (Ausgangsrechnungen) — Design Spec

**Date:** 2026-05-09
**Status:** Approved
**Scope:** Phase A — core invoices, PDF, email; Phase B — template branding + Monaco editor

---

## 1. Goal

Add outbound invoice (Ausgangsrechnung) management to WebBuchhaltung:
numbered invoice sequences, PDF generation, automatic double-entry booking on issue,
email delivery, and (Phase B) fully customizable PDF templates per mandant.

---

## 2. Architecture

Standalone invoice module alongside existing accounting core. Invoices are a
separate domain that *triggers* bookings — the booking subsystem remains unchanged.
No full CRM; customer management is lightweight (inline on invoice + a simple
customer list page). All PDF rendering is server-side (weasyprint).

---

## 3. Data Model

### 3.1 New tables

#### `customers`
```
id              UUID PK
mandant_id      FK → mandants.id  NOT NULL
name            VARCHAR(200) NOT NULL
street          VARCHAR(200)
postal_code     VARCHAR(20)
city            VARCHAR(100)
country         VARCHAR(2) DEFAULT 'DE'
vat_id          VARCHAR(30)          -- Kunden-USt-IdNr. (optional)
email           VARCHAR(254)
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

#### `invoice_sequences`
```
id              UUID PK
mandant_id      FK → mandants.id  NOT NULL  UNIQUE
prefix          VARCHAR(20) DEFAULT 'RE'    -- e.g. "RE", "2026-"
next_number     INTEGER DEFAULT 1
year_reset      BOOLEAN DEFAULT TRUE        -- reset counter each calendar year
last_reset_year INTEGER                     -- tracks when last reset happened
```

#### `invoices`
```
id              UUID PK
mandant_id      FK → mandants.id  NOT NULL
customer_id     FK → customers.id  NOT NULL
invoice_number  VARCHAR(50) NOT NULL  UNIQUE  -- e.g. "RE-2026-001"
status          ENUM('draft','issued','cancelled')  DEFAULT 'draft'
issue_date      DATE
due_date        DATE
currency        CHAR(3) DEFAULT 'EUR'
net_total_cents INTEGER                  -- computed, stored for GoBD
vat_total_cents INTEGER
gross_total_cents INTEGER
notes           TEXT
booking_id      FK → bookings.id  NULLABLE  -- set when issued
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

GoBD note: once `status = 'issued'`, the invoice is immutable. Corrections via
credit note (Storno-Rechnung) only — represented as a new invoice with negative
amounts referencing the original.

#### `invoice_line_items`
```
id              UUID PK
invoice_id      FK → invoices.id  NOT NULL
position        SMALLINT NOT NULL            -- sort order
description     TEXT NOT NULL
quantity        NUMERIC(10,3) NOT NULL
unit            VARCHAR(20)                  -- "Std.", "Stk.", "Pauschale", …
unit_price_cents INTEGER NOT NULL
vat_rate        NUMERIC(5,4) NOT NULL        -- 0.19, 0.07, 0.00
net_total_cents INTEGER                      -- quantity × unit_price_cents
vat_amount_cents INTEGER
```

#### `invoice_templates` (Phase B — created in Phase A with defaults)
```
id              UUID PK
mandant_id      FK → mandants.id  NOT NULL  UNIQUE
logo_path       VARCHAR(500)                 -- server-side file path / S3 key
primary_color   CHAR(7) DEFAULT '#000000'    -- hex
font_family     VARCHAR(100) DEFAULT 'Arial, sans-serif'
header_text     TEXT                         -- appears above line items
footer_text     TEXT                         -- payment terms / legal notice
payment_terms_text VARCHAR(200) DEFAULT 'Zahlbar innerhalb von 14 Tagen'
custom_html_template TEXT NULLABLE           -- Phase B: raw Jinja2 HTML
use_custom_template BOOLEAN DEFAULT FALSE    -- Phase B: toggle
updated_at      TIMESTAMP
```

### 3.2 Extended tables

#### `mandants` — add columns
```
iban            VARCHAR(34)
bic             VARCHAR(11)
smtp_host       VARCHAR(253)
smtp_port       SMALLINT DEFAULT 587
smtp_user       VARCHAR(254)
smtp_password   VARCHAR(500)    -- encrypted at rest
smtp_from       VARCHAR(254)
smtp_from_name  VARCHAR(200)
```

#### `bookings` — add column
```
invoice_id      FK → invoices.id  NULLABLE
```

---

## 4. Booking Logic on Issue

When an invoice transitions from `draft` → `issued`, the backend creates a
compound booking (one booking per VAT bucket):

| Tax bucket | Debit account | Credit account |
|-----------|---------------|----------------|
| 19% (Regelsteuersatz) | 1400 Forderungen | 8400 Erlöse 19% USt |
| 7% (ermäßigt) | 1400 Forderungen | 8300 Erlöse 7% USt |
| 0% / §13b | 1400 Forderungen | 8200 Erlöse steuerfrei |

Each booking amount = gross total for that VAT bucket.
The VAT portion is implicit (derived from account rules) — no separate USt
booking line is generated; that follows from the SKR03 account definitions
already seeded in Phase 1.

`invoices.booking_id` is set after the booking is persisted.

---

## 5. API Endpoints

All endpoints are under `/api/v1/` and require `Authorization: Bearer <token>`.

### Customers
```
GET    /customers                   list (mandant-scoped)
POST   /customers                   create
GET    /customers/{id}              detail
PUT    /customers/{id}              update
DELETE /customers/{id}              soft-delete (if no invoices reference it)
```

### Invoices
```
GET    /invoices                    list (filterable: status, customer, date range)
POST   /invoices                    create draft
GET    /invoices/{id}               detail with line items
PUT    /invoices/{id}               update draft (forbidden if issued/cancelled)
DELETE /invoices/{id}               delete draft
POST   /invoices/{id}/issue         draft → issued, triggers booking
POST   /invoices/{id}/cancel        issued → cancelled (creates Storno-Buchung)
GET    /invoices/{id}/pdf           returns PDF binary (application/pdf)
POST   /invoices/{id}/send-email    send PDF to customer.email (or override address)
```

### Template (Phase A: GET/PUT basics; Phase B: logo upload, preview, Monaco)
```
GET    /invoice-template            get mandant template settings
PUT    /invoice-template            update branding fields
POST   /invoice-template/logo       upload logo (multipart/form-data)
POST   /invoice-template/preview    render preview PDF with given template data
```

### Sequences
```
GET    /invoice-sequences           get current sequence settings
PUT    /invoice-sequences           update prefix / year_reset
```

---

## 6. PDF Generation

**Library:** weasyprint (pure Python, no external process needed)
**Template engine:** Jinja2 `SandboxedEnvironment` (safe for user-supplied HTML in Phase B)

### Layout A — Classic (default)
- Serif font (optionally overridden by template)
- Header: logo (if set) + company name left; "RECHNUNG" + number/date right
- Recipient block below header separator
- Line items table: Pos., Beschreibung, Menge, Einheit, Einzelpreis, Betrag
- Totals block (Netto, USt per rate, Brutto)
- Footer: IBAN/BIC, payment terms, legal text

### Context variables available in templates
```jinja2
{{ invoice.invoice_number }}
{{ invoice.issue_date | date }}
{{ invoice.due_date | date }}
{{ mandant.name }}, {{ mandant.street }}, …
{{ mandant.iban }}, {{ mandant.bic }}
{{ customer.name }}, {{ customer.street }}, …
{{ line_items }}   -- list of line item dicts
{{ net_total }}, {{ vat_total }}, {{ gross_total }}  -- formatted strings
{{ template.header_text }}, {{ template.footer_text }}
```

### Phase B: custom HTML template
If `use_custom_template = True`, the `custom_html_template` Jinja2 string is
rendered with `SandboxedEnvironment` using the same context variables. The
result is passed to weasyprint as HTML. If rendering fails (syntax error,
undefined variable), the API returns HTTP 422 with the Jinja2 error message —
no fallback to built-in template (explicit failure).

---

## 7. Email

**Library:** Python `smtplib` (stdlib) + `email.mime` for multipart
**Config:** per-mandant SMTP (host, port, user, password, from, from_name)
**Password storage:** encrypted with Fernet using a key derived from
`settings.SECRET_KEY` — stored encrypted in DB, decrypted only at send time.

Send flow:
1. Render PDF for the invoice
2. Build MIME multipart: text/plain body (German template) + PDF attachment
3. Connect to mandant SMTP, send, disconnect
4. On success: log to invoice notes, return 200
5. On failure: return 502 with SMTP error details (do not silently swallow)

The `/send-email` request body allows overriding the recipient address so the
user can send a test copy to themselves.

---

## 8. Frontend

### New routes (added to App.tsx)
```
/invoices              InvoicesPage       list + create button
/invoices/:id          InvoiceDetailPage  view + issue + cancel + PDF + email
/customers             CustomersPage      list + inline create/edit
/settings/mandant      MandantSettingsPage  SMTP + IBAN + Phase B template
```

### InvoicesPage
- MUI DataGrid: Nummer, Kunde, Datum, Fälligkeit, Status-Chip (draft/issued/cancelled), Brutto
- FAB or top-right button → opens InvoiceFormDialog (full-page drawer)
- Filter bar: status select, date range pickers

### InvoiceFormDialog (create/edit draft)
- Customer: MUI Autocomplete with search + "Neuen Kunden anlegen" inline option
- Issue date + due date (date pickers)
- Line items: dynamic add/remove rows — Beschreibung, Menge, Einheit, Einzelpreis, MwSt-Satz (select: 19%/7%/0%)
- Computed totals preview (Netto, USt, Brutto) — client-side, re-calculated on every change
- Save as draft button

### InvoiceDetailPage
- Read-only display of all invoice fields
- Action buttons (top-right):
  - Draft: "Ausstellen" (issue) → confirmation dialog → POST /issue
  - Issued: "PDF herunterladen", "E-Mail senden" dialog, "Stornieren"
  - Cancelled: read-only view only
- Status chip + booking reference if issued

### CustomersPage
- Simple table: Name, Stadt, E-Mail, USt-IdNr., Aktionen
- Inline create form (MUI Dialog)

### MandantSettingsPage (Phase A: SMTP + bank details)
- Tabs: "Bankverbindung", "E-Mail (SMTP)", (Phase B: "Rechnungsvorlage")
- SMTP: host, port, user, password (masked), from, from_name
- "Testmail senden" button → POST /mandants/smtp-test

---

## 9. Sequence Numbering

Format example: `RE-2026-001`
- Prefix + year (if `year_reset=True`) + zero-padded counter (min 3 digits)
- Year reset: on first invoice of a new calendar year, `next_number` resets to 1 and `last_reset_year` is updated — done atomically with `SELECT … FOR UPDATE` on the sequence row
- The invoice_number is assigned at `POST /invoices` (draft creation), not at issue time — this ensures a draft always has a number visible to the user

---

## 10. Phasing

### Phase A — Core (this spec)
- All DB tables and migrations
- All backend API endpoints
- PDF generation with built-in Layout A template
- Email sending (per-mandant SMTP)
- Frontend: InvoicesPage, InvoiceFormDialog, InvoiceDetailPage, CustomersPage
- MandantSettingsPage with SMTP + IBAN tabs
- `invoice_templates` table created with defaults (no UI for editing yet)

### Phase B — Template Editor (follow-up spec)
- MandantSettingsPage: "Rechnungsvorlage" tab
  - Logo upload (drag-and-drop + preview)
  - Branding fields: primary color (color picker), font family, header/footer text
  - Monaco editor for raw Jinja2 HTML (`use_custom_template` toggle)
  - Live preview button → renders PDF in an `<iframe>` via `/invoice-template/preview`
- Backend: logo upload to disk/S3, PUT /invoice-template branding fields, preview endpoint

---

## 11. Testing Strategy

### Backend
- Unit tests: invoice number generation (year reset, concurrent increment), PDF rendering (mocked weasyprint), booking creation per VAT bucket
- Integration tests: full issue flow (draft → issued → booking exists), cancel flow
- SMTP: tested with a mock SMTP server (smtpd or aiosmtpd in test mode)

### Frontend
- Vitest unit tests: line item total calculation, VAT breakdowns, invoice number display formatter
- Component tests: InvoiceFormDialog save/validation, status chip rendering

---

## 12. GoBD Compliance Notes

- Issued invoices are immutable: PUT on `issued` or `cancelled` invoices returns 403
- Cancellation creates a Storno-Buchung (reversal booking) — the original booking is not deleted
- `net_total_cents`, `vat_total_cents`, `gross_total_cents` are stored on `invoices` at issue time and never recomputed — source of truth for auditing
- Invoice PDFs are generated on-demand (not stored) — acceptable under GoBD §14 UStG as long as the data is preserved in the DB and the same PDF can be regenerated deterministically
