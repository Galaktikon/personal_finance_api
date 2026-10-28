# Phase 5 checkpoint — analytics

**Date:** 2026-10-28  
**Status:** Local synthetic and PostgreSQL acceptance checks passed. Remote CI and live Neon Auth branch verification remain open.

## Delivered

- Added authenticated, user-scoped summary, monthly trend, category breakdown, and merchant breakdown endpoints.
- Applied the accepted income, expense, refund, net spending, and net cash flow formulas to posted rows only, excluding transfers.
- Added owned-account and inclusive-start/exclusive-end date filters, pagination for list results, stable ordering, decimal-string amounts, and empty-result behavior.
- Documented response fields, omission of inactive months, merchant normalization, uncategorized groups, and the decision to publish no percentages yet.

## Verification performed

- `ruff check .`, `ruff format --check .`, and `mypy app` passed.
- `pytest -q` against local PostgreSQL: 64 passed, 1 Starlette/httpx deprecation warning.
- `alembic check` reported no schema drift; `uv lock --check` and `git diff --check` passed. No schema migration or dependency change was needed.
- Synthetic ledger tests independently calculate February leap-day and March totals, a refund-heavy negative-spending month, category and merchant reconciliation, case/whitespace merchant normalization, card payment transfer exclusion, pending and voided exclusion, account/date filters, empty periods, pagination, and two-user isolation.

## Setup and run

Follow the [README](../../README.md#local-setup) and run the checks documented there with `TEST_DATABASE_URL` set to a migrated PostgreSQL database. The [analytics API contract](../api-contracts.md#phase-5-analytics-contract) describes each route and response. Local tests use synthetic Ed25519 tokens and do not need a Neon branch.

## Known limits and next gate

Monthly trends return only months with posted activity; they do not fill gaps with zero rows. Percentages are deferred because a useful denominator and zero-denominator convention need to be chosen, especially when refunds exceed expenses. A live Neon Auth branch smoke test and remote GitHub Actions run remain pending. Phase 6 hardens the API and runs end-to-end verification.
