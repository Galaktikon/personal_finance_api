# Phase 6 checkpoint — hardening and end-to-end verification

**Date:** 2026-10-28  
**Status:** Local PostgreSQL, clean-migration, and container smoke checks passed. Live Neon Auth branch validation and remote GitHub Actions remain deployment gates.

## Delivered

- Added sanitized `422` validation responses and generic `500` responses with a fixed error log event. The documented Uvicorn command and Docker image disable raw access logs.
- Added a configurable overall request body limit (`REQUEST_MAX_BYTES`, default 3 MB) that checks declared and streamed bodies, with configuration validation against the import file limit.
- Expanded PostgreSQL API tests for transfer match/unmatch rollback, private-value redaction, streamed request limits, cross-user import preview and rule list access, and the synthetic demo's repeat import.
- Added an invented [CSV statement and demo loader](../demo.md) and a local [clean migration probe](../../scripts/verify_clean_migration.py).

## Verification performed

- `uv sync --locked --all-groups`, `ruff format --check .`, `ruff check .`, `mypy app`, `uv lock --check`, and `git diff --check` passed.
- `pytest -q` against local PostgreSQL: 69 passed, 1 Starlette/httpx deprecation warning.
- `alembic check` reported no schema drift. The clean migration probe created a new temporary local database, applied all three revisions, checked drift and both health routes, and removed the temporary database.
- `docker build -t personal-finance-api:phase6 .` succeeded. A temporary container served `200` from `/health/live` and `/health/ready` against local PostgreSQL, then was stopped.
- The demo test ran the loader twice with synthetic JWTs and confirmed the same import job and expected posted summary totals.

## Setup and run

Follow the [README](../../README.md#local-setup), including the locked dependency install and database migration. Run the [demo workflow](../demo.md) with a token from a paired Neon Auth branch. For local verification, set `TEST_DATABASE_URL` to a migrated PostgreSQL database and run `uv run pytest -q`; run `uv run --all-groups python scripts/verify_clean_migration.py` for the disposable local database probe.

## Known limits and next gate

The local gate is ready for a controlled portfolio deployment, but no live Neon Auth branch URL was available, so a real sign-in/token/API smoke test was not run. Remote GitHub Actions has not run. Hosting must keep raw request access logs disabled and apply an ingress body limit alongside the application limit. Phase 7 configures deployment, verifies these external gates, and publishes the final portfolio documentation.
