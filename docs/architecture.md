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

The credential type and verification mechanism are **unresolved** until official Neon documentation is checked in Phase 3. The [authentication diagram](diagrams/authentication-flow.mmd) depicts the intended trust boundary, not a verified protocol.

## Data and deployment

Local development uses Docker Compose PostgreSQL. Deployment is intended to use Neon PostgreSQL and managed Python hosting. The hosting provider and current free-tier constraints are open choices. Database and auth environments must be separated across local, test, and production.

## Repository layout

The planned `app/`, `alembic/`, `tests/`, `scripts/`, and `sample_data/` structure is in the [development plan](project-plan.md#4-repository-structure). Phase 1 creates only the foundation needed to run and test the API.
