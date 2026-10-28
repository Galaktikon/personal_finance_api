# Personal Finance Analytics API

FastAPI foundation for a personal finance analytics backend. The MVP will manage accounts and transactions, import synthetic CSV/JSON data, and report spending and cash flow. It uses PostgreSQL, SQLAlchemy, and Alembic. Neon Auth integration is a Phase 3 gate.

**Status:** Phase 3 authenticated account, transaction, and category CRUD. Imports, categorization rules, transfers, and analytics remain in later phases.

## Local setup

Install Python 3.11, [uv](https://docs.astral.sh/uv/), and Docker Desktop with its engine running. From the repository root:

```powershell
Copy-Item .env.example .env
uv sync --locked --all-groups
docker compose up -d db
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
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

## Project docs

- [Development plan](docs/project-plan.md) — complete scope, phases, acceptance criteria, and definition of done.
- [Documentation index](docs/README.md) — requirements, design, ADRs, diagrams, and open decisions.
- [Roadmap](docs/roadmap.md) — phase checkpoints.
- [Phase 1 checkpoint](docs/checkpoints/phase-1.md) — delivered foundation and verification results.
- [Phase 2 checkpoint](docs/checkpoints/phase-2.md) — domain schema and financial rule verification.
- [Phase 3 checkpoint](docs/checkpoints/phase-3.md) — authentication and user-scoped CRUD verification.

The documentation establishes intended future behavior. Use synthetic financial data only.

