# Environments and deployment

Deployment is a Phase 7 deliverable. The intended production shape is managed Python hosting, Neon PostgreSQL, and a distinct Neon Auth environment. Current host choice, free-tier quotas, sleep behavior, auth configuration, and email-delivery limits require verification before commitment. Phase 6 verified the local container, clean migration path, health checks, and synthetic API workflow.

## Environment separation

Local development uses Docker Compose PostgreSQL. Automated tests use a disposable PostgreSQL-compatible database. Production uses separate database and authentication settings. Secrets stay in environment configuration or a managed secret store; `.env.example` will document names without values in Phase 1 and be expanded after the auth integration gate.

## Release gate

Before publishing, validate clean database migrations, health checks, authentication, user isolation, synthetic demo loading, API examples, and the full PostgreSQL-backed test suite. Keep raw access logs disabled at the hosting proxy and apply a request body ceiling there as well. Document deployment and troubleshooting commands only after they are exercised. Publish known limitations and a final test report with actual results.

No public deployment exists as of Phase 6. The [Phase 6 checkpoint](checkpoints/phase-6.md) records the local release gate and the remaining live Neon Auth and remote CI checks.
