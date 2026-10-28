# Personal Finance Analytics API

FastAPI foundation for a personal finance analytics backend. The MVP manages accounts and transactions, imports synthetic CSV/JSON data, and reports spending and cash flow. It uses PostgreSQL, SQLAlchemy, Alembic, and Neon Auth JWT verification.

**Status:** Phase 7 local deployment package verified. Public deployment is deferred at the user's request; live Neon Auth and remote CI remain open.

## Local setup

Install Python 3.11, [uv](https://docs.astral.sh/uv/), and Docker Desktop with its engine running. From the repository root:

```powershell
Copy-Item .env.example .env
uv sync --locked --all-groups
docker compose up -d db
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --no-access-log
```

The example database user and password are for local Docker Compose only. Set `DATABASE_URL` to a Neon PostgreSQL URL using the `postgresql+psycopg://` scheme and TLS settings for a remote environment. Never commit `.env`.

For authenticated routes, set `NEON_AUTH_BASE_URL` in `.env` to the Managed Better Auth URL for the **same Neon branch** as `DATABASE_URL`. Production startup requires it. Without a Neon branch, health routes and synthetic tests still work, while authenticated routes return `503` when a Bearer token is presented. The API accepts the JWT returned by the Neon SDK's `authClient.token()` method:

```javascript
const { data, error } = await authClient.token();
if (error) throw error;
const response = await fetch("http://127.0.0.1:8000/api/v1/accounts", {
  headers: { Authorization: `Bearer ${data.token}` },
});
```

See the [Neon JWT guide](https://neon.com/docs/auth/guides/plugins/jwt) for client setup and cross-origin cookie requirements. Never put a real token in source files or shell history.

Open `http://127.0.0.1:8000/docs` for OpenAPI, `GET /health/live` for process liveness, and `GET /health/ready` for database readiness. Liveness returns `200` independently of PostgreSQL; readiness returns `503` when the database cannot be reached, without exposing connection details.

## Checks

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest -q
```

Set `TEST_DATABASE_URL` to a separate, already migrated PostgreSQL database URL to run the integration tests. CI starts a PostgreSQL service, migrates it from empty, checks schema drift, and runs the full suite. Local tests can use the Docker Compose database after `uv run alembic upgrade head` when it contains no personal data.

Phase 3 tests issue synthetic Ed25519 JWTs and supply a fake JWKS. They do not require a Neon account. A live Neon Auth smoke test remains a deployment gate.

Phase 4 tests use synthetic transactions and the same synthetic authentication. The [import guide](docs/import-pipeline.md) defines CSV/JSON fields, limits, preview and commit behavior, and duplicate policy. Import commits require `Idempotency-Key`; previews do not. The API docs at `/docs` show the multipart upload fields and the rule and transfer routes.

Phase 5 adds summary, monthly trend, category, and merchant analytics at `/api/v1/analytics/*`. The [API contract](docs/api-contracts.md#phase-5-analytics-contract) defines filters, response fields, and empty-period behavior. The synthetic tests reconcile the published totals against separately calculated amounts.

Phase 6 adds sanitized request errors and logs, a 3 MB overall request body limit, rollback checks, and a [repeatable synthetic demo](docs/demo.md). `REQUEST_MAX_BYTES` must exceed `IMPORT_MAX_BYTES` for multipart overhead. The local server command disables raw access logs because URLs can contain sensitive query values.

## Reviewer and deployment walkthrough

Start with the [reviewer guide](docs/reviewer-guide.md) for the architecture, API paths, and synthetic expected totals. Run the local synthetic demonstration without Neon using its listed PostgreSQL-backed test commands. To host the API, follow the [Render and Neon deployment guide](docs/deployment.md) and review the [Blueprint](render.yaml) before creating a service. The Docker image applies Alembic migrations before serving requests. After deployment, run `uv run --all-groups python scripts/smoke_deployment.py --base-url https://<service>.onrender.com`, then run the [demo loader](docs/demo.md) with a JWT from the paired Neon Auth branch. The [verification report](docs/final-report.md) separates local evidence from live checks.

## Project docs

- [Development plan](docs/project-plan.md) — complete scope, phases, acceptance criteria, and definition of done.
- [Documentation index](docs/README.md) — requirements, design, ADRs, diagrams, and open decisions.
- [Roadmap](docs/roadmap.md) — phase checkpoints.
- [Phase 1 checkpoint](docs/checkpoints/phase-1.md) — delivered foundation and verification results.
- [Phase 2 checkpoint](docs/checkpoints/phase-2.md) — domain schema and financial rule verification.
- [Phase 3 checkpoint](docs/checkpoints/phase-3.md) — authentication and user-scoped CRUD verification.
- [Phase 4 checkpoint](docs/checkpoints/phase-4.md) — import, categorization, and transfer verification.
- [Phase 5 checkpoint](docs/checkpoints/phase-5.md) — analytics formulas and PostgreSQL verification.
- [Phase 6 checkpoint](docs/checkpoints/phase-6.md) — hardening and end-to-end verification.
- [Phase 7 checkpoint](docs/checkpoints/phase-7.md) — deployment package and live release gates.

The documentation establishes intended future behavior. Use synthetic financial data only.

