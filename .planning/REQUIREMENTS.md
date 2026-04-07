# Requirements: corpulse

**Defined:** 2026-03-24
**Core Value:** RAG teams can point corpulse at their Qdrant instance and immediately understand corpus health — no manual instrumentation

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

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web dashboard / UI | Destroys zero-infrastructure value prop; use notebooks + to_dataframe() |
| Answer quality / faithfulness metrics | Ragas and DeepEval cover this; splits focus |
| Real-time streaming capture | SQLite lock contention; WAL + batch writes sufficient |
| Automatic engagement inference | High false-positive rate; engagement stays explicit |
| Multi-tenancy | SQLite doesn't scale for concurrent multi-tenant writes; one instance per corpus |
| PyPI publishing | GitHub-only for v1 until API stabilizes |

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

**Coverage:**
- v1 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-04-07 after planning-state and dependency cleanup*
