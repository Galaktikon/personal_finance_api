# Requirements

## MVP outcomes

An authenticated user can manage their own accounts, transactions, categories, and categorization rules; preview and commit CSV/JSON imports; link internal transfers; and request accurate summary, monthly, category, and merchant analytics. Every user-owned operation enforces isolation. The API supports reproducible synthetic demos without real banking connections.

## Functional requirements

1. Manage accounts and transactions with validation, pagination, filters, and documented archival/voiding behavior.
2. Import CSV and JSON with validation, normalization, row results, duplicate handling, and import history. Preview has no persistent business side effects.
3. Apply deterministic categorization with manual corrections taking precedence over user rules and system rules.
4. Represent transfers as linked, opposite signed transactions and exclude them from income and spending.
5. Report financial analytics according to [financial rules](financial-rules.md), with inclusive start and exclusive end dates.
6. Expose liveness and readiness endpoints and OpenAPI documentation.

## Quality and security requirements

- Use verified Neon Auth identity to derive the current internal user; never trust a caller supplied owner ID.
- Use `Decimal` and PostgreSQL `NUMERIC(19,2)` for money; support USD only in the MVP.
- Test domain rules, migrations, API behavior, PostgreSQL constraints, and cross-user access.
- Keep credentials and raw financial content out of logs and public error responses.
- Provide CI, migrations, documented setup, synthetic fixtures, and a reproducible deployment.

## Exclusions

Bank aggregation, bank credential storage, payments, investments, tax advice, a full frontend, multi-currency conversion, AI categorization, and distributed infrastructure are outside the MVP.

## Traceability

The complete endpoint list, entity fields, acceptance criteria, and definition of done are in the [development plan](project-plan.md). Each phase's checkpoint in the [roadmap](roadmap.md) is the delivery gate.
