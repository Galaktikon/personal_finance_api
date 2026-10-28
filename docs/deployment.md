# Deployment and release checks

Phase 7 targets a Render Docker web service connected to one Neon PostgreSQL branch with Neon Auth enabled. The checked-in [Render Blueprint](../render.yaml) selects the free web-service plan, disables automatic deploys, requests both environment-specific URLs at creation, and uses `/health/ready` for health checks. This is a portfolio preview configuration. Render's [free-service documentation](https://render.com/docs/free) describes idle spin-down and other limits; its [deploy documentation](https://render.com/docs/deploys) says pre-deploy commands require a paid web service. The Docker image therefore runs `alembic upgrade head` before starting Uvicorn on every startup. Use one instance; do not start multiple instances against an unmigrated database at the same time.

## Environment and secrets

Create a Neon project or branch and enable Managed Better Auth for that branch. Copy its PostgreSQL connection string and Auth URL from the same branch. Keep the database URL private, change its scheme from `postgresql://` to `postgresql+psycopg://`, and retain `sslmode=require` (or a stronger TLS mode). Render's initial Blueprint setup prompts for `DATABASE_URL` and `NEON_AUTH_BASE_URL`; provide them there, not in source. Render exposes service environment variables as Docker build arguments, so the Dockerfile must never reference these secrets. The application requires `APP_ENV=production`, the matching HTTPS Auth URL, and a TLS database URL at startup. See [ADR-003](adr/ADR-003-neon-auth-and-authorization.md) for JWT and branch constraints and Neon's [JWT plugin guide](https://neon.com/docs/auth/guides/plugins/jwt) for the client token flow.

The remaining settings in `render.yaml` set a 2 MB file limit, 5,000-row import limit, and 3 MB total body limit. The Docker command disables Uvicorn access logs. Keep raw URL logging disabled at the Render edge or any added proxy, and apply an ingress request limit there as well. `GET /health/live` does not depend on PostgreSQL; `GET /health/ready` checks the application database.

## Deploy sequence

1. Push the reviewed branch and wait for the [GitHub Actions CI workflow](../.github/workflows/ci.yml) to pass. Its PostgreSQL service starts empty; the workflow installs locked dependencies, checks formatting/types, applies migrations, checks drift, and runs all tests.
2. In Render, create a Blueprint from this repository and select the reviewed branch containing `render.yaml`. Set the prompted Neon URLs. Confirm the plan before creating the service. The Blueprint disables automatic deploys so a later code push does not publish without a review.
3. Start the initial deploy or a manual deploy. The image builds from the lockfile; startup applies Alembic migrations before binding to Render's `PORT`. Wait for Render's `/health/ready` check to pass. Do not seed real financial data.
4. Run `uv run --all-groups python scripts/smoke_deployment.py --base-url https://<service>.onrender.com`. It checks liveness, readiness, OpenAPI, and anonymous rejection. Set `DEMO_BEARER_TOKEN` to a JWT obtained by signing in through the paired Neon Auth SDK and repeat the smoke check to exercise authenticated access. Never put the token in a command argument or source file.
5. Run the [synthetic demo loader](demo.md) with the same token and deployed base URL. Confirm the documented totals, import replay, and user-scoped account/transaction access. Repeat with a second test user to verify isolation before sharing the URL publicly.

For later releases, save the service's secret [Render deploy hook](https://render.com/docs/deploy-hooks) as the GitHub repository secret `RENDER_DEPLOY_HOOK_URL`. Manually run the CI workflow with `workflow_dispatch` on the reviewed commit. Its deploy job runs only after checks pass and asks Render to deploy that exact commit. The hook starts a deploy; inspect its progress in Render and run the smoke script again before sharing the new version.

## Troubleshooting

- **Build fails:** verify `uv.lock` is current and the Docker build passes locally (`docker build -t personal-finance-api:phase7 .`).
- **Startup fails:** verify both prompted URLs are set for the same Neon branch, the database scheme is `postgresql+psycopg://`, TLS mode is present, and the database user can run migrations. Read the fixed startup error and Alembic revision messages; keep connection strings out of logs and support tickets.
- **Liveness passes but readiness fails:** check Neon connectivity and whether migrations reached `head`; run `alembic check` in a controlled environment with that branch URL.
- **Authenticated route returns `401`:** obtain a fresh `authClient.token()` JWT from the paired branch and verify issuer, audience, and JWKS URL against [ADR-003](adr/ADR-003-neon-auth-and-authorization.md). A browser session cookie alone is not accepted.
- **Authenticated route returns `503`:** check the Auth URL and JWKS availability. An unconfigured Auth URL produces a generic service-unavailable response.
- **A free service responds slowly after idle:** Render documents spin-down and cold-start behavior for its free plan; use a paid plan if the portfolio needs continuous availability.

## Current evidence

The [Phase 6 checkpoint](checkpoints/phase-6.md) records local PostgreSQL, clean-migration, container, and synthetic-auth evidence. The [Phase 7 checkpoint](checkpoints/phase-7.md) distinguishes prepared deployment artifacts from live Render, Neon Auth, and remote CI checks. Do not describe the API as publicly deployed until the live checks above pass.
