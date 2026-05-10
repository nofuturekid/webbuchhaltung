# ADR-0003 — Agent Pipeline Order for Feature Branches

*2026-05-10*

## Decision
Feature branches follow a fixed agent pipeline before merging to develop/main:
Backend-Agent → (QA-Agent ‖ Frontend-Agent) → Docs-Agent → Tax/Compliance-Agent →
Security-Agent → Review-Agent → merge.

## Context
The project uses a multi-agent orchestration model where each domain (backend, frontend,
database, QA, docs, tax, security, review) is handled by a separate Claude Code sub-agent.
With nine agents operating on overlapping artifacts, pipeline order determines which
conflicts are even possible and which gates are meaningful.

Key constraints that drove the ordering:
1. **Backend defines contracts**: Pydantic schemas and OpenAPI responses must be stable
   before the frontend or QA agents consume them.
2. **QA and Frontend are independent** after the backend contract is fixed, so they can
   run in parallel to reduce wall-clock time.
3. **Docs-Agent** needs final code to verify endpoint prose and generate the CHANGELOG;
   running it before code is stable produces stale output.
4. **Tax/Compliance-Agent** is a domain gate: it checks GoBD immutability, VAT rates, and
   SKR03/04 account validity. It must see the final implementation, not a draft.
5. **Security-Agent** runs last among the substantive agents so it can scan the complete
   set of changes, including any files added by QA or docs.
6. **Review-Agent** is the final human-readable summary gate before the merge request is
   opened; it consumes the outputs of all prior agents.

## Consequences
- A bug found by the Tax- or Security-Agent requires looping back to the Backend-Agent,
  which re-triggers the downstream agents. This is intentional: correctness over speed.
- Parallel spawning of QA + Frontend saves approximately 30–60 minutes per feature cycle
  on medium-sized features.
- The Docs-Agent is non-blocking: it can warn about missing summaries without halting the
  pipeline. Only Tax- and Security-Agents can block a merge.
- New agent types (e.g. a future Performance-Agent) should be inserted before Review-Agent
  and after the domain they analyze (backend perf → after Backend-Agent).
