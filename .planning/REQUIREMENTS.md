# Requirements: corpulse

**Defined:** 2026-03-24
**Core Value:** RAG teams can point corpulse at their vector DB and immediately understand corpus health — no manual instrumentation

## v1 Requirements

### Packaging

- [x] **PKG-01**: Library installable via `pip install git+https://github.com/.../corpulse`
- [x] **PKG-02**: pyproject.toml with build metadata, Python >=3.10 requirement, and dependency declarations
- [x] **PKG-03**: Optional `[qdrant]` extra installs qdrant-client dependency
- [x] **PKG-04**: `import corpulse` succeeds without qdrant-client installed (lazy import)
- [x] **PKG-05**: Package uses `corpulse/` directory structure (not flat files)

### Qdrant Wrapper

- [x] **QDRT-01**: `QdrantCorpulseClient` wraps a user-provided `QdrantClient` via composition
- [x] **QDRT-02**: Wrapper intercepts `query_points()` and automatically calls `log_retrieval()` with extracted results
- [x] **QDRT-03**: Wrapper intercepts `search()` (deprecated but still used) and automatically calls `log_retrieval()`
- [x] **QDRT-04**: Wrapper returns original Qdrant response objects untouched (no side effects on return values)
- [x] **QDRT-05**: Non-intercepted methods delegate to underlying client via `__getattr__`
- [x] **QDRT-06**: Configurable `payload_id_field` parameter for mapping Qdrant payload to doc_id (default: uses point ID)
- [x] **QDRT-07**: Configurable `payload_filename_key` parameter for extracting filename from payload (default: "filename")
- [x] **QDRT-08**: `AsyncQdrantCorpulseClient` wraps `AsyncQdrantClient` with identical interception behavior
- [x] **QDRT-09**: Async wrapper intercepts async `query_points()` and `search()` methods
- [x] **QDRT-10**: Embeddings captured from response when `with_vectors=True` was passed by caller

### Testing

- [x] **TEST-01**: pytest test suite for existing analytics engine (ghosts, duplicates, obsolete, stale, suspects)
- [x] **TEST-02**: Tests for sync Qdrant wrapper using in-memory QdrantClient
- [x] **TEST-03**: Tests for async Qdrant wrapper using in-memory AsyncQdrantClient
- [x] **TEST-04**: Tests verify wrapper returns unmodified Qdrant response objects

### Bug Fixes

- [x] **FIX-01**: Fix `corpus_health()` calling `get_duplicates()` twice (lines 330-334 in memento.py)
- [x] **FIX-02**: Enable SQLite WAL mode for concurrent write safety

### Documentation

- [x] **DOC-01**: README with installation instructions (GitHub install + optional extras)
- [x] **DOC-02**: README with usage example for manual API (log_retrieval, report)
- [x] **DOC-03**: README with usage example for Qdrant wrapper (sync and async)
- [x] **DOC-04**: Clear scope statement: corpus health tool, not answer quality evaluator
- [x] **DOC-05**: API reference via docstrings on all public methods

### Review Follow-Ups

- [x] **RVW-CH-01**: `corpus_health()` returns the same response keys for empty and populated corpora
- [x] **RVW-CH-02**: `corpus_health().noise_estimate` counts unique noisy documents once even when categories overlap
- [x] **RVW-QD-01**: Sync and async Qdrant wrappers follow the currently installed client's `query_points()` and `search()` behavior without fabricating compatibility
- [x] **RVW-QD-02**: Qdrant wrapper vector capture stores the requested named vector when `with_vectors` specifies one and preserves boolean `with_vectors=True` behavior

## v1.1 Requirements

Requirements for milestone v1.1: Pluggable Storage Backends.

### Abstraction

- [x] **ABS-01**: StorageBackend ABC defines 8 abstract methods matching existing DB interface
- [x] **ABS-02**: TypedDict return types (DocumentRow, RetrievalRow, EngagementRow, EmbeddingRow) shared across all backends
- [x] **ABS-03**: StorageBackendError wraps native DB exceptions at the backend boundary
- [x] **ABS-04**: Shared parametrized test fixture runs against all backend implementations

### Backends

- [x] **BACK-01**: SQLiteBackend refactors existing DB class with zero behavioral change (41 tests pass)
- [x] **BACK-02**: db.py becomes a one-line compat shim importing SQLiteBackend as DB
- [x] **BACK-03**: InMemoryBackend (dict-based, no deps) with full aggregate behavior
- [x] **BACK-04**: PostgresBackend (sync) via psycopg>=3.2 with schema auto-init
- [ ] **BACK-05**: AsyncPostgresBackend via asyncpg>=0.29 with async initialize() and connection pool
- [x] **BACK-06**: All backends implement close() and context manager protocol

### Integration

- [x] **INT-01**: Corpulse(backend=...) accepts explicit backend; defaults to SQLiteBackend when omitted
- [ ] **INT-02**: pyproject.toml extras: [postgres] for psycopg, [postgres-async] for asyncpg
- [ ] **INT-03**: PostgresBackend and AsyncPostgresBackend support connection pooling

## v2 Requirements

### Additional Wrappers

- **WRAP-01**: ChromaDB wrapper with same interception pattern
- **WRAP-02**: Pinecone wrapper
- **WRAP-03**: LangChain callback integration
- **WRAP-04**: LlamaIndex callback integration

### Distribution

- **DIST-01**: PyPI publishing (pip install corpulse)
- **DIST-02**: Changelog and versioning policy

### Features

- **FEAT-01**: CLI tool (memento report ./memento.db)
- **FEAT-02**: Standalone audit mode (crawl vector DB without runtime)
- **FEAT-03**: Batch write buffering for high-throughput pipelines
- **FEAT-04**: Export-to-CSV for BI tools

### Async Facade

- **ASYNC-01**: AsyncCorpulse facade with async analytics methods
- **ASYNC-02**: Native async support without asyncio.to_thread() bridge

### Additional Backends

- **ADDL-01**: MySQL/MariaDB backend
- **ADDL-02**: Schema versioning and migration support

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web dashboard / UI | Destroys zero-infrastructure value prop; use notebooks + to_dataframe() |
| Answer quality / faithfulness metrics | Ragas and DeepEval cover this; splits focus |
| Real-time streaming capture | SQLite lock contention; WAL + batch writes sufficient |
| Automatic engagement inference | High false-positive rate; engagement stays explicit |
| PyPI publishing | GitHub-only until API stabilizes |
| SQLAlchemy/ORM abstraction | Library uses raw SQL by design; ORM adds heavy dependency for 3 tables |
| Schema migration (Alembic) | 3 stable tables; CREATE TABLE IF NOT EXISTS is sufficient |
| AsyncCorpulse facade | Async analytics layer is a separate milestone; v1.1 focuses on storage only |
| MySQL/MariaDB backend | PostgreSQL is the priority for the service repo |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PKG-01 | Phase 1 | Complete |
| PKG-02 | Phase 1 | Complete |
| PKG-03 | Phase 1 | Complete |
| PKG-04 | Phase 1 | Complete |
| PKG-05 | Phase 1 | Complete |
| TEST-01 | Phase 2 | Complete |
| FIX-01 | Phase 2 | Complete |
| FIX-02 | Phase 2 | Complete |
| QDRT-01 | Phase 3 | Complete |
| QDRT-02 | Phase 3 | Complete |
| QDRT-03 | Phase 3 | Complete |
| QDRT-04 | Phase 3 | Complete |
| QDRT-05 | Phase 3 | Complete |
| QDRT-06 | Phase 3 | Complete |
| QDRT-07 | Phase 3 | Complete |
| QDRT-08 | Phase 3 | Complete |
| QDRT-09 | Phase 3 | Complete |
| QDRT-10 | Phase 3 | Complete |
| TEST-02 | Phase 3 | Complete |
| TEST-03 | Phase 3 | Complete |
| TEST-04 | Phase 3 | Complete |
| DOC-01 | Phase 4 | Complete |
| DOC-02 | Phase 4 | Complete |
| DOC-03 | Phase 4 | Complete |
| DOC-04 | Phase 4 | Complete |
| DOC-05 | Phase 4 | Complete |
| RVW-CH-01 | Phase 5 | Complete |
| RVW-CH-02 | Phase 5 | Complete |
| RVW-QD-01 | Phase 5 | Complete |
| RVW-QD-02 | Phase 5 | Complete |
| ABS-01 | Phase 6 | Complete |
| ABS-02 | Phase 6 | Complete |
| ABS-03 | Phase 6 | Complete |
| ABS-04 | Phase 6 | Complete |
| BACK-01 | Phase 6 | Complete |
| BACK-02 | Phase 6 | Complete |
| BACK-03 | Phase 6 | Complete |
| BACK-04 | Phase 9 | Complete |
| BACK-05 | Phase 10 | Pending |
| BACK-06 | Phase 6 | Complete |
| INT-01 | Phase 6 | Complete |
| INT-02 | Phases 7-8 | Pending |
| INT-03 | Phases 9-10 | Pending |

**Coverage:**
- v1 requirements: 30 total (all complete)
- v1.1 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-04-09 after Phase 9 sync-only evidence was narrowed and INT-03 was remapped to pending async verification*
