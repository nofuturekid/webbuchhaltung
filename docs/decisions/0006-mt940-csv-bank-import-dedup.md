# ADR-0006 — MT940/CSV Bank Import Deduplication Strategy

*2026-05-10*

## Decision

Use a SELECT-first + conditional INSERT strategy (application-level deduplication
via `source_ref`) rather than PostgreSQL's `ON CONFLICT DO NOTHING` for bank
statement import deduplication.

## Context

Phase 5 adds bank statement import for MT940 and CSV formats. Operators may
re-import the same statement file (e.g. after a sync error), so duplicate
transactions must be silently skipped rather than raising an error.

Two approaches were considered:

1. **`INSERT … ON CONFLICT (source_ref) DO NOTHING`** — single round trip,
   atomic, idiomatic PostgreSQL. Rejected because MariaDB 10.11 uses
   `INSERT IGNORE` with different semantics, and both databases must be
   fully supported without branching SQL.

2. **SELECT-first + INSERT** — query for an existing row by `source_ref`; skip
   if found, insert if not. Two round trips per transaction but works identically
   on PostgreSQL 16 and MariaDB 10.11 without any dialect branching.

Approach 2 was chosen. Import operations are infrequent (operator-triggered,
not high-frequency), so the extra round trip is not a performance concern.
`source_ref` is indexed (unique index on `(mandant_id, source_ref)`) so the
SELECT is fast.

## Consequences

- Import is safe to re-run: already-imported transactions are skipped without
  error or duplicate entries.
- The `source_ref` column carries the dedup key (MT940: bank reference + value
  date; CSV: row hash). Callers must always populate it; a missing `source_ref`
  raises a validation error before the database is touched.
- If a future deployment becomes PostgreSQL-only, the SELECT-first approach can
  be replaced with `ON CONFLICT` for a minor performance gain — the service layer
  interface does not change.
- MariaDB compatibility is preserved without conditional SQL or dialect-specific
  ORM flags.
