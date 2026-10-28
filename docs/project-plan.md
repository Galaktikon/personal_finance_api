# Personal Finance Analytics API — Project Development Plan

## 1. Project Overview

### Project Name
Personal Finance Analytics API

### Purpose
Build a production-minded backend API that demonstrates enterprise-quality backend engineering, financial data modeling, data processing, secure API development, analytical calculations, testing, and deployment.

This project is intended to support applications for Software Engineer, Backend Engineer, and FinTech Engineer roles. It complements a loan-focused FinTech project by concentrating on personal transaction data, spending analytics, and financial reporting rather than loan management.

### Core Objectives

The application must support:

- User authentication and strict per-user data isolation.
- Financial account and transaction management.
- CSV and JSON transaction imports.
- Data validation, normalization, duplicate detection, and import history.
- Configurable transaction categorization rules.
- Manual categorization overrides.
- Internal account transfers and credit card payment handling.
- Accurate income, spending, cash-flow, merchant, and monthly analytics.
- Consistent monetary precision and date-range behavior.
- Automated unit, integration, API, and security tests.
- CI/CD, database migrations, synthetic demo data, API documentation, and deployment.

### Non-Goals for the MVP

- Connecting to real banks or financial aggregators.
- Storing bank credentials.
- Initiating payments or moving money.
- Investment portfolio management.
- Tax filing or financial advice.
- Microservices, Kafka, Redis, or distributed processing.
- A full-featured consumer frontend.
- Multi-currency conversion.
- AI-based transaction categorization.

The MVP should remain small enough to finish while demonstrating realistic production engineering.

---

## 2. Technology Stack

| Area | Technology |
|---|---|
| Language | Python |
| API framework | FastAPI |
| Authentication | Neon Auth / Managed Better Auth |
| Database | Neon PostgreSQL |
| ORM | SQLAlchemy 2.x |
| Database migrations | Alembic |
| Validation and settings | Pydantic, pydantic-settings |
| Monetary calculations | Python `Decimal`, PostgreSQL `NUMERIC` |
| Testing | pytest, HTTPX |
| Database integration tests | PostgreSQL-compatible test database |
| Dependency management | uv |
| Local development | Docker Compose |
| CI | GitHub Actions |
| API documentation | OpenAPI / Swagger UI |
| Deployment | Low-cost managed Python hosting |
| Sample data | Synthetic CSV and JSON fixtures |

Use free tiers where practical, but verify current quotas, deployment sleep behavior, authentication configuration requirements, and email-delivery limitations before committing to a production setup.

---

## 3. Architecture

### Architectural Style

Use a **modular monolith**: one FastAPI application, one PostgreSQL database, and clear separation between API endpoints, domain rules, application services, and persistence.

Do not introduce microservices unless a demonstrated requirement justifies them.

### System Components

1. **Neon Auth / Managed Better Auth**
   - User registration and sign-in.
   - Session management and supported authentication flows.
   - Authentication configuration and identity records.
   - Branch-specific authentication environments.
   - User identity used by the application for ownership and authorization.

2. **FastAPI application**
   - Authenticated HTTP API.
   - Request and response validation.
   - Authentication integration.
   - Per-user authorization.
   - Transaction management and business rules.
   - Imports, categorization, and analytics.
   - Consistent errors and API documentation.

3. **Neon PostgreSQL**
   - Application data and relational constraints.
   - Accounts, transactions, categories, rules, imports, and transfer links.
   - Database transactions and analytical queries.
   - Optional row-level security as an additional protection layer.

4. **Automated quality checks**
   - Unit and integration tests.
   - API and authorization tests.
   - Financial invariant tests.
   - Migration checks.
   - GitHub Actions CI.

### Request Flow

A typical authenticated API request follows this flow:

1. The user authenticates through Neon Auth.
2. The client sends the supported session or access credential with its request.
3. FastAPI validates the credential using the documented, supported Neon Auth integration.
4. The application derives the authenticated subject from verified identity information.
5. The application resolves the internal user profile associated with that subject.
6. The API service executes a user-scoped operation.
7. PostgreSQL constraints and, where configured, row-level security provide additional safeguards.
8. FastAPI returns a validated response.

### Authentication Integration Gate

Before implementing authenticated endpoints, confirm the current Neon Auth integration requirements for a Python backend.

Verify:

- The authentication flow and credential type available to the client.
- How FastAPI can validate the credential, including signature, issuer, audience, expiry, and key rotation where applicable.
- Whether the intended session or JWT flow is supported for this architecture.
- How the authenticated subject is obtained reliably.
- How local development, tests, and deployment configure separate auth environments.
- Which user identifiers and claims are stable and suitable for ownership mapping.

Use Neon’s official documentation as the source of truth:

- https://neon.com/docs/auth/overview
- https://neon.com/docs/auth/authentication-flow

Do not decode a token and trust its claims without verifying it. Do not assume that a token intended for Neon’s Data API is automatically valid for a custom FastAPI backend.

If a supported direct verification flow is not available for the selected configuration, evaluate a documented server-side session-validation approach before writing the security dependency. Do not silently substitute a different authentication provider.

### Database Access

Use SQLAlchemy for application data access and Alembic for schema migrations. Connect using the appropriate Neon PostgreSQL connection string and secure connection settings.

Do not mix multiple competing database access patterns in the MVP. Neon Auth manages identity; SQLAlchemy manages application persistence.

---

## 4. Repository Structure

```text
personal-finance-analytics-api/
├── app/
│   ├── main.py
│   ├── api/
│   │   └── v1/
│   │       ├── accounts.py
│   │       ├── transactions.py
│   │       ├── categories.py
│   │       ├── categorization_rules.py
│   │       ├── imports.py
│   │       ├── transfers.py
│   │       └── analytics.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── errors.py
│   │   └── logging.py
│   ├── domain/
│   │   ├── money.py
│   │   ├── transactions.py
│   │   ├── transfers.py
│   │   ├── categorization.py
│   │   └── analytics.py
│   ├── schemas/
│   ├── models/
│   ├── repositories/
│   ├── services/
│   │   ├── import_service.py
│   │   ├── categorization_service.py
│   │   └── analytics_service.py
│   └── db/
│       ├── session.py
│       └── base.py
├── alembic/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   └── fixtures/
├── scripts/
│   └── seed_demo_data.py
├── sample_data/
├── docs/
├── .github/
│   └── workflows/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
├── alembic.ini
├── .env.example
├── .gitignore
└── README.md
```

Adjust the structure when implementation provides a good reason, but preserve the separation of responsibilities.

---

## 5. Data Model

### UserProfile

An application-owned profile associated with the authenticated identity.

Fields:

- `id`
- `auth_subject_id`
- `created_at`
- `updated_at`

Requirements:

- Store the stable identity subject from the verified Neon Auth integration.
- Enforce uniqueness on `auth_subject_id`.
- Never accept the identity subject as an unrestricted user-supplied ownership value.
- Avoid duplicating authentication credentials or password data.
- Do not copy or independently manage Neon Auth session records.

### Account

Fields:

- `id`
- `user_id`
- `name`
- `type`
- `currency`
- `is_active`
- `created_at`
- `updated_at`

Account types may include checking, savings, cash, credit card, and other supported personal accounts.

### Transaction

Fields:

- `id`
- `user_id`
- `account_id`
- `transaction_date`
- `amount`
- `currency`
- `description`
- `normalized_description`
- `merchant`
- `normalized_merchant`
- `kind`
- `status`
- `category_id`
- `category_source`
- `categorization_rule_id`
- `external_transaction_id`
- `source_identifier`
- `created_at`
- `updated_at`

Use a calendar date for transaction dates. Preserve source timestamps separately only if needed by a supported import format.

### Category

Fields:

- `id`
- `user_id` or a clearly defined system-category ownership representation
- `name`
- `kind`
- `parent_category_id`
- `is_active`
- timestamps

Support system-provided categories and user-owned categories without permitting users to modify another user's records.

### CategorizationRule

Fields:

- `id`
- `user_id` or system ownership
- `name`
- `priority`
- `condition_type`
- `condition_value`
- `category_id`
- `is_active`
- timestamps

### ImportJob

Fields:

- `id`
- `user_id`
- `source_format`
- `status`
- `content_digest`
- `started_at`
- `completed_at`
- `total_rows`
- `created_count`
- `duplicate_count`
- `failed_count`
- sanitized error summary

### ImportRecord

Fields:

- `id`
- `import_job_id`
- `row_number`
- `status`
- `transaction_id`
- `error_code`
- `fingerprint`

### TransferLink

Fields:

- `id`
- `user_id`
- `source_transaction_id`
- `destination_transaction_id`
- `status`
- timestamps

### TransactionRevision

Recommended for tracking manual corrections and important changes.

Fields:

- `id`
- `user_id`
- `transaction_id`
- `changed_fields`
- `previous_values`
- `new_values`
- `created_at`

Do not log sensitive raw transaction content through application logs just because a revision record exists.

### Relational Integrity

- Every user-owned record must be associated with an owner.
- Every transaction's account must belong to the same user as the transaction.
- A category or categorization rule must be system-accessible or owned by the same user.
- Transfer links must connect valid transactions owned by the same user.
- Use database constraints and, where appropriate, composite foreign keys to enforce ownership consistency.
- Use migrations for all schema changes.

---

## 6. Financial Domain Rules

These rules must be documented and implemented before analytics development.

### Monetary Precision

- Use Python `Decimal` for monetary arithmetic.
- Use PostgreSQL `NUMERIC(19,2)` for the MVP's monetary values.
- Reject unsupported fractional precision rather than silently rounding.
- Return monetary amounts as decimal strings in API responses.
- Never use binary floating-point arithmetic for money.

The MVP supports USD only. Reject unsupported currencies explicitly.

### Transaction Signs

- Income: positive amount.
- Expense: negative amount.
- Refund: positive amount.
- Transfer out: negative amount.
- Transfer in: positive amount.

Persist the transaction kind explicitly. Do not determine the meaning of a transaction solely from its sign.

### Transaction Status

Support:

- `pending`
- `posted`
- `voided`

Default financial analytics to posted transactions only. Exclude pending and voided transactions unless an endpoint explicitly documents a different status filter.

### Transfers

Transfers between a user's own accounts must not inflate income or expenses.

Represent an internal transfer with two signed transactions linked together:

- Source account: negative amount.
- Destination account: positive amount.

Transfers are excluded from income, expenses, refunds, and net cash flow.

Do not automatically match unrelated transactions based on amount alone. Any matching logic must have explicit criteria and a safe manual correction path.

### Credit Card Purchases and Payments

- A credit card purchase is an expense.
- Paying a credit card from a checking account is an internal transfer, not another expense.
- Credit card payments must not double-count purchases already recorded on the card account.

### Refunds

- Record refunds as separate positive refund transactions.
- Refunds reduce net spending.
- Refunds are not ordinary income.

### Analytics Definitions

- Gross income = sum of posted income amounts.
- Gross expenses = absolute sum of posted expense amounts.
- Refunds = sum of posted refund amounts.
- Net spending = gross expenses minus refunds.
- Net cash flow = gross income minus gross expenses plus refunds.
- Internal transfers are excluded from these measures.

If net spending is negative due to refunds, preserve the actual calculation rather than silently clamping it to zero.

### Date Ranges

Use inclusive start dates and exclusive end dates:

`start_date <= transaction_date < end_date`

For a calendar month, use the first day of that month through, but not including, the first day of the following month.

Test month boundaries, leap years, and empty periods.

---

## 7. Authentication and Authorization

### Authentication Provider

Use **Neon Auth / Managed Better Auth** as the default authentication provider. Do not add Supabase Auth as a second provider for the MVP.

Neon Auth is responsible for identity and supported authentication flows. FastAPI remains responsible for protecting the business API.

### Required Application Components

Implement:

- `app/core/security.py` for the documented authentication integration.
- An authentication dependency that returns a verified identity.
- An application-user resolution function or service.
- A standard unauthenticated response.
- Ownership-aware repository and service methods.
- Tests for missing, invalid, expired, and incorrectly scoped credentials.

The exact credential verification implementation must follow the verified Neon Auth integration discovered during the authentication checkpoint.

### Ownership Rules

- Derive the current user from verified authentication information.
- Never trust a `user_id` supplied in a query parameter, body, header, or path as proof of ownership.
- Scope every user-owned query to the authenticated user's internal profile ID.
- Verify ownership before reading, updating, deleting, or linking records.
- Return consistent not-found or authorization responses that do not leak another user's data.
- Protect imports, import histories, categories, rules, transfer links, and analytics—not just accounts and transactions.
- Keep administrative and seed-data operations separate from normal user-facing requests.

### Defense in Depth

Consider PostgreSQL row-level security after the API-level authorization model works and is tested.

If RLS is implemented, document how authenticated identity reaches the database connection and how pooled connections prevent identity context from leaking between requests. Do not assume that merely enabling RLS creates correct policies.

### Security and Privacy

- Never log bearer tokens, cookies, session credentials, passwords, or secrets.
- Avoid logging raw imported records, descriptions, or unnecessary financial details.
- Keep credentials in environment variables or the hosting provider's secret manager.
- Commit `.env.example`, never real `.env` secrets.
- Use TLS for remote database connections.
- Validate file sizes, row counts, MIME/format expectations, and input content.
- Do not expose stack traces or database errors in public API responses.

---

## 8. API Scope

All business endpoints use the `/api/v1` prefix.

### Health

- `GET /health/live`
- `GET /health/ready`

Liveness should not depend on database availability. Readiness should report whether required dependencies are available without disclosing credentials or internal connection details.

### Accounts

- `GET /api/v1/accounts`
- `POST /api/v1/accounts`
- `GET /api/v1/accounts/{id}`
- `PATCH /api/v1/accounts/{id}`
- `DELETE /api/v1/accounts/{id}`

Define safe behavior for accounts with existing transactions. Prefer deactivation or archival where deletion would break financial history.

### Transactions

- `GET /api/v1/transactions`
- `POST /api/v1/transactions`
- `GET /api/v1/transactions/{id}`
- `PATCH /api/v1/transactions/{id}`
- `DELETE /api/v1/transactions/{id}`

Support pagination, filtering by account, date range, status, category, kind, and merchant as appropriate.

Avoid hard deletion where it would undermine transfer integrity or auditability. Define deletion and voiding semantics explicitly.

### Categories

- `GET /api/v1/categories`
- `POST /api/v1/categories`
- `PATCH /api/v1/categories/{id}`

### Categorization Rules

- `GET /api/v1/categorization-rules`
- `POST /api/v1/categorization-rules`
- `PATCH /api/v1/categorization-rules/{id}`
- `DELETE /api/v1/categorization-rules/{id}`

### Imports

- `POST /api/v1/imports/preview`
- `POST /api/v1/imports`
- `GET /api/v1/imports`
- `GET /api/v1/imports/{id}`

Support CSV and JSON.

### Transfers

- `POST /api/v1/transfers/match`
- `DELETE /api/v1/transfers/{id}`

Specify how matching, unmatching, and reversal work so linked transactions cannot be left in an inconsistent state.

### Analytics

- `GET /api/v1/analytics/summary`
- `GET /api/v1/analytics/monthly-trends`
- `GET /api/v1/analytics/categories`
- `GET /api/v1/analytics/merchants`

Every endpoint must document its parameters, response schemas, date behavior, financial definitions, error responses, and authentication requirements.

---

## 9. Import Pipeline

### Supported Inputs

- CSV files with documented required columns and optional mappings.
- JSON records with a documented schema.

Do not build a universal file-import framework in the MVP.

### Processing Flow

1. Validate the upload size and format.
2. Parse the input safely.
3. Normalize dates, descriptions, merchant names, and amounts.
4. Validate required fields and transaction semantics.
5. Compute stable identifiers or duplicate fingerprints where possible.
6. Apply duplicate-detection rules.
7. Apply categorization precedence.
8. Produce a preview or persist a committed import.
9. Record per-row results and import summary.
10. Return a sanitized result to the caller.

### Preview and Commit

Preview must not create transactions or otherwise mutate persistent business data.

Commit must revalidate input and enforce duplicate detection again. Do not trust a preview result as authorization to skip validation.

### Idempotency and Duplicates

- Prefer a stable source transaction ID when available.
- Use deterministic fingerprints as a fallback, with documented limitations.
- Do not silently discard legitimate purchases merely because date, amount, and merchant match.
- Bind import idempotency keys to the request content.
- Reusing an idempotency key with different content must return a conflict.
- Define how pending transactions are reconciled with posted versions.
- Preserve manual category overrides during reimports.

### Failure Semantics

- Invalid rows may be reported individually where partial success is supported.
- Unexpected database persistence failures must roll back the affected transaction or import unit atomically.
- Store sanitized error codes and row numbers, not raw sensitive payloads.
- Enforce file-size and row-count limits.

---

## 10. Categorization

Use deterministic categorization rather than AI for the MVP.

Precedence:

1. Existing manual correction.
2. Matching user-defined rule.
3. Matching system rule.
4. Uncategorized.

Requirements:

- Rules have predictable priority and deterministic tie-breaking.
- Manual corrections survive rule changes and reimports.
- Rule updates do not silently overwrite manual decisions.
- Users cannot apply another user's rules or categories.
- Store categorization provenance so a category can be traced to manual input or a rule.
- Test overlapping rules, inactive rules, and unmatched transactions.

---

## 11. Testing Strategy

Use pytest and HTTPX. Run integration tests against PostgreSQL-compatible infrastructure; SQLite-only tests are not sufficient for database behavior and constraints.

### Unit Tests

Test:

- Decimal parsing and precision.
- Sign conventions and transaction kinds.
- Date-range logic.
- Monthly boundaries.
- Analytics formulas.
- Categorization precedence.
- Normalization and fingerprint generation.

### Integration Tests

Test:

- SQLAlchemy persistence and constraints.
- Alembic migrations from an empty database.
- Import commit and rollback behavior.
- Duplicate detection and idempotency.
- Transfer-link integrity.
- Analytics queries against realistic datasets.
- Database failures and transaction boundaries.

### API Tests

Test:

- Authentication success and failure.
- CRUD validation.
- Pagination and filters.
- Error response consistency.
- Request and response schemas.
- Every route's ownership checks.

### Security Tests

Create at least two users and verify that one cannot:

- Read or modify the other's accounts.
- Read, update, or delete the other's transactions.
- Access the other's import history.
- Use the other's categories or categorization rules.
- Create or alter transfer links involving the other's transactions.
- Access analytics derived from the other's financial records.

Also test forged ownership IDs, invalid credentials, expired credentials, and missing credentials.

### Financial Invariant Tests

Cover:

- No binary floating-point monetary arithmetic.
- Invalid precision is rejected.
- Internal transfers do not affect income or spending.
- Credit card payments do not double-count expenses.
- Refunds reduce net spending and are not income.
- Pending and voided transactions are excluded by default.
- January 31 and February 1 fall into the correct months.
- Empty periods return valid zero-value analytics.
- Zero-denominator percentages do not produce errors or invalid values.
- Reimports do not duplicate previously imported transactions.
- Manual category overrides survive reimports.

### Property and Reconciliation Tests

Where useful, verify invariants across generated datasets, not just hand-written examples. For example, the reported net cash flow must equal income minus expenses plus refunds under the documented definitions.

---

## 12. Development Phases

Each phase must conclude with tests, acceptance criteria, setup/run instructions, and a checkpoint before proceeding.

### Phase 0 — Artifacts and Documentation Setup

Create the project artifacts that guide implementation:

- Version this development plan in `docs/project-plan.md` and provide a root `README.md` that links to the documentation.
- Establish requirements, architecture, domain model, financial rules, API contracts, import pipeline, security, testing, deployment, and roadmap documents under `docs/`.
- Create ADRs for the major design decisions and record unresolved decisions as proposed rather than presenting them as verified.
- Add source-controlled Mermaid diagrams for the system, entities, import pipeline, and authentication flow.
- Identify the Phase 1 implementation artifacts and the evidence required at each later checkpoint.

Tests and acceptance criteria:

- Every documentation artifact listed for Phase 0 exists, is readable, and is linked from the README or documentation index.
- Documents agree on the MVP scope, financial definitions, ownership model, and phase boundaries.
- Provider-specific authentication and hosting details remain explicit verification gates where current behavior has not been confirmed.
- No implementation, credential, migration, test result, or deployment status is claimed before it exists.

Checkpoint: a contributor can use the documentation to start Phase 1 with clear scope and open decisions. Phase 0 requires document/link review, not application tests.

### Phase 1 — Repository and Foundation

Implement:

- Repository and dependency management.
- FastAPI application entry point.
- Configuration and environment validation.
- SQLAlchemy database connection.
- Neon PostgreSQL connectivity.
- Alembic initialization.
- Local Docker Compose PostgreSQL.
- Health endpoints.
- Basic GitHub Actions workflow.
- Update the Phase 0 README with working setup commands and add `.env.example`.

Tests and acceptance criteria:

- The application starts locally.
- Health endpoints behave as documented.
- Database connectivity works with local PostgreSQL and can be configured for Neon.
- Migrations can be applied.
- Tests and lint/type checks selected for the project pass in CI.
- No secrets are committed.

Checkpoint: a clean checkout can be configured and run using documented commands.

### Phase 2 — Domain Model and Financial Rules

Implement:

- Money utilities.
- Transaction kinds and statuses.
- SQLAlchemy models.
- Database constraints.
- Alembic migrations.
- Financial rules documentation.
- Initial domain and persistence tests.

Tests and acceptance criteria:

- Monetary precision rules are enforced.
- Account and transaction relationships are valid.
- Transfer and category ownership constraints are defined.
- Date and transaction semantics are documented and tested.
- A fresh database can be migrated successfully.

Checkpoint: the financial domain is consistent before business endpoints are added.

### Phase 3 — Neon Auth and Authenticated CRUD

Implement:

- Neon Auth configuration for development and deployment.
- Verified authentication integration for FastAPI.
- Application-user resolution.
- User-scoped repository/service patterns.
- Accounts, transactions, and categories endpoints.
- Standard authentication and authorization errors.
- Cross-user security tests.

First, complete the authentication integration gate in Section 3 and record the chosen verification approach in an ADR.

Tests and acceptance criteria:

- Valid credentials identify the correct user.
- Invalid or missing credentials are rejected.
- No request can choose its own effective user identity.
- Every CRUD operation enforces ownership.
- The application does not log credentials.
- Database and API integration tests pass.

Checkpoint: authenticated users can manage only their own data.

### Phase 4 — Imports and Categorization

Implement:

- CSV and JSON parsing.
- Validation and normalization.
- Import preview and commit.
- Import history and row results.
- Duplicate detection and idempotency.
- Categorization rules.
- Manual category overrides.
- Import limits and sanitized error reporting.

Tests and acceptance criteria:

- Preview has no persistent side effects.
- Valid rows are handled according to documented partial-success semantics.
- Duplicate and idempotency behavior is deterministic.
- Unexpected persistence failures roll back correctly.
- Manual category choices survive reimports.
- All import and rule operations enforce user ownership.

Checkpoint: synthetic transaction datasets can be imported and reconciled repeatably.

### Phase 5 — Analytics

Implement:

- Summary analytics.
- Monthly trends.
- Category breakdowns.
- Merchant analysis.
- Query filters and date ranges.
- Consistent response schemas and decimal serialization.

Tests and acceptance criteria:

- Every metric matches its documented formula.
- Transfers are excluded.
- Refunds and credit card payments are treated correctly.
- Pending and voided transactions are excluded by default.
- Empty periods return valid responses.
- Results reconcile against known synthetic datasets.

Checkpoint: published analytics match independently calculated expected results.

### Phase 6 — Hardening and End-to-End Verification

Implement:

- Consistent error handling.
- Logging redaction.
- Request limits and pagination limits.
- Migration verification.
- Dependency and configuration checks.
- Expanded integration and security tests.
- Database failure tests.
- Synthetic demo data and a reproducible demo workflow.

Tests and acceptance criteria:

- The full suite passes against PostgreSQL.
- Cross-user tests cover every user-owned resource.
- Import and transfer failures do not leave inconsistent state.
- No secrets or raw financial records appear in logs.
- The application starts from a clean environment.

Checkpoint: the API is ready for a controlled public portfolio deployment.

### Phase 7 — Deployment and Portfolio Presentation

Implement:

- Neon production database.
- Production Neon Auth configuration.
- Managed Python hosting.
- Environment-specific settings and secrets.
- Deployment health checks.
- CI deployment workflow if supported by the chosen host.
- OpenAPI documentation.
- Synthetic sample datasets.
- README walkthrough.
- Architecture and data-model diagrams.
- Known limitations and final test report.

Tests and acceptance criteria:

- A clean deployment can run database migrations.
- The deployed API passes health checks.
- Authentication works with the deployed environment.
- Public endpoints do not expose private financial data.
- Synthetic demo data can be loaded safely.
- API docs and usage examples work.
- Deployment and troubleshooting instructions are reproducible.

Checkpoint: a reviewer can understand the architecture, exercise the API, and verify the core financial behavior without providing real financial information.

### Phase 8 — Optional Enhancements

Only begin after the MVP definition of done is met.

Possible extensions:

- Recurring transaction detection.
- Budgets and budget-versus-actual reporting.
- Savings-rate analytics.
- Configurable merchant aliases.
- More advanced categorization.
- Background processing for large imports.
- Multi-currency support with explicit exchange-rate semantics.
- Read-only reporting frontend.
- PostgreSQL row-level security as an additional isolation layer.

Every extension must include requirements, design decisions, tests, and documentation.

---

## 13. Required Documentation and Artifacts

Phase 0 creates the README, this plan, the requirements/design documents, ADRs, and Mermaid diagram sources. The remaining root, application, test, CI, sample-data, and deployment artifacts are created in their implementation phases; this section is the complete project inventory, not a claim that every item exists in Phase 0.

### Root Files

- `README.md`
- `pyproject.toml`
- `uv.lock`
- `.gitignore`
- `.env.example`
- `Dockerfile`
- `docker-compose.yml`
- `alembic.ini`

### Requirements and Design

- `docs/requirements.md`
- `docs/architecture.md`
- `docs/domain-model.md`
- `docs/financial-rules.md`
- `docs/api-contracts.md`
- `docs/import-pipeline.md`
- `docs/security.md`
- `docs/testing-strategy.md`
- `docs/deployment.md`
- `docs/roadmap.md`

### Architecture Decision Records

- `docs/adr/ADR-001-architecture.md`
- `docs/adr/ADR-002-money-and-transaction-semantics.md`
- `docs/adr/ADR-003-neon-auth-and-authorization.md`
- `docs/adr/ADR-004-duplicate-detection-and-idempotency.md`
- `docs/adr/ADR-005-analytics-definitions.md`

The authentication ADR must record the verified Neon Auth flow, the chosen FastAPI verification strategy, user identity mapping, and any limitations or unresolved questions.

### Diagrams

- `docs/diagrams/system-architecture.mmd`
- `docs/diagrams/entity-relationships.mmd`
- `docs/diagrams/import-pipeline.mmd`
- `docs/diagrams/authentication-flow.mmd`

### Application and Delivery

- All application modules.
- Alembic migrations.
- Unit, integration, API, and security tests.
- Synthetic CSV and JSON files.
- Expected analytics totals.
- Duplicate and lifecycle fixtures.
- Seed script.
- GitHub Actions workflow.
- API examples.
- Deployment instructions.
- Final test report.
- Known limitations.
- Short portfolio walkthrough.

---

## 14. Local Development Workflow

Use `uv` for dependency and environment management.

Typical setup:

```bash
uv sync --all-groups
docker compose up -d db
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Run tests:

```bash
uv run pytest
uv run pytest tests/unit -q
uv run pytest tests/integration -q
uv run pytest tests/api -q
```

These commands are the intended workflow; adjust the test paths and dependency groups to match the final repository.

The `.env.example` should document the required local configuration, including:

- Application environment.
- Database URL.
- Neon Auth URL and other configuration required by the verified integration.
- Any required token-verification settings.
- Logging level.
- Import limits.
- Optional test database configuration.

Do not commit actual credentials. Document separate configuration for local development, automated tests, and deployment.

---

## 15. CI and Quality Gates

The GitHub Actions workflow should run on pull requests and pushes to the main development branch.

Minimum checks:

- Dependency installation from the lockfile.
- Formatting and linting.
- Type checks where configured.
- Unit tests.
- Integration tests against PostgreSQL.
- Migration validation.
- API and authorization tests.
- Secret scanning or equivalent repository hygiene checks where practical.

A change must not be considered complete merely because the application starts. The relevant tests and acceptance criteria for that phase must pass.

---

## 16. Definition of Done

The MVP is complete when all of the following are true:

### Core API
- [ ] FastAPI application is organized into clear modules.
- [ ] Neon PostgreSQL stores application data.
- [ ] SQLAlchemy and Alembic are configured.
- [ ] Accounts, transactions, categories, and categorization rules are supported.
- [ ] API schemas, validation, pagination, and error responses are documented.

### Authentication and Security
- [ ] Neon Auth / Managed Better Auth is configured.
- [ ] FastAPI uses a verified, documented authentication integration.
- [ ] Authenticated identity is mapped to an application user profile.
- [ ] Every user-owned endpoint enforces ownership.
- [ ] Cross-user access tests pass.
- [ ] Tokens, credentials, and sensitive transaction content are not logged.
- [ ] Secrets are not committed.
- [ ] Optional RLS, if implemented, is tested independently of API authorization.

### Financial Correctness
- [ ] Monetary calculations use Decimal-compatible logic.
- [ ] Unsupported precision and currencies are rejected.
- [ ] Transaction kinds and statuses are explicit.
- [ ] Transfers do not inflate income or expenses.
- [ ] Credit card payments do not double-count purchases.
- [ ] Refunds reduce net spending and are not income.
- [ ] Pending and voided transactions are excluded from default analytics.
- [ ] Date-range and month-boundary behavior is tested.
- [ ] Analytics reconcile against expected synthetic results.

### Imports and Categorization
- [ ] CSV and JSON imports work.
- [ ] Preview does not persist business changes.
- [ ] Import validation and normalization are implemented.
- [ ] Duplicate detection and idempotency are tested.
- [ ] Import history and row-level results are available.
- [ ] Persistence failures roll back correctly.
- [ ] Manual category overrides survive reimports.

### Engineering Quality
- [ ] Unit, integration, API, and security tests pass.
- [ ] Tests run against PostgreSQL where database behavior matters.
- [ ] CI is configured.
- [ ] Database migrations work from a clean database.
- [ ] Synthetic demo data is reproducible.
- [ ] Logging and error handling are hardened.
- [ ] API documentation is available.
- [ ] Architecture, domain rules, security, and deployment are documented.
- [ ] Each development phase has a recorded checkpoint and known limitations.

### Deployment and Portfolio
- [ ] The API is deployed to a publicly reachable environment.
- [ ] Production database and authentication configuration are separate from local development.
- [ ] Public documentation and API examples are usable.
- [ ] The demo uses synthetic data only.
- [ ] The README explains the problem, architecture, design decisions, tests, deployment, and limitations.
- [ ] A reviewer can exercise a documented demo flow without connecting a real bank account.

---

## 17. Working Rules for Implementation

1. Build in the specified phases; do not skip directly to analytics.
2. Finish one phase and verify its acceptance criteria before moving on.
3. At the end of every phase, provide:
   - A summary of completed work.
   - Files created or modified.
   - Tests run and results.
   - Setup and run instructions.
   - Known issues and limitations.
   - The next checkpoint.
4. Do not invent credentials, test results, deployment status, or unsupported features.
5. Treat financial correctness and user isolation as core requirements, not optional polish.
6. Record significant architecture choices in ADRs.
7. Prefer straightforward, maintainable implementations over unnecessary infrastructure.
8. Use synthetic data in tests, documentation, and public demos.
9. Verify current provider documentation before relying on authentication or deployment behavior.
10. Keep the MVP small enough to complete, test, deploy, and explain convincingly in an engineering interview.
