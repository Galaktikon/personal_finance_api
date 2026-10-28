# Manual Render setup and complete verification

This guide prepares a Render Docker Web Service backed by one Neon PostgreSQL branch with Neon Auth enabled. **No public service has been created for this project.** Run the local checks now; use the hosted steps when you choose to publish. Use synthetic financial data only. The checked-in [Render Blueprint](../render.yaml) is an alternative to the manual Web Service form.

Commands assume PowerShell 7, [uv](https://docs.astral.sh/uv/), Python 3.11, and Docker Desktop. Run them from the repository root. Keep database URLs, JWTs, and deploy hooks out of source, screenshots, and command arguments.

## 1. Run the full local gate

Copy [.env.example](../.env.example) to `.env`, install dependencies, start local PostgreSQL, and migrate it as shown in the [README](../README.md#local-setup). Use only the example local credentials for Docker Compose. The local test database must be disposable and contain no personal data.

```powershell
uv sync --locked --all-groups
docker compose up -d db
uv run alembic upgrade head
$env:TEST_DATABASE_URL = 'postgresql+psycopg://finance:finance_local_only@localhost:5432/finance'
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run alembic check
uv run pytest -q
uv run --all-groups python scripts/verify_clean_migration.py
docker build -t personal-finance-api:manual .
```

The test suite covers synthetic JWT verification, ownership, CRUD, imports and replay, categorization, transfers, analytics, limits, and rollback. The clean-migration probe creates and removes its own temporary **local** database. All commands must exit successfully; `alembic check` should report no new upgrade operations. The Docker build checks the production image and lockfile. See the [Phase 7 checkpoint](checkpoints/phase-7.md) for the last recorded local results.

For a local HTTP smoke check, start `uv run uvicorn app.main:app --no-access-log` in a second PowerShell window after migrating, then run `uv run --all-groups python scripts/smoke_deployment.py --base-url http://127.0.0.1:8000` in the first. It checks health, OpenAPI, and anonymous access without requiring Neon Auth. Stop the local server after the check.

Push the reviewed commit and check that the [GitHub Actions CI workflow](../.github/workflows/ci.yml) passes on that commit before deploying. CI starts an empty PostgreSQL service, applies migrations, checks schema drift, and runs the same lint, type, and test gates. A local pass does not establish a remote CI pass.

## 2. Prepare one Neon branch

1. Create a Neon project and select the branch reserved for this preview. Enable Neon Auth for **that branch**. Follow Neon's [React Auth quickstart](https://neon.com/docs/auth/quick-start/react) and [JWT guide](https://neon.com/docs/auth/guides/plugins/jwt) for client sign-in and token retrieval.
2. Copy the branch's PostgreSQL connection string and its public Auth URL from Neon. Convert only the URL scheme from `postgresql://` to `postgresql+psycopg://`; preserve the host, database, user, password, and query settings. Ensure `sslmode=require` or a stronger TLS mode is present. `DATABASE_URL` and `NEON_AUTH_BASE_URL` must refer to the same branch. The Auth URL is a base URL, not a JWT or secret key.
3. Create two disposable Neon Auth users, A and B, for the hosted isolation check. Configure the Auth app's allowed/trusted domains for the client origin used to sign them in. For a real public app, review Neon's [production checklist](https://neon.com/docs/auth/production-checklist), including email provider, verification, and OAuth settings if used.

The API has no sign-in UI. Sign users in with a Neon Auth client configured for this branch, then call `authClient.token()` to get each user's short-lived Bearer JWT. The [README example](../README.md#local-setup) shows the API request. A browser session cookie by itself will not authenticate API calls. Refresh expired tokens before a test.

## 3. Create the Render service manually

In the [Render Dashboard](https://dashboard.render.com/), select **New > Web Service**, connect the GitHub repository, and choose the reviewed branch. Verify its latest commit is the one that passed CI. Set these fields in the Web Service form:

| Render field | Value |
|---|---|
| Name | `personal-finance-api` or another unique name |
| Language/runtime | `Docker` |
| Root directory | Repository root (leave blank) |
| Dockerfile path | `./Dockerfile` |
| Docker command | Leave blank; the image command migrates then starts Uvicorn |
| Instance type | Free for a portfolio preview; confirm the selected plan in Render |
| Auto-Deploy | Off |
| Health check path | `/health/ready` |

Add these **service environment variables** in Render. Enter the two branch URLs in Render's environment editor, never in `render.yaml` or `.env` committed to Git:

| Key | Value |
|---|---|
| `APP_ENV` | `production` |
| `DATABASE_URL` | The private Neon branch URL with `postgresql+psycopg://` and TLS |
| `NEON_AUTH_BASE_URL` | The paired branch's HTTPS Neon Auth base URL |
| `PORT` | `10000` |
| `IMPORT_MAX_BYTES` | `2000000` |
| `IMPORT_MAX_ROWS` | `5000` |
| `REQUEST_MAX_BYTES` | `3000000` |

Render's [Docker documentation](https://render.com/docs/docker) explains its Docker service settings and environment behavior. The Dockerfile does not reference service secrets during build. The image runs `alembic upgrade head` at startup, then binds to `0.0.0.0:$PORT`; Render's [pre-deploy command](https://render.com/docs/deploys) is unavailable on the free Web Service plan. Use one service instance while migrations run. Keep raw URL access logging disabled at Render or any added proxy, and set an ingress body limit there as well.

Create the service and inspect the **Deploys** page. The first deploy should build successfully, migrate the branch, start the server, and pass `/health/ready`. Record the HTTPS service URL. Automatic deploys remain off; use **Manual Deploy > Deploy latest commit** (or select a specific reviewed commit) for later releases. A free service may sleep after idle and take time to wake, per [Render's free service guide](https://render.com/docs/free).

## 4. Check the public, unauthenticated surface

Replace the placeholder with your actual service URL. These checks require no Auth account:

```powershell
$base = 'https://<service>.onrender.com'
uv run --all-groups python scripts/smoke_deployment.py --base-url $base
Invoke-RestMethod "$base/health/live"
Invoke-RestMethod "$base/health/ready"
```

The script checks both health endpoints (`{"status":"ok"}`), required OpenAPI routes, the [no-login CSV demo](../README.md#no-login-csv-demo) and its sample result, and `401` for anonymous `GET /api/v1/accounts`. Inspect `$base/`, `$base/docs`, and `$base/openapi.json` in a browser. A `503` on readiness means the database dependency is not ready; a `200` liveness response alone is insufficient. Avoid placing private values in URLs.

## 5. Check live Neon Auth

Using the client paired with the same branch, sign in as test user A and obtain `data.token` from `authClient.token()`. In PowerShell 7, enter it without echoing or storing it in command history:

```powershell
$env:DEMO_BEARER_TOKEN = Read-Host -MaskInput 'User A Bearer JWT'
uv run --all-groups python scripts/smoke_deployment.py --base-url $base
$headersA = @{ Authorization = "Bearer $env:DEMO_BEARER_TOKEN" }
Invoke-RestMethod "$base/api/v1/accounts" -Headers $headersA
```

The authenticated accounts call must return a JSON array, including `[]` on a fresh user. Check the negative paths without sending a real token:

```powershell
$anonymous = Invoke-WebRequest "$base/api/v1/accounts" -SkipHttpErrorCheck
$invalid = Invoke-WebRequest "$base/api/v1/accounts" -Headers @{ Authorization = 'Bearer deliberately-invalid' } -SkipHttpErrorCheck
$anonymous.StatusCode, $invalid.StatusCode
$anonymous.Headers['WWW-Authenticate'], $invalid.Headers['WWW-Authenticate']
```

Both status codes must be `401`, with a Bearer challenge. A JWT from a different Auth branch, wrong audience, or expired session must also be rejected. Do not use a real user's token in a shared test transcript.

## 6. Load and inspect the synthetic demo

With user A's token still in `DEMO_BEARER_TOKEN`, run the loader twice:

```powershell
uv run --all-groups python scripts/demo_synthetic.py --base-url $base
uv run --all-groups python scripts/demo_synthetic.py --base-url $base
$accountsA = Invoke-RestMethod "$base/api/v1/accounts" -Headers $headersA
$demoAccount = $accountsA | Where-Object name -eq 'Synthetic Demo Checking' | Select-Object -First 1
Invoke-RestMethod "$base/api/v1/transactions?account_id=$($demoAccount.id)" -Headers $headersA
Invoke-RestMethod "$base/api/v1/imports" -Headers $headersA
Invoke-RestMethod "$base/api/v1/analytics/summary?account_id=$($demoAccount.id)" -Headers $headersA
```

On a fresh demo account, each loader run should print gross income `2500.00`, gross expenses `130.00`, refunds `20.00`, and net cash flow `2390.00`. The summary should show net spending `110.00` and four posted transactions; the fifth transaction is pending and excluded from analytics. The second run should reuse the import job and leave the transaction count unchanged. In `/docs`, inspect the demo account's import job and all four analytics routes (`summary`, `monthly-trends`, `categories`, `merchants`) with `account_id`; compare their figures with the [demo guide](demo.md) and [analytics contract](api-contracts.md#phase-5-analytics-contract). Check that no raw CSV rows or secrets appear in server logs.

## 7. Check two-user isolation

Sign in as disposable user B on the **same Neon Auth branch** and obtain B's token. Keep A's token available in `$headersA` from the prior step. Run:

```powershell
$tokenB = Read-Host -MaskInput 'User B Bearer JWT'
$headersB = @{ Authorization = "Bearer $tokenB" }
$accountsB = Invoke-RestMethod "$base/api/v1/accounts" -Headers $headersB
$accountsB | Where-Object id -eq $demoAccount.id
$response = Invoke-WebRequest "$base/api/v1/accounts/$($demoAccount.id)" -Headers $headersB -SkipHttpErrorCheck
$response.StatusCode
$response = Invoke-WebRequest "$base/api/v1/analytics/summary?account_id=$($demoAccount.id)" -Headers $headersB -SkipHttpErrorCheck
$response.StatusCode
```

B's account list must contain no A demo account; the last two status codes must both be `404`. In `/docs`, repeat the ownership check for an A transaction ID (`GET /api/v1/transactions/{id}`), A import job ID (`GET /api/v1/imports/{id}`), and A category or rule (`PATCH` on that ID using disposable input); each must return `404` or otherwise deny modification without revealing A's data. B's unfiltered transaction, import, and analytics lists must exclude A's demo. Then create one synthetic account and transaction as B and verify A cannot read them. The [full automated suite](#1-run-the-full-local-gate) covers these ownership paths and financial edge cases with synthetic JWTs; this hosted check confirms the real Neon issuer, JWKS, audience, and subject mapping.

Clear tokens from the PowerShell session when finished:

```powershell
Remove-Item Env:DEMO_BEARER_TOKEN -ErrorAction SilentlyContinue
Remove-Variable tokenB, headersA, headersB -ErrorAction SilentlyContinue
```

If the Neon branch was created only for this review, delete that branch after the review to remove its disposable Auth users and synthetic data. Otherwise, retain the isolated demo branch for a repeatable portfolio walkthrough. Do not use the demo branch for personal finances.

## 8. Release and troubleshooting

For each later release, confirm the reviewed commit's CI check, deploy that commit manually from Render's **Deploys** page, wait for `/health/ready`, and repeat sections 4–7. An optional [Render deploy hook](https://render.com/docs/deploy-hooks) can be stored as the GitHub repository secret `RENDER_DEPLOY_HOOK_URL`; manually running `workflow_dispatch` then triggers the checked commit after CI passes. A deploy hook only starts deployment: inspect Render's result and rerun the smoke and demo checks before sharing the URL.

| Symptom | Check |
|---|---|
| Build fails | `uv.lock` is current; local `docker build` passes; Dockerfile path points to root |
| Startup fails | Both URLs are set for the same Neon branch; database URL has `postgresql+psycopg://` and TLS; database user can migrate |
| Liveness `200`, readiness `503` | Neon connection and startup migration logs; Alembic revision and permissions |
| Authenticated request `401` | Fresh `authClient.token()` JWT, paired branch, issuer, audience, and JWKS per [ADR-003](adr/ADR-003-neon-auth-and-authorization.md) |
| Authenticated request `503` | Neon Auth URL and JWKS availability; an unconfigured Auth URL gives a generic service-unavailable response |
| Slow response after idle | Free plan cold start; wait for readiness and retry |

The [verification report](final-report.md) and [Phase 7 checkpoint](checkpoints/phase-7.md) distinguish local evidence from live release gates. Do not describe the API as publicly deployed until the hosted checks pass.
