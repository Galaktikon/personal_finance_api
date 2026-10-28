# Domain model

See the [entity relationship diagram](diagrams/entity-relationships.mmd) and the full field inventory in the [development plan](project-plan.md#5-data-model).

| Entity | Role | Ownership |
|---|---|---|
| `UserProfile` | Maps a verified auth subject to an internal user | Unique `auth_subject_id` |
| `Account` | Checking, savings, cash, credit card, or other account | One user |
| `Transaction` | Dated, signed financial event with explicit kind and status | One user and one same-user account |
| `Category` | System or user category, optionally nested | System accessible or one user |
| `CategorizationRule` | Deterministic category assignment | System or one user |
| `ImportJob` and `ImportRecord` | Import lifecycle and per-row outcomes | Job belongs to one user |
| `TransferLink` | Links both sides of an internal transfer | One user; both transactions same user |
| `TransactionRevision` | Optional audit of manual corrections | One user and same-user transaction |

## Integrity requirements

The application must not accept an owner ID as proof of access. Repositories scope user-owned queries to the authenticated internal profile. Database constraints should enforce same-user account, transaction, category, rule, and transfer relationships where feasible; composite foreign keys are candidates. Every schema change uses Alembic.

Transactions use a calendar `transaction_date`; source timestamps are retained separately only when a supported format requires them. Money is stored in `NUMERIC(19,2)` and the MVP currency is USD. See [financial rules](financial-rules.md).

## Phase 2 decisions

Define category system ownership, transaction deletion versus voiding, account archival, transfer reversal, and whether `TransactionRevision` is in the initial migration before finalizing models. Record any material choice in an ADR.
