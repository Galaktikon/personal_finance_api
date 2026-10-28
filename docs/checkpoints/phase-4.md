# Phase 4 checkpoint — imports, categorization, and transfers

**Date:** 2026-10-28  
**Status:** Local synthetic and PostgreSQL acceptance checks passed. Remote CI and live Neon Auth branch verification remain open.

## Delivered

- Added CSV and JSON multipart preview and commit endpoints, import history, row outcomes, file and row limits, and sanitized errors.
- Implemented account/source scoped external ID duplicate detection, advisory fingerprints for rows without IDs, user-scoped idempotency keys, and pending-to-posted reconciliation that preserves manual categories.
- Added active user and system categorization rules with deterministic precedence and CRUD for user-owned rules.
- Added transfer matching and unmatching with classification snapshots and transaction revisions.
- Added database migration and constraints for import idempotency, reconciliation counts, row warnings, external ID uniqueness, and transfer restoration snapshots.
- Accepted the duplicate and idempotency policy in [ADR-004](../adr/ADR-004-duplicate-detection-and-idempotency.md) and documented the [upload schema](../import-pipeline.md) and [API contract](../api-contracts.md).

## Verification performed

- `uv sync --locked --all-groups` succeeded after adding multipart support.
- `ruff check .`, `ruff format --check .`, and `mypy app` passed.
- `pytest -q` against local PostgreSQL: 59 passed, 1 Starlette/httpx deprecation warning.
- `alembic upgrade head` applied the Phase 4 migration; `alembic check` reported no schema drift. `uv lock --check` and `git diff --check` passed.
- Synthetic API tests cover preview without transaction or history writes, partial row failure, idempotent replay and conflict, duplicate warnings, CSV and JSON, pending reconciliation including two versions in one file, manual category survival, rule precedence and ownership, transfer restoration and ownership, import rollback on persistence failure, and upload limits.

## Setup and run

Follow the [README](../../README.md#local-setup). Run `uv run alembic upgrade head` after installing locked dependencies. Set `TEST_DATABASE_URL` to a migrated PostgreSQL database for the full suite. The [import guide](../import-pipeline.md) defines the file columns and multipart request. Local authentication tests issue synthetic Ed25519 tokens and do not need a Neon branch.

## Known limits and next gate

Fingerprint matches are advisory because identical purchases can be legitimate. A source that changes its external ID between pending and posted cannot reconcile automatically. Import preview reflects current database state and commit checks again; concurrent changes may change its outcome. A live Neon Auth branch smoke test and remote GitHub Actions run remain pending. Phase 5 adds analytics and independent expected-total verification.
