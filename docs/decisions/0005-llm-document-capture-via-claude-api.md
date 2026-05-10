# ADR-0005 — LLM Document Capture via Claude API

*2026-05-10*

## Decision

Use Anthropic's Claude API (via the `anthropic` Python SDK) for structured data
extraction from uploaded receipts and invoices (PDFs and images). The extracted
data is presented to the user for review before any Buchungssatz is created.

## Context

Phase 4 adds a Belegerfassung (document capture) workflow. Receipts arrive as
PDFs or scanned images. Manually keying vendor, date, amount, and account for
every document is time-consuming. An LLM with vision and document capabilities
can reliably extract these fields from unstructured inputs.

The extraction step is intentionally separate from the confirmation step: the
frontend shows the file preview alongside the extracted fields so the user can
verify and correct before posting. This keeps the human in the loop and
satisfies GoBD §9 (audit trail on every posting).

Claude was chosen over generic OCR because it handles multi-page PDFs, handwritten
amounts, and non-standard invoice layouts without a training pipeline.

## Consequences

- `ANTHROPIC_API_KEY` must be set in production for `POST /documents/{id}/process`
  to work. Without it, the endpoint returns 502. The key is optional at boot so
  deployments that do not use document capture are unaffected.
- `STORAGE_ROOT` (default `/tmp/webbuchhaltung-docs`) must be backed by a named
  Docker volume (`docdata`) in production to survive container restarts.
- The `anthropic` SDK is pinned at `>=0.25.0,<1.0` to avoid breaking changes.
- LLM extraction is synchronous in Phase 4 (acceptable latency 3–10 s). If
  throughput demands grow, a background task queue (e.g. Celery/ARQ) can be
  added without changing the API surface.
- On extraction failure the service degrades gracefully: all fields are returned
  as `None` with `confidence_score=0.0` instead of raising an error, so the user
  can still manually enter the booking data.
