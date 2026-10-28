# ADR-006 — Ownership and schema integrity

**Status:** Accepted for Phase 2  
**Decision date:** 2026-10-28

## Context

The API will support system categories and user-owned categories, while every account, transaction, import, transfer, and revision must stay within one user's data. PostgreSQL foreign keys alone cannot express access to either a system category or a same-user category when the category owner may be null.

## Decision

Use UUID primary keys and explicit owner IDs. Use composite foreign keys where both records have an owner. Represent system categories and rules with `user_id IS NULL`. Use PostgreSQL triggers to validate category parent, rule category, and transaction category/rule scope. Enforce valid transfer pairs at link creation and prevent silent mutation of linked financial fields.

The API layer remains responsible for authentication, user-scoped queries, and limiting who can create or change system-owned records. Database constraints are defense in depth.

## Consequences

Migrations include trigger functions as well as tables. PostgreSQL-backed tests are required; SQLite cannot verify the same behavior. Ownership of categories and rules is immutable after creation. Unmatching a transfer must remove or otherwise safely transition the link before editing either transaction; exact lifecycle semantics are finalized in Phase 4.
