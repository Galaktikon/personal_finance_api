# Security and privacy

Neon Auth / Managed Better Auth is the intended identity provider. The FastAPI business API must independently verify the credential before deriving a stable subject and resolving the internal `UserProfile`. The exact supported flow is an [open integration gate](adr/ADR-003-neon-auth-and-authorization.md); consult current official Neon documentation in Phase 3 before implementation.

## Authorization

- Never accept a caller supplied `user_id` as proof of ownership.
- Scope all user-owned reads and writes to the verified internal profile.
- Validate ownership before account, transaction, category, rule, import, transfer, and analytics operations.
- Avoid revealing whether another user's resource exists.
- Enforce same-user relationships with database constraints where possible.
- Test every route with two users and forged ownership IDs.

## Data handling

Do not log bearer tokens, cookies, passwords, secrets, raw import rows, or unnecessary financial descriptions. Store credentials in environment variables or managed secrets; commit only an example configuration. Use TLS for remote database access, validate upload sizes and content, and return sanitized errors without traces.

PostgreSQL row-level security is optional defense in depth. If added, document identity propagation and pooled-connection cleanup, then test policies independently of API authorization.

## Verification gate

Confirm credential type, signature/session validation, issuer, audience, expiry, key rotation, stable subject, local/test/production separation, and compatibility with a custom FastAPI backend. A token intended for Neon's Data API is not assumed valid for this API.
