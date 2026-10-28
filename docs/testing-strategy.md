# Testing strategy

Use pytest and HTTPX. PostgreSQL-backed integration tests are required for database behavior; SQLite alone cannot validate PostgreSQL constraints or migrations.

| Layer | Evidence |
|---|---|
| Unit | Decimal precision, signs, dates, analytics formulas, categorization order, normalization, fingerprints |
| Integration | SQLAlchemy constraints, migrations from empty database, import rollback/idempotency, transfer integrity, analytics queries |
| API | Auth, validation, pagination, filters, errors, schemas, all route ownership checks |
| Security | Two-user isolation across all resources; forged IDs; missing, invalid, expired, or mis-scoped credentials |
| Financial reconciliation | Independently calculated synthetic totals for transfers, payments, refunds, statuses, month boundaries, and empty periods |

CI will install locked dependencies and run formatting/linting, configured type checks, unit and PostgreSQL integration tests, migration validation, API/security tests, and practical repository hygiene checks. Each phase's acceptance criteria in the [development plan](project-plan.md#12-development-phases) must pass before the next phase.

Phase 0 is documentation only. Its checks are artifact presence, links, and consistency; there are no application tests yet. Record actual commands and results in each phase checkpoint. Never claim unrun tests passed.
