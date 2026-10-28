# Architecture

The API is a modular monolith: one FastAPI application and one PostgreSQL application database. Neon Auth manages identity. SQLAlchemy handles application persistence, and Alembic owns schema changes. See the [system diagram](diagrams/system-architecture.mmd).

## Boundaries

- API routers validate HTTP input and format responses.
- Authentication verifies the credential and resolves an internal `UserProfile`.
- Services coordinate operations and transaction boundaries.
- Domain modules implement money, transfer, categorization, and analytics rules.
- Repositories query only records available to the resolved user.
- PostgreSQL constraints protect relationships and ownership consistency.

## Request path

The client presents a supported Neon Auth credential. FastAPI verifies it using the integration chosen in [ADR-003](adr/ADR-003-neon-auth-and-authorization.md), maps its stable subject to an internal profile, and invokes a user-scoped service. The service uses repositories and commits within a defined transaction boundary. The response is validated before return.

The Phase 3 verifier uses Neon's documented JWT plugin flow: a client sends `authClient.token()` as a Bearer JWT, and FastAPI checks it against the branch JWKS before resolving `UserProfile`. See [ADR-003](adr/ADR-003-neon-auth-and-authorization.md) and the [authentication diagram](diagrams/authentication-flow.mmd). A live Neon branch smoke test remains before deployment.

## Data and deployment

Local development uses Docker Compose PostgreSQL. The [deployment guide](deployment.md) selects a Render Docker web service and a paired Neon PostgreSQL and Neon Auth branch for the portfolio preview. Database and Auth environments must be separated across local, test, and production. The Docker image applies Alembic migrations before serving requests; the Render health check uses `/health/ready`.

## Repository layout

The `app/`, `alembic/`, `tests/`, `scripts/`, and `sample_data/` layout follows the [development plan](project-plan.md#4-repository-structure).
