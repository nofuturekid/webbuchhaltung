# ADR-0008 — Bank Transaction Matching Score Algorithm

*2026-05-10*

## Decision

Score candidate booking–transaction matches using a weighted sum of three
signals (amount, date proximity, purpose keyword), and auto-apply matches
that reach a score of 0.90 or above.

## Context

Phase 5 adds automatic reconciliation of imported bank transactions against
open bookings. The matching problem requires a heuristic because:

- Amount alone is not unique (multiple invoices may share an amount).
- Date alone is not reliable (payment delays of several days are common in
  German business practice).
- Purpose strings (Verwendungszweck) are semi-structured and may contain
  truncated invoice numbers.

A rule-based weighted score was chosen over an ML model because:

- The feature set is small and interpretable.
- No training data exists at Phase 5.
- Operators need to understand and override suggestions; a score is
  explainable, a model embedding is not.

### Score components

| Signal | Condition | Points |
|--------|-----------|--------|
| Amount | Exact cent match | +0.60 |
| Date   | Within ±3 calendar days | +0.30 |
| Date   | Within ±4–7 calendar days | +0.15 |
| Purpose| Booking reference found in Verwendungszweck | +0.10 |

Maximum score: 1.00 (amount exact + date ±3d + purpose match).

The amount signal carries the most weight (0.60) because an exact cent match
is a strong indicator in accounting contexts. Date proximity is split into two
tiers to reflect that most electronic transfers settle within 3 days, while
paper-based or international transfers may take up to 7 days. The purpose
bonus is small because Verwendungszweck content is not standardised.

### Auto-apply threshold

Matches with `score >= 0.90` are applied automatically without operator
confirmation. This requires at least an exact amount match plus a date within
±3 days (0.60 + 0.30 = 0.90). Purpose match alone cannot trigger auto-apply.

All auto-applied matches are written to the GoBD audit trail (§9) with
`actor="system"`.

### Float-rounding

Scores are rounded to 4 decimal places before comparison to avoid IEEE 754
accumulation errors (e.g. 0.60 + 0.30 computing as 0.8999999…, falling
below the 0.90 threshold).

## Consequences

- Any match below 0.90 is presented to the operator for manual confirmation
  or dismissal via the `MatchingView` frontend component.
- Adding a new signal (e.g. creditor name fuzzy match) requires only a weight
  adjustment and a re-evaluation of the auto-apply threshold — the scoring
  function is a simple sum with no hidden state.
- If false-positive auto-matches occur in production, the threshold can be
  raised (e.g. to 0.95) via config without a code change.
- `apply_ignore` and `apply_unmatch` are always available to the operator for
  reverting any match, including auto-applied ones, in compliance with GoBD §9
  auditability requirements.
