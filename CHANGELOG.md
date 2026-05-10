# Changelog

## Unreleased — Unreleased

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


### Testing

- Strengthen GoBD cancel assertions + add 7%/0% VAT tests ([`d130143`])
