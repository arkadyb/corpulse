# Phase 27 Research: Workload Trace Feasibility and Schema Contract

## RESEARCH COMPLETE

**Phase:** 27 - Workload Trace Feasibility and Schema Contract
**Date:** 2026-05-02
**Requirements:** FEAS-01, FEAS-02

## Question

What does the executor need to know to plan Phase 27 well?

Phase 27 is a decision-record phase. It should not implement workload trace storage or public APIs yet. It must create a concrete feasibility artifact that downstream phases can treat as the source of truth for schema, scope, and deferrals.

## Source Findings

### RAGPulse Comparison

`.planning/research/RAGPULSE-COMPARISON-FEATURES.md` identifies the core gap as workload observability and replay, not corpus-health analytics. The relevant capabilities are:

- Workload trace schema with timestamp, input/output lengths, session identity, and prompt component references.
- Serving latency metrics such as TTFT and TPOT.
- Replay/export using timestamp scaling and benchmarkable JSONL traces.
- Traffic shape analytics for throughput, burst windows, token distributions, and component proportions.
- Prompt component breakdown for system prompt, vector DB passages, chat history, web search, and user input.
- Session analytics and repeated context/source reuse.
- External context taxonomy beyond local vector DB passages.
- Cacheability and optimization reports as later advanced signals.

### Existing corpulse Architecture

The current source layout gives Phase 27 clear implementation constraints:

- `corpulse/models.py` defines API/backend row payloads as `TypedDict` classes.
- `corpulse/backends/base.py` is the synchronous `StorageBackend` contract; every durable feature needs explicit backend methods.
- `corpulse/backends/sqlite.py` owns the SQLite schema string and SQL implementations.
- `corpulse/backends/postgres.py` builds Postgres schema SQL through `build_schema_sql(schema, prefix)`, preserving tenant schema/table-prefix support.
- `corpulse/backends/postgres_async.py` mirrors sync Postgres behavior.
- `corpulse/backends/memory.py` is the lightweight test/backend contract implementation.
- `corpulse/core.py` exposes sync public APIs and pure report helper functions.
- `corpulse/async_core.py` exposes async parity for service integrations.
- `tests/test_trace_capture.py` shows the generation trace pattern: append-only storage, sync/async parity, deterministic ordering, and backend-call assertions.

## Feasibility Considerations

### Schema Shape

The safest MVP is one append-only workload request table plus JSON-encoded component/timing fields:

- `id` / `trace_id`
- `request_id` optional external identifier
- `session_id` optional conversation/session identifier
- `query_text` optional raw query
- `query_hash` derived from query text when present
- `input_token_count`
- `output_token_count`
- `components` JSON list of `{type, token_count, refs, content_hash, metadata}`
- `timings` JSON object for optional stage latencies
- `timeout` boolean
- `error` optional string/code
- `captured_at` unix timestamp

This keeps the first implementation close to generation traces while leaving analytic indexes to later phases if reports show they are needed. The decision record should explicitly compare this against a normalized multi-table schema and explain why MVP storage starts append-only.

### Privacy Boundary

Phase 27 should require downstream trace capture to work without raw prompt/context/answer text. Raw text may be optional, but the schema should be useful with:

- `query_hash`
- component `content_hash`
- component `refs`
- token counts
- source taxonomy values
- timing/error/session metadata

### Backend Compatibility

Any selected schema must account for:

- SQLite file-backed storage with JSON serialized as `TEXT`.
- Postgres and async Postgres with tenant-safe table names through `build_schema_sql()`.
- In-memory backend for fast contract tests.
- Existing optional dependency behavior: no new mandatory model-client package for replay feasibility.

### API Boundary

The feasibility record should specify only the intended downstream surface, not implement it:

- `Corpulse.log_rag_request(...)`
- `AsyncCorpulse.alog_rag_request(...)`
- `workload_traces(...)` or equivalent backend read method
- JSONL export/import in a later phase
- Replay prototype only after export is stable

### Deferral Guidance

Likely implement now:

- Trace schema and durable capture.
- Component taxonomy.
- JSONL import/export.
- Workload and serving summary reports.
- Session analytics.

Likely defer:

- Full serving benchmark suite.
- Endpoint-specific OpenAI-compatible replay client.
- Cacheability recommendations.
- Framework-specific plugins.
- UI/dashboard surfaces.

## Validation Architecture

Phase 27 is verified by artifact checks rather than unit tests:

1. `.planning/phases/27-workload-trace-feasibility-and-schema-contract/27-FEASIBILITY.md` exists.
2. The feasibility document contains sections titled `## Schema Options`, `## Recommended MVP Schema`, `## Backend Compatibility`, `## Privacy Model`, `## Capability Classification`, and `## Replay Gate`.
3. The document names all required backend/API surfaces: `StorageBackend`, `SQLiteBackend`, `PostgresBackend`, `AsyncPostgresBackend`, `InMemoryBackend`, `Corpulse.log_rag_request()`, and `AsyncCorpulse.alog_rag_request()`.
4. The capability classification lists at least one `Implement Now`, `Defer`, and `Reject` or `Out of Scope` item.
5. The recommended MVP schema includes session identity, request identity, prompt components, token counts, timings, error/timeout state, and export semantics.
6. The replay gate states whether Phase 32 should implement only design, a callable-only proof, or a broader endpoint replay prototype.

## Planning Recommendation

Use one executable plan:

- Plan 27-01 creates the feasibility and schema decision record.
- It reads the roadmap, requirements, RAGPulse comparison, research summary, existing trace/storage files, and this research file.
- It does not modify source code.
- It updates `STATE.md` and, if needed, planning docs to reflect approved/deferred/rejected capabilities after the decision record is written.
