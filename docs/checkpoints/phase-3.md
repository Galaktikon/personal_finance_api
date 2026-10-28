# Phase 3 checkpoint — Neon Auth and authenticated CRUD

**Date:** 2026-10-28  
**Status:** Documented Neon JWT integration and local synthetic/PostgreSQL acceptance checks passed. Live Neon branch verification and remote CI remain open.

## Delivered

- Verified and recorded Neon's documented JWT plugin flow in [ADR-003](../adr/ADR-003-neon-auth-and-authorization.md).
- Added EdDSA/JWKS verification with branch-origin issuer and audience checks, expiry and subject checks, bounded JWKS caching, key refresh, generic authentication errors, and no credential logging.
- Mapped verified subjects to unique `UserProfile` rows with race-safe insert behavior.
- Added user-scoped accounts, transactions, and categories endpoints with validation, pagination, filters, archival/voiding semantics, and transaction revisions.
- Updated configuration, OpenAPI contracts, security docs, local setup, and the authentication diagram.

## Verification performed

- `uv sync --locked --all-groups` completed with PyJWT and cryptography.
- `ruff check .`, `ruff format --check .`, and `mypy app` passed.
- `pytest -q` against local PostgreSQL passed: 52 tests, 1 Starlette/httpx deprecation warning.
- Synthetic Ed25519 tests cover valid and wrong signatures, expired/future/wrong issuer/wrong audience claims, role and banned status, and JWKS key rotation.
- API tests cover missing/invalid credentials, JWKS outage, two-user CRUD isolation, forged owner IDs, monetary validation, category scope, pagination, archival, voiding, and manual override history.

## Setup and run

Follow the [README](../../README.md#local-setup). Configure `NEON_AUTH_BASE_URL` for authenticated routes and use a JWT from the branch's Neon Auth SDK. Local tests use synthetic keys and do not need a Neon branch.

## Known limits and next gate

No Neon Auth branch URL was available, so a real sign-in/token/API smoke test was not run. The official guide documents the verification flow, but real branch behavior and deployment configuration must be confirmed before production use. GitHub Actions has not run remotely. Phase 4 adds imports, categorization rules, and transfer matching/unmatching.
