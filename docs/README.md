# Documentation index

The [project development plan](project-plan.md) is the full scope and phased delivery contract. This index links the working design documents created in Phase 0. Update them as implementation decisions are verified.

| Topic | Document |
|---|---|
| MVP requirements and boundaries | [Requirements](requirements.md) |
| Components and request flow | [Architecture](architecture.md) |
| Entities and ownership constraints | [Domain model](domain-model.md) |
| Money, transactions, dates, analytics | [Financial rules](financial-rules.md) |
| Planned HTTP surface | [API contracts](api-contracts.md) |
| CSV/JSON processing | [Import pipeline](import-pipeline.md) |
| Authentication and data isolation | [Security](security.md) |
| Verification approach | [Testing strategy](testing-strategy.md) |
| Environments and release gate | [Deployment](deployment.md) |
| Phase checkpoints | [Roadmap](roadmap.md) |

## Decision records

- [ADR-001: modular monolith](adr/ADR-001-architecture.md)
- [ADR-002: money and transaction semantics](adr/ADR-002-money-and-transaction-semantics.md)
- [ADR-003: Neon Auth and authorization](adr/ADR-003-neon-auth-and-authorization.md)
- [ADR-004: duplicates and idempotency](adr/ADR-004-duplicate-detection-and-idempotency.md)
- [ADR-005: analytics definitions](adr/ADR-005-analytics-definitions.md)

## Diagram sources

- [System architecture](diagrams/system-architecture.mmd)
- [Entity relationships](diagrams/entity-relationships.mmd)
- [Import pipeline](diagrams/import-pipeline.mmd)
- [Authentication flow](diagrams/authentication-flow.mmd)

ADR-003 and ADR-004 are proposed. Their unresolved details must be verified before the related implementation phases.
