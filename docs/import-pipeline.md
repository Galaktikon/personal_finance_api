# Import pipeline

The MVP accepts documented CSV columns and JSON records, using synthetic fixtures for tests and demos. The precise input schemas and limits are finalized in Phase 4. See the [pipeline diagram](diagrams/import-pipeline.mmd).

## Processing

1. Check file size, format, and row count.
2. Parse and normalize dates, amounts, descriptions, and merchants.
3. Validate required fields, USD, precision, transaction kind, and account ownership.
4. Identify duplicates by stable external transaction ID where available, then a documented fingerprint fallback.
5. Apply categorization precedence: manual correction, user rule, system rule, uncategorized.
6. Return a preview or commit transactions and row results.

Preview does not mutate persistent business data. Commit revalidates all input and duplicate checks. Unexpected persistence failure rolls back the affected atomic unit. Report row numbers and sanitized error codes, never raw payloads in logs.

## Decisions to close in Phase 4

[ADR-004](adr/ADR-004-duplicate-detection-and-idempotency.md) tracks fingerprint fields, pending-to-posted reconciliation, idempotency scope, and partial-success transaction boundaries. Identical date, amount, and merchant alone cannot prove a duplicate. An idempotency key bound to different content must conflict. Manual category corrections must survive reimport.
