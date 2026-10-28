# Synthetic demo workflow

The repository includes a small invented [CSV statement](../sample_data/demo_transactions.csv) and a [loader](../scripts/demo_synthetic.py) that exercises account and category creation, a categorization rule, import idempotency, and analytics through the public API. It does not connect to a bank or read personal finance data.

Start the API after following the [local setup](../README.md#local-setup). Authenticated routes require a Bearer JWT from the Neon Auth branch paired with the database. Supply that token to the loader through `DEMO_BEARER_TOKEN` in your process environment, then run:

```powershell
uv run --all-groups python scripts/demo_synthetic.py --base-url http://127.0.0.1:8000
```

The loader creates or reuses `Synthetic Demo Checking`, `Synthetic Demo Food`, and a Market categorization rule. It imports five rows with a stable key tied to the account, then prints summary amounts. On a fresh demo account, the expected posted totals are gross income `2500.00`, gross expenses `130.00`, refunds `20.00`, net spending `110.00`, and net cash flow `2390.00`. The pending `10.00` purchase is excluded. Running the loader again reuses the import job and does not create duplicate transactions.

Inspect `GET /api/v1/imports`, `/api/v1/transactions?account_id=<demo-account-id>`, and `/api/v1/analytics/{summary,monthly-trends,categories,merchants}?account_id=<demo-account-id>` in `/docs` to review row outcomes and breakdowns. The loader does not print the token, raw CSV rows, or response headers.

For a local clean-database check, set `TEST_DATABASE_URL` to the Docker PostgreSQL test instance and run:

```powershell
uv run --all-groups python scripts/verify_clean_migration.py
```

That probe creates a uniquely named temporary database, applies all migrations, checks schema drift and health routes, then removes only that temporary database. It does not touch the database named in `TEST_DATABASE_URL`.
