# API contracts

This is the planned HTTP surface. Request/response schemas, pagination defaults, error codes, and examples become normative as each endpoint is implemented. Every business route requires verified authentication and derives ownership from the credential.

| Group | Planned routes |
|---|---|
| Health | `GET /health/live`, `GET /health/ready` |
| Accounts | `GET/POST /api/v1/accounts`, `GET/PATCH/DELETE /api/v1/accounts/{id}` |
| Transactions | `GET/POST /api/v1/transactions`, `GET/PATCH/DELETE /api/v1/transactions/{id}` |
| Categories | `GET/POST /api/v1/categories`, `PATCH /api/v1/categories/{id}` |
| Rules | `GET/POST /api/v1/categorization-rules`, `PATCH/DELETE /api/v1/categorization-rules/{id}` |
| Imports | `POST /api/v1/imports/preview`, `POST/GET /api/v1/imports`, `GET /api/v1/imports/{id}` |
| Transfers | `POST /api/v1/transfers/match`, `DELETE /api/v1/transfers/{id}` |
| Analytics | `GET /api/v1/analytics/summary`, `/monthly-trends`, `/categories`, `/merchants` |

## Shared contract rules

- Money appears as decimal strings; USD is the only supported currency.
- Date filters use an inclusive start and exclusive end.
- Default analytics include posted transactions only and exclude internal transfers.
- List endpoints paginate and document supported filters and limits.
- Missing or invalid credentials return a standard unauthenticated response. Cross-user resources must not disclose another user's data.
- Liveness does not require the database; readiness checks required dependencies without exposing connection details.

## Contract work by phase

Phase 1 finalizes health schemas. Phase 3 finalizes authenticated CRUD and error formats. Phase 4 finalizes import/rule/transfer request contracts. Phase 5 finalizes analytics response schemas and zero-denominator behavior. OpenAPI examples are checked against actual responses in later phases.
