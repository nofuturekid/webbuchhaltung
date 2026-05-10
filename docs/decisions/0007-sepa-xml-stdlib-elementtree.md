# ADR-0007 — SEPA XML Generation via stdlib xml.etree.ElementTree

*2026-05-10*

## Decision

Use Python's stdlib `xml.etree.ElementTree` for generating SEPA
pain.001.003.03 XML files instead of the `lxml` third-party library.

## Context

Phase 5 adds SEPA batch payment export (pain.001.003.03) for vendor invoices.
The two realistic library choices were:

1. **`lxml`** — mature, fast, supports XPath and XSLT. However, `lxml` links
   against `libxml2` and `libxslt` C extensions, which have no pre-built wheel
   for Python 3.14 as of 2026-05. Installing it in the backend container
   requires build toolchain packages, increases image size by ~40 MB, and
   introduces a C-level dependency that must be rebuilt on every Python minor
   version upgrade.

2. **`xml.etree.ElementTree`** (stdlib) — available in every CPython release,
   zero additional dependencies, zero container image growth. Sufficient for
   generating well-formed pain.001.003.03 documents, which do not require
   XSLT transforms or XPath queries.

The pain.001.003.03 schema is a fixed, well-known namespace
(`urn:iso:std:iso:20022:tech:xsd:pain.001.001.03`). Generating it with
`ElementTree` requires only `SubElement`, namespace registration, and
`indent()` (available from Python 3.9). No XPath or schema validation is
needed at generation time; banks validate on receipt.

## Consequences

- No new runtime dependency. The backend container image stays lean.
- Python 3.14 compatibility is guaranteed without any wheel rebuild.
- XSLT transforms or XSD validation against the pain.001 schema are not
  possible with stdlib alone. If these are required in the future (e.g. for
  automated rejection analysis), adding `lxml` at that point is straightforward
  — the XML generation function has a clear interface boundary.
- The generated XML is validated end-to-end in QA by checking element
  names, namespace prefixes, and required fields (BIC, IBAN, amount) rather
  than against the full XSD, which is acceptable for the current test scope.
