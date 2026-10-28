# Phase 2 checkpoint — domain model and financial rules

**Date:** 2026-10-28  
**Status:** Local acceptance checks passed; GitHub Actions execution awaits a push.

## Delivered

- Decimal money parsing, USD validation, transaction signs and statuses, half-open date ranges, month bounds, and transfer-pair validation.
- SQLAlchemy models for profiles, accounts, transactions, categories, rules, imports, transfers, and revisions.
- Alembic migration `877f154026dd` with PostgreSQL checks, composite ownership foreign keys, category/rule scope triggers, and transfer integrity triggers.
- Updated financial/domain documentation and [ADR-006](../adr/ADR-006-ownership-and-schema-integrity.md).

## Verification performed

- `ruff check .`, `ruff format --check .`, and `mypy app` passed after formatting.
- `pytest -q` with local PostgreSQL passed: 32 tests, 1 Starlette/httpx deprecation warning.
- Alembic downgrade to the Phase 1 baseline and upgrade to head succeeded.
- Alembic `check` reported no schema drift.
- A fresh disposable PostgreSQL database migrated from empty through both revisions and passed `alembic check`.

## Setup and run

Follow the [README](../../README.md#local-setup). Apply `uv run alembic upgrade head` after starting PostgreSQL. For integration tests, set `TEST_DATABASE_URL` to a migrated PostgreSQL database with only synthetic test data.

## Known limits and next gate

Direct SQL writes to a `NUMERIC(19,2)` column may be rounded by PostgreSQL; application and ORM validation reject excess precision. Authenticated endpoints, system-category administration, and account/transaction lifecycle operations are Phase 3 work. Import, categorization, and transfer unmatching behavior are Phase 4 work. The remote GitHub Actions workflow has not run in this checkpoint.
