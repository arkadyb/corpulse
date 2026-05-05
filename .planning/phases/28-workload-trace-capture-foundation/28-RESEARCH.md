# Phase 28 Research: Workload Trace Capture Foundation

## RESEARCH COMPLETE

**Phase:** 28 - Workload Trace Capture Foundation
**Date:** 2026-05-02
**Requirements:** TRACE-01, TRACE-02, TRACE-03, TRACE-04

## Phase Boundary

Phase 28 implements the capture foundation selected in Phase 27:

- append-only `rag_request_traces` storage
- sync `Corpulse.log_rag_request()`
- async `AsyncCorpulse.alog_rag_request()`
- structured prompt/context components
- optional timing, timeout, and error fields
- backend contract coverage across in-memory, SQLite, Postgres, and async Postgres

Phase 28 does not implement workload reports, JSONL import/export, sessions analytics, or replay. Those are later phases.

## Key Source Patterns

### Models

`corpulse/models.py` uses `TypedDict` models for backend rows and public payloads. Workload traces should add:

- `RagRequestComponent`
- `RagRequestTimings`
- `RagRequestTraceRow`

The source taxonomy should be explicit and documented in code/docs as string values:

- `system_prompt`
- `vector_db`
- `chat_history`
- `web_search`
- `user_input`
- `file_attachment`
- `tool_result`
- `other`

### Backend Contract

`corpulse/backends/base.py` is the source of truth for storage methods. Add explicit abstract methods rather than a generic metadata sink:

- `insert_rag_request_trace(...)`
- `rag_request_traces(since: float) -> list[RagRequestTraceRow]`

### Append-Only Storage

Generation trace capture is the closest analog:

- SQLite stores JSON as text and decodes at read time.
- Postgres schema is generated through `build_schema_sql()`.
- Async Postgres should mirror sync Postgres.
- In-memory storage should copy nested structures and return deterministic ordering by `(captured_at, trace_id)`.

### Public API Shape

`Corpulse.log_generation_trace()` and `AsyncCorpulse.log_generation_trace()` show the expected sync/async facade style. Phase 28 should add:

- `Corpulse.log_rag_request(...)`
- `Corpulse.get_rag_request_traces(...)`
- `AsyncCorpulse.alog_rag_request(...)`
- `AsyncCorpulse.get_rag_request_traces(...)`

Use `_hash_query(query)` when query text is present. Preserve raw query as optional because the privacy model allows hash/reference-only operation.

## Implementation Risks

- Adding abstract backend methods requires all concrete backends and test fakes to be updated.
- Postgres multi-tenancy must preserve schema and table-prefix handling.
- Async fake backends in tests may need methods added when `AsyncCorpulse` gets new API calls.
- Timing fields are optional and should not conflate missing values with zero.
- Existing generation trace tests must keep passing unchanged.

## Validation Architecture

Phase 28 should be validated by:

1. Focused workload trace tests.
2. Existing trace capture tests.
3. Backend contract tests.
4. Import/package tests.
5. Optional Postgres SQL builder tests if live Postgres is unavailable.

Recommended commands:

```bash
pytest tests/test_trace_capture.py tests/test_backend_contract.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_import.py
```

If live Postgres environment variables are unavailable, Postgres integration tests may skip; the plan should still validate SQL builders and non-live contract behavior.

## Recommended Plan Split

1. Model, storage contract, and in-memory behavior.
2. SQLite/Postgres/async Postgres durable backend implementation.
3. Sync/async public APIs and parity tests.
4. Compatibility/docs verification for current APIs and user-facing guidance.
