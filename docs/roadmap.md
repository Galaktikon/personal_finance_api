# Roadmap and checkpoints

The [development plan](project-plan.md#12-development-phases) contains the full deliverables and acceptance criteria. Complete one checkpoint before starting the next.

| Phase | Deliverable | Checkpoint |
|---|---|---|
| 0 | Versioned plan, docs, ADRs, Mermaid sources, README | A contributor can start Phase 1 from clear scope and open decisions |
| 1 | Runnable FastAPI foundation, local PostgreSQL, Alembic, CI, config | [Local checkpoint passed](checkpoints/phase-1.md); remote CI awaits a push |
| 2 | Models, migrations, money/domain rules | [Local checkpoint passed](checkpoints/phase-2.md); remote CI awaits a push |
| 3 | Verified Neon Auth JWT design and user-scoped CRUD | [Synthetic and PostgreSQL checkpoint](checkpoints/phase-3.md); live Neon smoke test pending |
| 4 | CSV/JSON imports, duplicates, categorization, transfers | [Local checkpoint passed](checkpoints/phase-4.md); synthetic imports reconcile repeatably |
| 5 | Summary and breakdown analytics | [Local checkpoint passed](checkpoints/phase-5.md); results match independent expected totals |
| 6 | Hardening and end-to-end tests | [Local checkpoint](checkpoints/phase-6.md); controlled deployment gate is documented |
| 7 | Deployment, docs, synthetic demo, final report | Reviewer can exercise and verify the API |
| 8 | Optional extensions | Begin only after MVP definition of done |

## Phase 1 artifact list

Create `pyproject.toml`, `uv.lock`, `.gitignore`, `.env.example`, `Dockerfile`, `docker-compose.yml`, `alembic.ini`, `app/`, `alembic/`, `tests/`, and `.github/workflows/` as their runnable configuration is implemented. Update the README with commands that have been tested. Phase 0 does not create empty runtime placeholders or assert a dependency lockfile exists.

## Phase 0 checkpoint

- Scope and requirements are captured in `docs/project-plan.md` and `docs/requirements.md`.
- Design docs and diagrams identify components, ownership, and financial rules.
- ADRs distinguish accepted project choices from proposed implementation details.
- Authentication integration, duplicate policy, and hosting are explicit later gates.
- Documentation and link review is the Phase 0 verification; application test results begin in Phase 1.
