# Roadmap: corpulse

## Milestones

- ✅ **v1.0 — Qdrant Wrapper + Packaging** - Phases 1-5 (shipped 2026-04-07)
- ✅ **v1.1 — Pluggable Storage Backends** - Phases 6-10 (shipped 2026-04-09, archive: `.planning/milestones/v1.1-ROADMAP.md`)
- ✅ **v1.2 — Full Async Parity** - Phases 11-14 (shipped 2026-04-12, archive: `.planning/milestones/v1.2-ROADMAP.md`)
- 🚧 **v1.3 — Multi-Tenant Integrations** - Phases 15-20

## Current Milestone: v1.3 — Multi-Tenant Integrations

**Goal:** Make corpulse service-ready for tenant-scoped use by improving Postgres tenancy support, normalizing DSNs, adding Qdrant tenant/indexing primitives, and introducing typed integration surfaces in a backward-compatible order.

## Phases

### Phase 15: DSN Normalization

**Goal**: Accept SQLAlchemy-style Postgres DSNs in both sync and async backends without changing current plain-DSN behavior.
**Depends on**: Phase 14
**Requirements**: DSN-01, DSN-02, DSN-03

Plans:

- [ ] 15-01: Add DSN normalization helpers to sync and async Postgres backends with regression tests

### Phase 16: Postgres Multi-Tenancy

**Goal**: Add validated `schema` and `table_prefix` support to sync and async Postgres backends using shared DDL/table-name generation.
**Depends on**: Phase 15
**Requirements**: PGMT-01, PGMT-02, PGMT-03, PGMT-04, PGMT-05

Plans:

- [x] 16-01: Introduce shared identifier validation and public `build_schema_sql(schema=None, prefix="")`
- [x] 16-02: Refactor sync and async Postgres queries to use qualified table helpers
- [x] 16-03: Add isolation, prefix-mode, and invalid-identifier coverage

### Phase 17: Qdrant Tenant Helpers

**Goal**: Add reusable, additive Qdrant helper functions for tenant-safe collection naming, deterministic chunk IDs, document-point deletion, and idempotent collection setup.
**Depends on**: Phase 16
**Requirements**: QDRT-HELP-01, QDRT-HELP-02, QDRT-HELP-03, QDRT-HELP-04, QDRT-HELP-05

Plans:
**Plans:** 1/2 plans executed
- [x] 17-01-PLAN.md — Add additive helper functions to `corpulse.integrations.qdrant` while preserving lazy imports
- [ ] 17-02-PLAN.md — Add deterministic and idempotency-focused helper tests

### Phase 18: Indexing Pipeline MVP

**Goal**: Ship a minimal async indexing pipeline over parser/chunker/embedder protocols and Qdrant rollback semantics without inventing unsupported Corpulse behaviors.
**Depends on**: Phase 17
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05

Plans:

- [ ] 18-01: Define indexing protocols and minimal result contract
- [ ] 18-02: Implement orchestration, retries, and rollback behavior
- [ ] 18-03: Add fake-driven happy-path and rollback tests

### Phase 19: Typed Async Payload Models

**Goal**: Introduce typed models that mirror the current async report and cleanup-report payloads exactly while preserving existing method contracts.
**Depends on**: Phase 18
**Requirements**: MODEL-01, MODEL-02, MODEL-03, MODEL-04

Plans:

- [ ] 19-01: Define typed models for existing async report payload structures
- [ ] 19-02: Integrate typed model builders without breaking dict-based consumers

### Phase 20: FastAPI Optional Integration

**Goal**: Add an optional FastAPI router helper over tenant-scoped `AsyncCorpulse` instances and the typed async payload layer.
**Depends on**: Phase 19
**Requirements**: FASTAPI-01, FASTAPI-02, FASTAPI-03, FASTAPI-04

Plans:

- [ ] 20-01: Add optional `corpulse.fastapi` package and dependency extras
- [ ] 20-02: Implement router factory and integration tests

## Current Status

- Active milestone: `v1.3 — Multi-Tenant Integrations`
- Latest shipped milestone: `v1.2 — Full Async Parity`
- Next workflow step: `/gsd-execute-phase 16`

---
