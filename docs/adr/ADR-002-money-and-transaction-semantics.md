# ADR-002 — Money and transaction semantics

**Status:** Accepted (project plan)  
**Decision date:** 2026-10-27

## Decision

Use `Decimal` in Python, `NUMERIC(19,2)` in PostgreSQL, decimal strings in JSON, and USD only. Reject excess precision. Persist explicit transaction kind and `pending`/`posted`/`voided` status. Income and refunds are positive; expenses and transfer-out are negative; transfer-in is positive.

Link both sides of an internal transfer. Credit card payments are transfers; purchases are expenses. Analytics include posted transactions by default and exclude transfers. Date ranges are inclusive at start and exclusive at end.

## Consequences

Validation must prevent sign/kind mismatch and floating-point input from silently changing money. Imports and manual operations follow the same domain rules. See [financial rules](../financial-rules.md) for formulas and examples.
