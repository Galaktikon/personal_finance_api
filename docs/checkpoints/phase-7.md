# Phase 7 checkpoint — local deployment package

**Date:** 2026-10-28  
**Status:** Local deployment package and checks passed. The user chose to keep deployment local for now; no public service was created.

## Delivered

- Added a [Render Blueprint](../../render.yaml) for a free, manually deployed Docker web service with `/health/ready` checks and prompted Neon database/Auth URLs.
- Packaged Alembic migrations into the Docker image and made startup run `alembic upgrade head` before binding to `PORT`.
- Added production configuration validation for TLS PostgreSQL URLs and tests that configuration errors do not echo database passwords.
- Added a [deployment smoke script](../../scripts/smoke_deployment.py), [deployment and troubleshooting guide](../deployment.md), [reviewer walkthrough](../reviewer-guide.md), and [verification report](../final-report.md).
- Added an optional manual GitHub Actions deploy job that runs after CI and targets a reviewed commit when `RENDER_DEPLOY_HOOK_URL` is configured.

## Verification performed

- `uv sync --locked --all-groups`, `ruff format --check .`, `ruff check .`, `mypy app`, `uv lock --check`, and `git diff --check` passed.
- `pytest -q` against local PostgreSQL: 72 passed, 1 Starlette/httpx deprecation warning.
- `alembic check` reported no schema drift. The Docker image built successfully from the lockfile.
- A temporary local container bound to Render's `PORT=10000` and passed liveness, readiness, OpenAPI, and anonymous-access checks through the deployment smoke script.
- A second container started against a newly created empty local PostgreSQL database, migrated it to revision `1a4b_phase4`, and passed readiness; both container and temporary database were removed.
- `render.yaml` and the GitHub CI workflow parsed successfully as YAML in an ephemeral container. Render's Blueprint acceptance was not tested against a live workspace.
- A synthetic Ed25519 API test exercised the optional authenticated smoke path. No real Neon-issued token was used.
- Relative Markdown links in the README and docs were checked locally.

## Setup and run

Use the [README](../../README.md#local-setup) for the local API and PostgreSQL. Follow the [reviewer guide](../reviewer-guide.md) to run synthetic-auth tests without Neon. The [deployment guide](../deployment.md) and checked-in Blueprint are prepared for a later Render and Neon setup; they have not been applied remotely.

## Remaining release gates

The user requested local deployment only for now. When they choose to publish, connect or provide a Neon branch with Auth enabled and a Render service, push the reviewed commit, confirm remote CI, complete a live sign-in/JWT/JWKS/API smoke test, check two-user isolation, and run the synthetic demo on the deployed URL. Until those checks pass, the MVP has no verified public deployment.
