# Phase 1 checkpoint — repository and foundation

**Date:** 2026-10-28  
**Status:** Local acceptance checks passed; GitHub Actions execution awaits a push.

## Delivered

- Locked Python 3.11 dependencies with uv and created the FastAPI entry point.
- Added validated environment settings, a SQLAlchemy/psycopg connection, and an empty Alembic baseline revision.
- Added database-independent liveness and PostgreSQL-backed readiness endpoints.
- Added local Docker Compose PostgreSQL, an API Dockerfile, `.env.example`, and GitHub Actions checks.
- Documented setup, checks, and current scope in the root README.

## Verification performed

- `uv sync --locked --all-groups` completed.
- `ruff check .` and `ruff format --check .` passed.
- `mypy app` passed.
- Alembic `upgrade head` applied revision `0001_foundation` to local PostgreSQL.
- `pytest -q` passed with `TEST_DATABASE_URL` set: 7 passed, 1 Starlette/httpx deprecation warning.
- Docker image built from the lockfile; `/health/live` and `/health/ready` both returned `200` and `{"status":"ok"}` against local PostgreSQL.
- `.env`, `.venv`, and `.uv-cache` are ignored by Git.

## Setup and run

Follow the [README local setup](../../README.md#local-setup). Start Docker Desktop first. The local database container was stopped after verification; its named volume remains. Set a separate `TEST_DATABASE_URL` for optional local integration tests.

## Known limits and next gate

The migration establishes only the Alembic baseline; Phase 2 adds domain tables. Authentication and business routes are not yet implemented. GitHub Actions is configured but has not run on the remote service in this checkpoint. Phase 2 begins with money utilities, transaction semantics, models, constraints, migrations, and PostgreSQL-backed domain tests.
