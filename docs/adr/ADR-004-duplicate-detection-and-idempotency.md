# ADR-004 — Duplicate detection and idempotency

**Status:** Proposed; policy details remain open  
**Decision date:** 2026-10-27

## Planned decision

Use a stable source transaction ID when present and a deterministic fingerprint fallback. Bind import idempotency keys to content; a reused key with different content is a conflict. Commit revalidates after preview. Preserve manual category corrections on reimport.

## Before Phase 4 implementation

Specify fingerprint fields and scope, collision/manual correction behavior, pending-to-posted reconciliation, repeated identical purchases, partial-success boundaries, and rollback semantics. Test the chosen policy with synthetic duplicates and legitimate lookalikes. Date, amount, and merchant alone are insufficient proof of duplication.
