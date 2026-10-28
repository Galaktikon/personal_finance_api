# ADR-004 — Duplicate detection and idempotency

**Status:** Accepted for Phase 4
**Decision date:** 2026-10-28

## Decision

An import request identifies an owned account, a nonempty source identifier, and a CSV or JSON file. An external transaction ID is unique within `(user, account, source identifier)` and is the only automatic cross-import duplicate key. Repeating the same external ID returns a duplicate row result without inserting a transaction. An existing pending transaction with that ID may be reconciled to posted if the incoming kind matches; its row result is `updated`. A posted transaction is never regressed to pending.

For rows without an external ID, compute a SHA-256 fingerprint from the scoped account/source, date, normalized amount, kind, status, normalized description, and normalized merchant. The fingerprint is advisory: matching rows receive a `possible_duplicate` warning but are still created. This avoids silently dropping legitimate same-day repeat purchases. An explicit file `category_id` is a manual assignment; an existing manual category survives reconciliation and reimport.

Commit requires an `Idempotency-Key` header, unique per user. Its digest covers the raw file bytes, account, source identifier, and format. Replaying the same key and digest returns the original job and row results; reusing it for different content returns `409`. Preview performs no writes. Commit parses and validates again. Per-row input failures are recorded as sanitized `failed` results while valid rows proceed. The job, transactions, updates, and row results commit atomically; an unexpected persistence error rolls back the whole job. No raw rows or sensitive descriptions are stored in import errors or logs.

## Consequences and limits

Fingerprint collisions or repeated identical purchases require user review; they are never automatically discarded. External IDs must be stable within the stated scope. A source that changes IDs between pending and posted cannot be reconciled automatically; the user must correct it manually. Import limits are configured in bytes and rows. Rule changes do not retroactively overwrite manual categories.
