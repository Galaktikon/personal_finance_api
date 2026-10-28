# Security and privacy

Neon Auth / Managed Better Auth is the identity provider. The FastAPI business API verifies a Bearer JWT against the branch-specific JWKS before deriving `sub` and resolving the internal `UserProfile`. The verified integration choice and remaining live-test limit are in [ADR-003](adr/ADR-003-neon-auth-and-authorization.md).

The verifier accepts EdDSA only. It checks signature, key ID, issuer and audience against the configured Auth URL origin, expiry, issued-at time, authenticated role, and a nonempty subject. It caches the JWKS for five minutes, refreshes immediately for unknown keys, and uses a five-second fetch timeout. Missing or invalid credentials return a generic `401`; an unreachable JWKS returns `503`. No credentials or raw claims are logged.

## Authorization

- Never accept a caller supplied `user_id` as proof of ownership.
- Scope all user-owned reads and writes to the verified internal profile.
- Validate ownership before account, transaction, category, rule, import, transfer, and analytics operations.
- Avoid revealing whether another user's resource exists.
- Enforce same-user relationships with database constraints where possible.
- Test every route with two users and forged ownership IDs.

## Data handling

Do not log bearer tokens, cookies, passwords, secrets, raw import rows, or unnecessary financial descriptions. Store credentials in environment variables or managed secrets; commit only an example configuration. Use TLS for remote database access, validate upload sizes and content, and return sanitized errors without traces.

The API strips submitted values and user-supplied field names from `422` validation responses. Unexpected request failures return a generic `500` and emit only a fixed `request_failed` log event without exception text. The Docker command and documented local Uvicorn command disable raw access logs, which otherwise can include query strings. Operators should keep raw access logging disabled at any hosting proxy as well. The application rejects request bodies above `REQUEST_MAX_BYTES` (3 MB by default), including streamed bodies; imports have a lower file limit. List routes cap page size at 100.

PostgreSQL row-level security is optional defense in depth. If added, document identity propagation and pooled-connection cleanup, then test policies independently of API authorization.

## Environment and live verification

Set `NEON_AUTH_BASE_URL` to the Auth URL of the same Neon branch as the application database. It is optional for local health and domain-only work; authenticated routes cannot operate without it, and production startup requires it. Tests use synthetic Ed25519 keys and a fake JWKS response. Before deployment, exercise sign-in, `authClient.token()`, and the FastAPI API against a real Neon Auth branch. A token accepted by Neon's Data API is not automatically trusted by this API.
