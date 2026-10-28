# ADR-005 — Analytics definitions

**Status:** Accepted (project plan)  
**Decision date:** 2026-10-27

## Decision

For posted transactions, gross income is the sum of income; gross expenses are the absolute sum of expenses; refunds are the sum of refund amounts. Net spending is gross expenses minus refunds. Net cash flow is gross income minus gross expenses plus refunds. Internal transfers are excluded. Preserve negative net spending when refunds exceed expenses.

Use `start_date <= transaction_date < end_date`. Return zero amounts for empty periods. Document and test zero-denominator percentage behavior before publishing percentage metrics.

Phase 5 publishes no percentages. Monthly trends include only months with posted activity. Category and merchant breakdowns include expenses and refunds, including negative net spending where refunds exceed expenses. Empty list results are `[]`.

## Consequences

Every analytics endpoint and synthetic expected-total fixture must reconcile to these formulas. Credit card payments do not double-count purchases. Pending and voided records are excluded by default.
