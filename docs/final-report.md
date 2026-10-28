# Portfolio verification report

**Prepared:** 2026-10-28  
**Public deployment:** Deferred at the user's request; the deployment package remains local.

The [reviewer guide](reviewer-guide.md) walks through health, OpenAPI, authentication, and a replayable synthetic import. The [deployment guide](deployment.md) names the Render Blueprint, production environment settings, migration startup, smoke checks, and troubleshooting steps. The [architecture](architecture.md), [domain model](domain-model.md), and [financial rules](financial-rules.md) document the implementation and its boundaries.

## Verified locally

Phase 6's final local gate passed 69 PostgreSQL tests, locked dependency install, Ruff formatting and lint, mypy, Alembic drift check, a clean temporary-database migration, Docker build, and container health checks. Phase 7 adds a production-oriented Blueprint, startup migration in the image, TLS configuration enforcement, and a deploy smoke script. Its local gate passed 72 PostgreSQL tests and a clean container migration from an empty database; exact results are recorded in the [Phase 7 checkpoint](checkpoints/phase-7.md).

## Open release evidence

No live Neon Auth branch URL or database connection is configured in this workspace. A real sign-in, issued token, JWKS validation, and two-user test against Neon remain open. Render and GitHub integrations are not connected here, so no public service or remote CI result can be asserted. The user chose to keep deployment local for now. The repository does not contain a deployed URL or credentials. These gates must pass before marking the MVP publicly deployed.

## Known limits

The API is USD-only. Import file size and row limits are 2 MB and 5,000 by default. A source changing its external ID between pending and posted cannot reconcile automatically; rows without IDs receive advisory duplicate warnings. A free Render service can sleep after idle. No reporting percentages or read-only frontend are included.
