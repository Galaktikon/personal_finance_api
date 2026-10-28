# API contracts

This is the HTTP surface. Phase 3 account, transaction, and category routes are implemented; remaining groups are planned. Every business route requires a verified Neon Auth Bearer JWT and derives ownership from its verified subject.

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

## Phase 3 account contract

`POST /api/v1/accounts` accepts `name` (1–120 characters), `type` (`checking`, `savings`, `cash`, `credit_card`, or `other`), and optional `currency` (`USD` only). The server assigns ownership and returns `201` with the account. `GET /api/v1/accounts` returns the current user's accounts ordered by name and ID; it accepts `limit` (1–100, default 50), `offset` (default 0), and optional `is_active`. `GET /api/v1/accounts/{id}` returns one owned account. `PATCH` accepts `name` and/or `is_active`; type and currency are immutable. `DELETE` archives the account (`is_active=false`) and returns `204`, preserving transaction history. Archived accounts cannot receive new transactions.

## Phase 3 transaction contract

`POST /api/v1/transactions` accepts an owned active `account_id`, calendar `transaction_date`, decimal-string `amount`, `description` (1–2000 characters), optional `merchant`, `kind` (`income`, `expense`, or `refund`), optional `status` (`pending` or `posted`, default posted), optional accessible `category_id`, and USD currency. Direct transfer creation is reserved for the later transfer workflow. The response is `201` with a decimal-string amount and server-derived owner. An explicit category is a manual override.

`GET /api/v1/transactions` returns owned transactions ordered by date descending and ID. It accepts `limit` (1–100, default 50), `offset`, `account_id`, `start_date` (inclusive), `end_date` (exclusive), `status`, `kind`, `category_id`, and `merchant`. `GET /{id}` returns one owned transaction. `PATCH /{id}` accepts account, date, amount, description, merchant, kind, status, and category changes; changes create a revision. Setting `category_id` manually clears a previous rule reference. `DELETE /{id}` voids the transaction and returns `204`; linked transfers must be unlinked before editing or voiding.

## Phase 3 category contract

`GET /api/v1/categories` returns system categories and the current user's categories with `limit` and `offset`. Responses identify system categories with `is_system`. `POST` accepts `name`, `kind` (`income` or `expense`), and optional accessible same-kind `parent_category_id`, then creates a user-owned category. `PATCH /{id}` changes name, parent, or active state for an owned category. System categories and another user's categories cannot be patched through the business API.

## Errors and authorization

Missing, invalid, expired, wrongly scoped, or incorrectly signed credentials return `401` with a generic detail and `WWW-Authenticate: Bearer`. An unavailable JWKS or unconfigured local Auth URL returns `503`. A nonexistent or other-user record returns `404`. Invalid input or violated financial constraints returns `422`; editing or voiding a linked transfer returns `409`. Request bodies reject caller-supplied `user_id`. Health routes do not require authentication.

## Contract work by phase

Phase 4 finalizes import/rule/transfer request contracts. Phase 5 finalizes analytics response schemas and zero-denominator behavior. OpenAPI examples are checked against actual responses in later phases.
