# ADR-003 — Neon Auth and authorization

**Status:** Proposed; integration gate remains open  
**Decision date:** 2026-10-27

## Planned decision

Use Neon Auth / Managed Better Auth for identity and map a verified, stable subject to a unique application `UserProfile`. FastAPI enforces business API authorization; all user-owned queries use the resolved internal user ID.

## Required verification before Phase 3 code

Read current [Neon Auth overview](https://neon.com/docs/auth/overview) and [authentication flow](https://neon.com/docs/auth/authentication-flow). Confirm the client credential, supported verification method for custom FastAPI, issuer/audience/expiry/signature or server-side session checks, key rotation, stable subject, and separate environments. Document the precise approach and limitations here before implementing `app/core/security.py`.

Do not trust decoded claims without verification or assume Data API tokens can authorize this API. If direct token verification is unsupported, evaluate documented server-side session validation. Do not silently change identity providers.
