# Project Status

**Last updated:** 2026-05-10
**Phase:** Phase 5 complete — `release/phase5` branch ready; PR #8 open to main

## Done

- Phase 1–4 complete (PRs #1–#7 merged to main); 112 tests at Phase 4 end
- **Housekeeping (2026-05-10):** Auto-migrations, repo restructure src/backend + src/frontend

## Done (Phase 5 — 2026-05-10)

### Backend
- Migration 0008: bank_accounts + bank_transactions tables
- Migration 0009: vendors + vendor_invoices + AP account backfill (SKR03: 1600/1576/1571; SKR04: 3300/1406/1401)
- T3: Bank import (MT940 via mt-940 lib, CSV with German decimal), dedup by source_ref
- T4: Vendor invoice service + SEPA pain.001.003.03 XML export (stdlib ElementTree)
- T5: Advanced reports — Saldenliste, Bilanz, G+V, BWA (all MariaDB-compatible)
- T6: confirm_document extended with create_vendor_invoice=True path
- GoBD §9 fix: apply_ignore + apply_unmatch now write audit entries
- Float fix: match score rounded to 4 decimal places (IEEE 754 drift at 0.90 threshold)
- Admin endpoint: GET /api/v1/admin/audit-log (mandant-scoped, paginated, filterable)
- Tax-Agent T12: WARNING only (3 non-blocking items, 2 fixed; Vorsteuer split deferred → now done)

### Frontend
- T7: BankAccountsPage (MT940 import dialog, transaction matching view, auto-match button)
- T8: VendorsPage + VendorInvoicesPage (SEPA export button)
- T9: SaldenllistePage + BilanzPage (amber imbalance alert) + GuvPage + BWAPage
- T11: AdminPage (audit log viewer, system info, mandant stub)

### Infrastructure
- T10: Helm chart helm/webbuchhaltung/ (Chart 0.5.0), backend + frontend deployments, ingress, PVC

### Tech Debt (cleared 2026-05-10)
- SKR03 disposal accounts 4855/2680 seeded in test_assets.py `_setup()` — loss/gain paths now fully tested (commit 41574ad)
- Vorsteuer split (UStG §15): `post_vendor_invoice` creates Sammelbuchung (2 bookings sharing `entry_number` + `booking_group_id`) when `vat_coa_id` provided; `PostInvoiceDialog` gains Vorsteuer-Konto select; `vatAmountCents` prop wired in parent (commits f8ee626, 8ffc3bc)
- **188 backend tests pass**

## Done (Phase 6 — partial, 2026-05-10)

### Frontend T4 + T5 (dashboard agent)
- T4: Dashboard year selector (MUI Select, 2020–current+1), `useOpenReceivables` hook (invoices/api.ts), `useOpenPayables` hook (vendors/api.ts), three KPI cards (Offene Forderungen, Überfällige Forderungen, Offene Verbindlichkeiten) with color coding and click navigation; handles both array and paginated API response shapes
- T5 (mobile): Mobile-responsive tables — BookingList.tsx, InvoicesPage.tsx, VendorInvoicesPage.tsx hide secondary columns on xs via `sx={{ display: { xs: 'none', sm: 'table-cell' } }}`; desktop layout unchanged
- Branch: `feature/phase6-dashboard` pushed; 0 TypeScript errors

### Frontend T3 + T5 search (lists agent, 2026-05-10)
- T3: Pagination controls on BookingsPage, InvoicesPage, VendorInvoicesPage — MUI `Pagination`, `count=Math.ceil(total/50)`, page state, reset on filter change; "Seite X von Y — Z Einträge" label
- T5 (search): Debounced text search bars (300ms, no deps) on BookingsPage ("Suche (Beschreibung, Belegnr.)") and InvoicesPage ("Suche (Rechnungsnr., Kunde)"); `q` param passed to `useBookings` and `useInvoices`; no search on VendorInvoicesPage (backend not ready)
- API changes: `useInvoices` returns `InvoiceListResponse`; `useVendorInvoices` returns `VendorInvoiceListResponse`; `useBookings` accepts `q` filter; `useOpenPayables` handles paginated response shape
- `InvoiceListResponse` added to `src/frontend/src/types/invoice.ts`; `VendorInvoiceListResponse` added to `src/frontend/src/types/vendor.ts`
- Branch: `feature/phase6-lists`; 0 TypeScript errors

## Open

- **[PR #8]** `release/phase5` → `main` — push to update remote with the 3 new commits, then merge
- **[Phase 6]** `feature/phase6-dashboard` — open PR to develop when ready
- **[Phase 6]** `feature/phase6-lists` — open PR to develop when ready (depends on `feature/phase6-backend` merge first for real backend pagination on invoices)
- **[PRODUCTION]** ANTHROPIC_API_KEY, STORAGE_ROOT env vars required
- **[PRODUCTION]** helm CLI not installed — `pacman -S helm` to run lint

## Key Decisions
- See memory/project_decisions.md
- Backend test command: `cd src/backend && TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/webbuchhaltung_test uv run pytest tests/ -q`







<!-- session-end: 2026-05-10 20:48 -->
