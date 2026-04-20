# Requirements: corpulse

**Defined:** 2026-04-20
**Core Value:** RAG teams can point corpulse at their vector DB and immediately understand what's wrong with their corpus without manual audits.

## v1.5 Requirements

### Retrieval Ordering + Acceptance Analytics

- [ ] **v1.5-01**: `Corpulse` and `AsyncCorpulse` expose `mean_reciprocal_rank()` over existing retrieval rows and engagement events, with sync/async parity and no schema changes.
- [ ] **v1.5-02**: `Corpulse` and `AsyncCorpulse` expose `acceptance_rate()` over the existing engagement table using a documented accepted-event convention, with no new ingestion APIs.
- [ ] **v1.5-03**: Shared aggregation helpers and backend query contracts support SQLite, Postgres, async Postgres, and in-memory backends with deterministic ordering and parity tests.

## v1.4 Requirements

### Nearly-Free RAG Analytics

- [x] **v1.4-01**: `Corpulse` and `AsyncCorpulse` expose low-confidence retrieval analytics as both a summary metric and a query-level detail method over existing retrieval rows, with no schema changes.
- [x] **v1.4-02**: Zero-result analytics remain a separate signal from low-confidence analytics and are computed from the same stored retrieval/query data without new ingestion APIs.
- [x] **v1.4-03**: Query-level aggregation needed for these analytics is implemented consistently across SQLite, Postgres, async Postgres, and in-memory backends, with sync/async parity tests.

## v1.3 Requirements

### Postgres Multi-Tenancy

- [x] **PGMT-01**: `PostgresBackend` accepts optional `schema` and `table_prefix` parameters so multiple tenants can share one database without table collisions.
- [x] **PGMT-02**: `AsyncPostgresBackend` accepts the same optional `schema` and `table_prefix` parameters with behavior matching the sync backend.
- [x] **PGMT-03**: Postgres schema creation and table/index DDL are generated from a public `build_schema_sql(schema=None, prefix="")` helper.
- [x] **PGMT-04**: Invalid Postgres identifiers for `schema` or `table_prefix` are rejected with `ValueError` before any SQL executes.
- [x] **PGMT-05**: Sync and async Postgres tests prove per-schema isolation and prefix-only mode on one database.

### DSN Compatibility

- [x] **DSN-01**: `AsyncPostgresBackend.create()` accepts SQLAlchemy-style DSNs such as `postgresql+asyncpg://...` by normalizing them before pool creation.
- [x] **DSN-02**: `PostgresBackend` accepts equivalent normalized DSN variants for symmetry with the async backend.
- [x] **DSN-03**: Tests prove passthrough and normalized DSN forms behave identically.

### Qdrant Tenant Helpers

- [x] **QDRT-HELP-01**: `collection_name_for_user(user_id, base="corpulse")` returns a deterministic, sanitized collection name using only `[a-z0-9_]`.
- [x] **QDRT-HELP-02**: `chunk_id(doc_id, chunk_index)` returns deterministic UUIDv5 identifiers for vector chunks.
- [x] **QDRT-HELP-03**: `delete_document_points(...)` removes Qdrant points for one document via payload filtering and exposes a clear result contract.
- [x] **QDRT-HELP-04**: `ensure_collection(...)` creates tenant-ready collections idempotently, including the required payload indexes.
- [x] **QDRT-HELP-05**: Helper additions preserve the current lazy-import behavior of `corpulse.integrations.qdrant`.

### Indexing Pipeline MVP

- [x] **PIPE-01**: `corpulse.pipelines.indexing.index_document(...)` orchestrates parse → chunk → embed → Qdrant upsert → Corpulse register flow for one document.
- [x] **PIPE-02**: The indexing pipeline retries embedding failures with bounded backoff before failing.
- [x] **PIPE-03**: If indexing fails after vector upsert begins, the pipeline rolls back Qdrant points for that document before re-raising.
- [x] **PIPE-04**: The first pipeline version returns a minimal result contract (`doc_id`, `chunk_count`, `duration_ms`) without inventing unsupported Corpulse semantics.
- [x] **PIPE-05**: Pipeline tests cover both happy path and rollback behavior using fakes.

### Typed Async Payload Models

- [x] **MODEL-01**: Typed models mirror the current async `report()` payload shape exactly (`summary` plus `rows`) without changing the public method contract.
- [x] **MODEL-02**: Typed models mirror the current async `cleanup_report()` analysis payload shape exactly (`ghosts`, `obsolete`, `stale`, `suspects`, metadata) without changing the public method contract.
- [x] **MODEL-03**: Internal helper/model layers can expose typed payloads while `AsyncCorpulse.report()` and `AsyncCorpulse.cleanup_report()` remain backward-compatible for existing dict consumers.
- [x] **MODEL-04**: If a mutating cleanup API is added later, it is introduced as a new operation rather than overloading `cleanup_report()`.

### FastAPI Optional Integration

- [x] **FASTAPI-01**: `corpulse[fastapi]` provides an optional router helper that wires tenant-scoped `AsyncCorpulse` instances into HTTP endpoints.
- [x] **FASTAPI-02**: The router exposes report, cleanup-report, ghosts, duplicates, obsolete, stale, and suspects endpoints using the milestone’s typed payload models.
- [x] **FASTAPI-03**: The FastAPI integration remains optional and does not add import/runtime cost for non-FastAPI consumers.
- [x] **FASTAPI-04**: FastAPI tests verify route wiring, status codes, and response schemas with a dummy factory.

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
| v1.5-01 | Phase 22 | Complete |
| v1.5-02 | Phase 23 | Planned |
| v1.5-03 | Phase 22-23 | Complete |
| v1.4-01 | Phase 21 | Complete |
| v1.4-02 | Phase 21 | Complete |
| v1.4-03 | Phase 21 | Complete |
| DSN-01 | Phase 15 | Complete |
| DSN-02 | Phase 15 | Complete |
| DSN-03 | Phase 15 | Complete |
| PGMT-01 | Phase 16 | Complete |
| PGMT-02 | Phase 16 | Complete |
| PGMT-03 | Phase 16 | Complete |
| PGMT-04 | Phase 16 | Complete |
| PGMT-05 | Phase 16 | Complete |
| QDRT-HELP-01 | Phase 17 | Complete |
| QDRT-HELP-02 | Phase 17 | Complete |
| QDRT-HELP-03 | Phase 17 | Complete |
| QDRT-HELP-04 | Phase 17 | Complete |
| QDRT-HELP-05 | Phase 17 | Complete |
| PIPE-01 | Phase 18 | Complete |
| PIPE-02 | Phase 18 | Complete |
| PIPE-03 | Phase 18 | Complete |
| PIPE-04 | Phase 18 | Complete |
| PIPE-05 | Phase 18 | Complete |
| MODEL-01 | Phase 19 | Complete |
| MODEL-02 | Phase 19 | Complete |
| MODEL-03 | Phase 19 | Complete |
| MODEL-04 | Phase 19 | Complete |
| FASTAPI-01 | Phase 20 | Complete |
| FASTAPI-02 | Phase 20 | Complete |
| FASTAPI-03 | Phase 20 | Complete |
| FASTAPI-04 | Phase 20 | Complete |

**Coverage:**
- v1.3-v1.5 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0

**Notes:**
- v1.5-01 and v1.5-03 are complete from Phase 22.
- v1.5-02 remains planned for Phase 23.
- v1.4 requirements remain validated in the shipped milestone history.

---
*Requirements defined: 2026-04-20*
*Last updated: 2026-04-20 after milestone v1.5 start*
