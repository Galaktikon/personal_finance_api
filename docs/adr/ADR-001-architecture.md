# ADR-001 — Modular monolith

**Status:** Accepted (project plan)  
**Decision date:** 2026-10-27

## Context

The MVP needs authenticated transaction management, imports, categorization, and analytics with consistent financial rules and ownership. A single deployable backend is sufficient.

## Decision

Use one FastAPI application and one PostgreSQL application database. Separate routers, services, domain logic, and repositories. Use SQLAlchemy for application data and Alembic for schema changes; Neon Auth manages identity.

## Consequences

Operations can share explicit database transactions, and deployment stays small. Module boundaries need discipline as features grow. Add distributed services only for a demonstrated need.
