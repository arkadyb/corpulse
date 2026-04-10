# Requirements: corpulse — Milestone v1.2 Full Async Parity

**Defined:** 2026-04-10
**Core Value:** RAG teams can point corpulse at their vector DB and immediately understand corpus health without manual audits.
**Milestone goal:** Close the remaining gap between `AsyncCorpulse` and sync `Corpulse` so the async path is a fully at-par, documented, first-class surface for service integration.

## v1.2 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Async Parity Methods

- [ ] **ASYNC-PAR-01**: `AsyncCorpulse.to_dataframe(window_days)` returns a pandas DataFrame with the same columns (`doc_id`, `filename`, `retrievals`, `engagements`, `engagement_rate`, `status`), row ordering, and status classification as sync `Corpulse.to_dataframe()`; raises `RuntimeError` with a clear install hint if pandas is unavailable.
- [ ] **ASYNC-PAR-02**: `AsyncCorpulse.report(window_days)` returns a structured payload (dict) containing the same corpus-health summary, top-K document rows, status classification, and totals that sync `Corpulse.report()` prints — but returns rather than prints.
- [ ] **ASYNC-PAR-03**: `AsyncCorpulse.cleanup_report()` returns a structured payload (dict) containing the same prioritised sections (ghosts, obsolete, stale embeddings, re-chunk suspects) with counts, top-5 examples, and header metadata that sync `Corpulse.cleanup_report()` prints — but returns rather than prints.

### Shared Report Helpers

- [x] **REPORT-HELPERS-01**: Structured-payload builder helpers for the report table (`to_dataframe` rows) and the cleanup-report sections are factored into `corpulse/core.py` so sync and async paths compute the same output from the same code path.
- [x] **REPORT-HELPERS-02**: Sync `Corpulse.report()` and `Corpulse.cleanup_report()` are refactored to consume the shared structured payloads via a thin stdout formatter; their printed output and public signatures remain unchanged (backwards-compatible).

### Testing

- [ ] **ASYNC-TEST-01**: Deterministic async unit tests prove `AsyncCorpulse.to_dataframe()` parity against sync for an identical backend fixture (same rows, same ordering, same status columns).
- [ ] **ASYNC-TEST-02**: Deterministic async unit tests prove `AsyncCorpulse.report()` and `AsyncCorpulse.cleanup_report()` return payloads equivalent to the structured data underlying sync output for the same backend fixture.
- [ ] **ASYNC-TEST-03**: Live asyncpg integration tests (gated by `CORPULSE_POSTGRES_TEST_CONNINFO`) exercise `to_dataframe`, `report`, and `cleanup_report` end-to-end against a real Postgres instance.

### Documentation & Examples

- [ ] **ASYNC-DOC-01**: README gains a first-class "Async usage" section showing `AsyncCorpulse` over `AsyncPostgresBackend`, including ingestion, analysis, and the new structured report methods.
- [ ] **ASYNC-DOC-02**: Docstrings on all new `AsyncCorpulse` methods meet API-reference quality (args, returns, raises, parity notes vs sync).
- [ ] **ASYNC-DOC-03**: `examples/` contains a runnable async script demonstrating ingest → analysis → report end-to-end against `InMemoryBackend` (or an async Postgres instance if `CORPULSE_POSTGRES_TEST_CONNINFO` is set).

## Future Requirements

Deferred beyond v1.2. Tracked but not in this milestone.

### Integrations

- **INT-01**: ChromaDB wrapper
- **INT-02**: Pinecone wrapper
- **INT-03**: LangChain / LlamaIndex plugin

### Distribution

- **DIST-01**: PyPI publishing

### Async API evolution

- **ASYNC-FUT-01**: Async-aware top-level helpers or a unified facade that can span sync and async backends

## Out of Scope

Explicitly excluded from v1.2. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Changes to sync `Corpulse` public API or printed output | v1.2 is additive; backwards compat is a hard constraint |
| Making pandas a required dependency | Install footprint decision locked — pandas remains an optional extra |
| Stdout-coupling the async `report()` / `cleanup_report()` methods | Structured-return decision avoids coupling async API to stdout (see Key Decisions in PROJECT.md) |
| New backend implementations | Backend work shipped in v1.1; this milestone is parity above the backend layer |
| Service-repo / REST API work | Belongs to the separate service repo, not the library |
| Web dashboard / UI | Out of scope per PROJECT.md (library-first) |
| CLI tool | Deferred per PROJECT.md |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ASYNC-PAR-01 | Phase 12 | Pending |
| ASYNC-PAR-02 | Phase 12 | Pending |
| ASYNC-PAR-03 | Phase 12 | Pending |
| REPORT-HELPERS-01 | Phase 11 | Complete |
| REPORT-HELPERS-02 | Phase 11 | Complete |
| ASYNC-TEST-01 | Phase 12 | Pending |
| ASYNC-TEST-02 | Phase 12 | Pending |
| ASYNC-TEST-03 | Phase 13 | Pending |
| ASYNC-DOC-01 | Phase 14 | Pending |
| ASYNC-DOC-02 | Phase 14 | Pending |
| ASYNC-DOC-03 | Phase 14 | Pending |

**Coverage:**
- v1.2 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-10*
*Last updated: 2026-04-10 — traceability filled in after roadmap creation*
