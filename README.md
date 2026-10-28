# Personal Finance Analytics API

FastAPI foundation for a personal finance analytics backend. The MVP will manage accounts and transactions, import synthetic CSV/JSON data, and report spending and cash flow. It uses PostgreSQL, SQLAlchemy, and Alembic. Neon Auth integration is a Phase 3 gate.

**Status:** Phase 1 foundation. Health endpoints are implemented; financial models and business endpoints begin in later phases.

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

Open `http://127.0.0.1:8000/docs` for OpenAPI, `GET /health/live` for process liveness, and `GET /health/ready` for database readiness. Liveness returns `200` independently of PostgreSQL; readiness returns `503` when the database cannot be reached, without exposing connection details.

## Checks

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest -q
```

Set `TEST_DATABASE_URL` to a separate PostgreSQL database URL to run the integration connection test. CI starts a PostgreSQL service, migrates it from empty, and runs the full suite. The Phase 1 migration establishes an empty baseline; domain tables arrive in Phase 2.

## Project docs

- [Development plan](docs/project-plan.md) — complete scope, phases, acceptance criteria, and definition of done.
- [Documentation index](docs/README.md) — requirements, design, ADRs, diagrams, and open decisions.
- [Roadmap](docs/roadmap.md) — phase checkpoints.
- [Phase 1 checkpoint](docs/checkpoints/phase-1.md) — delivered foundation and verification results.

The documentation establishes intended future behavior. Use synthetic financial data only.

