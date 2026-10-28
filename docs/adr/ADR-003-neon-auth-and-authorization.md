# ADR-003 — Neon Auth and authorization

**Status:** Accepted for implementation; live branch validation pending
**Decision date:** 2026-10-28

## Decision

Use Neon Auth / Managed Better Auth for identity. A client signs in using the Neon Auth SDK, calls `authClient.token()`, and sends the resulting JWT as an `Authorization: Bearer` credential to FastAPI. FastAPI verifies the EdDSA signature against the branch's JWKS at `<NEON_AUTH_BASE_URL>/.well-known/jwks.json`, with a bounded cache and key refresh on an unknown `kid`. It requires the issuer and audience to equal the origin of the configured Neon Auth URL, and validates expiry, issued-at time, and a nonempty `sub`. The verified `sub` maps to a unique application `UserProfile.auth_subject_id`.

The business API accepts the JWT, not Neon Auth's opaque browser session cookie. It never trusts decoded claims before signature and claim verification. SQLAlchemy continues to access application tables directly, with explicit user-scoped queries. No Data API token is assumed valid merely because Neon Data API accepts it; this integration is based on Neon's documented JWT plugin flow for external services.

## Evidence and limits

- Neon's [JWT plugin guide](https://neon.com/docs/auth/guides/plugins/jwt) documents `authClient.token()`, the JWKS URL, EdDSA, 15-minute tokens, issuer/audience examples, and external-backend use.
- Neon's [authentication flow](https://neon.com/docs/auth/authentication-flow) identifies `sub` as the stable user ID and distinguishes the opaque session cookie from the JWT.
- Neon's [branching authentication guide](https://neon.com/docs/auth/branching-authentication) documents branch-isolated identity and auth configuration.
- [PyJWT's API reference](https://pyjwt.readthedocs.io/en/stable/api.html) documents JWKS caching and key refresh; its [usage guide](https://pyjwt.readthedocs.io/en/stable/usage.html) documents EdDSA support with cryptography.

The official examples are reference material, not a production guarantee. This project tests signature and claim failures, cache rotation behavior, and cross-user isolation with synthetic keys. A real Neon branch has not been connected; its issued token, endpoint, DNS/TLS behavior, and client cookie flow still require an end-to-end smoke test before deployment. Auth URL and JWKS settings must be branch specific. Key rotation can cause short 401 windows if the issuer rotates keys before publishing them; the verifier refreshes unknown keys immediately and otherwise uses a five-minute JWKS cache.
