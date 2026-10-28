# API contracts

This is the HTTP surface. Phase 3–5 routes are implemented. Every business route requires a verified Neon Auth Bearer JWT and derives ownership from its verified subject.

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

## Phase 4 import, rule, and transfer contract

Import preview and commit accept multipart fields `account_id` (owned active UUID), `source_identifier` (1–120 characters), `source_format` (`csv` or `json`), and `file`. Commit also requires `Idempotency-Key` (1–128 characters). Preview returns row classifications and counts without persistence. Commit returns `201` with a completed job and row results; an exact key replay returns `200`, while conflicting content returns `409`. Invalid document structure or file type returns `422`; an oversized upload returns `413`. Jobs list with `limit` (1–100, default 50) and `offset`; job detail includes sanitized row outcomes. See the [file schema and duplicate policy](import-pipeline.md).

Rules list with `limit` and `offset`, including visible system rules. `POST /api/v1/categorization-rules` accepts `name`, `priority` (0–10000, default 100), `condition_type` (`contains` or `equals`), `condition_value`, an accessible active `category_id`, and optional `is_active`. `PATCH /{id}` updates those fields on a user-owned rule. `DELETE /{id}` deactivates a user-owned rule (`204`); system and other-user rules cannot be modified.

`POST /api/v1/transfers/match` accepts `source_transaction_id` and `destination_transaction_id`. Both must be owned, posted, unlinked, in distinct accounts, and have equal opposite amounts; the source is an expense and destination an income or refund. It returns `201` with the link, converts the pair to transfer kinds, and records revisions. `DELETE /api/v1/transfers/{id}` restores prior kinds and categories and returns `204`. Another user's link returns `404`; a linked transaction cannot be edited until unmatched.

## Phase 5 analytics contract

All four `GET /api/v1/analytics/*` endpoints accept optional `account_id` (owned account, including archived accounts), `start_date` (inclusive), and `end_date` (exclusive). If both dates are supplied, start must precede end. An inaccessible account returns `404`; an invalid range returns `422`. Only posted income, expense, and refund transactions are included. Pending, voided, and transfer transactions are excluded. USD amounts are exact decimal strings with two fractional digits.

`GET /summary` returns `currency`, the applied date and account filters, `transaction_count`, `gross_income`, `gross_expenses`, `refunds`, `net_spending`, and `net_cash_flow`. Gross expenses are positive. Net spending is expenses minus refunds; net cash flow is income minus expenses plus refunds. An empty selection has count zero and all amounts `"0.00"`.

`GET /monthly-trends` returns one row per month with qualifying activity, ordered by month ascending. Each row has `month` (`YYYY-MM`), count, and the five summary amounts. Months with no qualifying rows are omitted. `GET /categories` and `GET /merchants` return expense/refund breakdowns with count, gross expenses, refunds, and net spending. Category rows identify `category_id` and `category_name`; uncategorized transactions use null values. Merchant rows use a case-insensitive normalized merchant name; missing merchant is null. Refund-only groups may have negative net spending. These three list endpoints accept `limit` (1–100, default 50) and `offset` (default 0); breakdowns sort by net spending descending, then name and ID where applicable. An empty selection returns `[]`.

No percentages are published. A percentage of net spending is misleading when refunds make the denominator zero or negative; a future percentage metric needs its own explicit denominator and zero-denominator convention.

## Errors and authorization

Missing, invalid, expired, wrongly scoped, or incorrectly signed credentials return `401` with a generic detail and `WWW-Authenticate: Bearer`. An unavailable JWKS or unconfigured local Auth URL returns `503`. A nonexistent or other-user record returns `404`. Invalid input or violated financial constraints returns `422`; editing or voiding a linked transfer returns `409`. Request bodies reject caller-supplied `user_id`. Health routes do not require authentication.

Validation `422` responses contain `detail` entries with error `type` only, without submitted values or user-supplied field names. Unexpected failures return `500` with a generic detail. A body above `REQUEST_MAX_BYTES` returns `413`; the default limit is 3 MB and must exceed `IMPORT_MAX_BYTES` to accommodate multipart overhead.

## Contract work by phase

Phase 6 checks OpenAPI examples against actual responses and hardens end-to-end behavior.
