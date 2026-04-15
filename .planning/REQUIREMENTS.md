# Requirements: corpulse

**Defined:** 2026-04-15
**Core Value:** RAG teams can point corpulse at their vector DB and immediately understand what's wrong with their corpus without manual audits.

## v1.3 Requirements

### Postgres Multi-Tenancy

- [x] **PGMT-01**: `PostgresBackend` accepts optional `schema` and `table_prefix` parameters so multiple tenants can share one database without table collisions.
- [x] **PGMT-02**: `AsyncPostgresBackend` accepts the same optional `schema` and `table_prefix` parameters with behavior matching the sync backend.
- [x] **PGMT-03**: Postgres schema creation and table/index DDL are generated from a public `build_schema_sql(schema=None, prefix="")` helper.
- [x] **PGMT-04**: Invalid Postgres identifiers for `schema` or `table_prefix` are rejected with `ValueError` before any SQL executes.
- [x] **PGMT-05**: Sync and async Postgres tests prove per-schema isolation and prefix-only mode on one database.

### DSN Compatibility

- [ ] **DSN-01**: `AsyncPostgresBackend.create()` accepts SQLAlchemy-style DSNs such as `postgresql+asyncpg://...` by normalizing them before pool creation.
- [ ] **DSN-02**: `PostgresBackend` accepts equivalent normalized DSN variants for symmetry with the async backend.
- [ ] **DSN-03**: Tests prove passthrough and normalized DSN forms behave identically.

### Qdrant Tenant Helpers

- [ ] **QDRT-HELP-01**: `collection_name_for_user(user_id, base="corpulse")` returns a deterministic, sanitized collection name using only `[a-z0-9_]`.
- [ ] **QDRT-HELP-02**: `chunk_id(doc_id, chunk_index)` returns deterministic UUIDv5 identifiers for vector chunks.
- [ ] **QDRT-HELP-03**: `delete_document_points(...)` removes Qdrant points for one document via payload filtering and exposes a clear result contract.
- [ ] **QDRT-HELP-04**: `ensure_collection(...)` creates tenant-ready collections idempotently, including the required payload indexes.
- [ ] **QDRT-HELP-05**: Helper additions preserve the current lazy-import behavior of `corpulse.integrations.qdrant`.

### Indexing Pipeline MVP

- [ ] **PIPE-01**: `corpulse.pipelines.indexing.index_document(...)` orchestrates parse → chunk → embed → Qdrant upsert → Corpulse register flow for one document.
- [ ] **PIPE-02**: The indexing pipeline retries embedding failures with bounded backoff before failing.
- [ ] **PIPE-03**: If indexing fails after vector upsert begins, the pipeline rolls back Qdrant points for that document before re-raising.
- [ ] **PIPE-04**: The first pipeline version returns a minimal result contract (`doc_id`, `chunk_count`, `duration_ms`) without inventing unsupported Corpulse semantics.
- [ ] **PIPE-05**: Pipeline tests cover both happy path and rollback behavior using fakes.

### Typed Async Payload Models

- [ ] **MODEL-01**: Typed models mirror the current async `report()` payload shape exactly (`summary` plus `rows`) without changing the public method contract.
- [ ] **MODEL-02**: Typed models mirror the current async `cleanup_report()` analysis payload shape exactly (`ghosts`, `obsolete`, `stale`, `suspects`, metadata) without changing the public method contract.
- [ ] **MODEL-03**: Internal helper/model layers can expose typed payloads while `AsyncCorpulse.report()` and `AsyncCorpulse.cleanup_report()` remain backward-compatible for existing dict consumers.
- [ ] **MODEL-04**: If a mutating cleanup API is added later, it is introduced as a new operation rather than overloading `cleanup_report()`.

### FastAPI Optional Integration

- [ ] **FASTAPI-01**: `corpulse[fastapi]` provides an optional router helper that wires tenant-scoped `AsyncCorpulse` instances into HTTP endpoints.
- [ ] **FASTAPI-02**: The router exposes report, cleanup-report, ghosts, duplicates, obsolete, stale, and suspects endpoints using the milestone’s typed payload models.
- [ ] **FASTAPI-03**: The FastAPI integration remains optional and does not add import/runtime cost for non-FastAPI consumers.
- [ ] **FASTAPI-04**: FastAPI tests verify route wiring, status codes, and response schemas with a dummy factory.

## v2 Requirements

### Future Integrations

- **INT-01**: ChromaDB wrapper
- **INT-02**: Pinecone wrapper
- **INT-03**: LangChain / LlamaIndex plugin

### Future Distribution and API Surface

- **DIST-01**: PyPI publishing
- **API-01**: Separate destructive cleanup API beyond analysis-only `cleanup_report()`
- **ASYNC-FUT-01**: Broader async-aware top-level helpers beyond the current facade

## Out of Scope

| Feature | Reason |
|---------|--------|
| Breaking replacement of async dict payloads with incompatible model shapes | Current README/tests define dict payload semantics; preserve compatibility in v1.3 |
| Broad service-layer business logic inside corpulse | Service repo remains the boundary for auth, deployment, and app-specific workflows |
| Non-Qdrant vector DB integrations | This milestone focuses on tenancy and indexing primitives around the existing Qdrant path |
| Full cleanup execution workflow with document deletion policies | The current milestone is about tenancy, typing, and ingestion primitives; destructive cleanup needs a separate design |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DSN-01 | Phase 15 | Pending |
| DSN-02 | Phase 15 | Pending |
| DSN-03 | Phase 15 | Pending |
| PGMT-01 | Phase 16 | Complete |
| PGMT-02 | Phase 16 | Complete |
| PGMT-03 | Phase 16 | Complete |
| PGMT-04 | Phase 16 | Complete |
| PGMT-05 | Phase 16 | Complete |
| QDRT-HELP-01 | Phase 17 | Pending |
| QDRT-HELP-02 | Phase 17 | Pending |
| QDRT-HELP-03 | Phase 17 | Pending |
| QDRT-HELP-04 | Phase 17 | Pending |
| QDRT-HELP-05 | Phase 17 | Pending |
| PIPE-01 | Phase 18 | Pending |
| PIPE-02 | Phase 18 | Pending |
| PIPE-03 | Phase 18 | Pending |
| PIPE-04 | Phase 18 | Pending |
| PIPE-05 | Phase 18 | Pending |
| MODEL-01 | Phase 19 | Pending |
| MODEL-02 | Phase 19 | Pending |
| MODEL-03 | Phase 19 | Pending |
| MODEL-04 | Phase 19 | Pending |
| FASTAPI-01 | Phase 20 | Pending |
| FASTAPI-02 | Phase 20 | Pending |
| FASTAPI-03 | Phase 20 | Pending |
| FASTAPI-04 | Phase 20 | Pending |

**Coverage:**
- v1.3 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-15*
*Last updated: 2026-04-15 after milestone v1.3 definition*
