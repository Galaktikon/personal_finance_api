# Import pipeline

Phase 4 accepts UTF-8 CSV and JSON uploads for an owned, active account. Each upload names a stable `source_identifier` (such as a bank or statement source). The server normalizes that name by collapsing whitespace and ignoring case. See the [pipeline diagram](diagrams/import-pipeline.mmd) and [ADR-004](adr/ADR-004-duplicate-detection-and-idempotency.md).

## File schema

CSV has a header row. Required columns are `transaction_date`, `amount`, `description`, and `kind`. Optional columns are `status`, `currency`, `merchant`, `external_transaction_id`, and `category_id`. JSON is an array of objects with the same keys. Unknown keys or columns are rejected; a malformed CSV header or JSON document rejects the whole upload. A malformed transaction row is reported as `failed` while other valid rows can commit.

| Field | Accepted value |
|---|---|
| `transaction_date` | ISO calendar date, `YYYY-MM-DD` |
| `amount` | Signed decimal string with at most two fractional digits; negative expense, positive income/refund |
| `description` | Nonblank text, at most 2,000 characters |
| `kind` | `expense`, `income`, or `refund` |
| `status` | `pending` or `posted`; defaults to `posted` |
| `currency` | `USD`; defaults to `USD` |
| `merchant` | Optional text, at most 255 characters |
| `external_transaction_id` | Optional stable source ID, at most 255 characters |
| `category_id` | Optional accessible, active category of the matching kind; treated as a manual override |

Descriptions, merchants, and external IDs have surrounding and repeated whitespace normalized. Amounts are stored as exact two-decimal values. Uploads are limited to 2 MB and 5,000 rows by default (`IMPORT_MAX_BYTES`, `IMPORT_MAX_ROWS`). The file extension and MIME type must match the declared `source_format` (`csv` or `json`).

Example JSON:

```json
[
  {"transaction_date":"2024-02-29","amount":"-12.50","description":"Market purchase","kind":"expense","merchant":"Market","external_transaction_id":"example-1"}
]
```

## Preview, commit, and history

`POST /api/v1/imports/preview` accepts multipart form fields `account_id`, `source_identifier`, `source_format`, and `file`. It returns row numbers, `created`/`updated`/`duplicate`/`failed` classifications, counts, and sanitized error or warning codes. Preview makes no persistent changes. Its classification reflects existing committed transactions; commit repeats validation and duplicate checks against current database state.

`POST /api/v1/imports` accepts the same form fields and requires `Idempotency-Key`. It commits valid rows, records invalid rows, and returns a completed import job with row results (`201`). Replaying the same key, file bytes, account, source, and format returns that job (`200`); using the same key with different content returns `409`. `GET /api/v1/imports` paginates the user's jobs; `GET /api/v1/imports/{id}` returns a job and its row results. Errors do not contain uploaded descriptions or raw rows.

An external transaction ID identifies a transaction within one user, account, and source. A repeated ID is `duplicate`, except a pending row may reconcile to a posted row of the same kind (`updated`). Reconciliation preserves an existing manual category. An existing posted transaction is never moved back to pending. Linked transfers cannot be reconciled. Rows without an ID are always created; matching fingerprints receive `possible_duplicate` for review because two identical purchases can be legitimate.

For each new row, categorization applies an explicit file category first, then active user rules, active system rules, then uncategorized. Within each rule scope, lower priority wins and rule ID breaks ties. Rules match normalized merchant or description with `contains` or `equals`. Rule changes affect future imports; existing manual categories remain intact. A transfer match stores both transactions' prior classifications; unmatching restores them and records revisions.

Row input failures are partial success. The job, all transaction changes, and all row results share one database transaction, so an unexpected persistence failure rolls back the complete job.
