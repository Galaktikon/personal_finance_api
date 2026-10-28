# Reviewer walkthrough

This is a backend API portfolio project. It keeps account and transaction data per verified Neon Auth user, imports CSV/JSON statements, categorizes transactions, matches internal transfers, and reports cash flow. The [architecture diagram](diagrams/system-architecture.mmd), [entity relationship diagram](diagrams/entity-relationships.mmd), and [API contract](api-contracts.md) explain the design.

## Quick public review

With a deployed base URL, open `/docs` for the interactive OpenAPI schema. `GET /health/live` should return `{"status":"ok"}` and `/health/ready` should return the same when Neon is reachable. Unauthenticated `GET /api/v1/accounts` should return `401`. Run the [smoke script](../scripts/smoke_deployment.py) to check these endpoints and the required OpenAPI paths.

Protected routes require a JWT obtained by signing in through the paired branch's Neon Auth SDK and calling `authClient.token()`. The [README](../README.md#local-setup) shows the Bearer header. The token is short-lived and must come from the same branch as the application database. Once signed in, run the [synthetic demo](demo.md) using `DEMO_BEARER_TOKEN`; it creates only invented records and can be replayed without duplicate transactions. Check the summary's expected income `2500.00`, expenses `130.00`, refunds `20.00`, and net cash flow `2390.00`.

## Local verification without a Neon account

After [local setup](../README.md#local-setup), run the synthetic API tests against the local PostgreSQL database:

```powershell
$env:TEST_DATABASE_URL = 'postgresql+psycopg://finance:finance_local_only@127.0.0.1:5432/finance'
uv run pytest tests/api/test_phase4.py::test_synthetic_demo_is_repeatable tests/api/test_phase5.py::test_summary_reconciles_independent_totals -q
```

The tests create and roll back invented transactions, sign synthetic Ed25519 JWTs, and check the same import and analytics paths as a deployed reviewer flow. They do not make a live Neon Auth claim. The complete suite, clean migration probe, and Docker smoke results are recorded in the [Phase 6 checkpoint](checkpoints/phase-6.md).

## Boundaries

The API supports USD and exact two-decimal amounts. Duplicate fingerprints without external IDs are advisory. Monthly trends omit empty months, and percentages are deferred. A hosted service on Render's free plan may sleep when idle. See the [deployment guide](deployment.md) and [Phase 7 checkpoint](checkpoints/phase-7.md) for live verification status.
