---
phase: 28
phase_slug: workload-trace-capture-foundation
created: 2026-05-02
---

# Validation Strategy: Phase 28

## Required Behavior

- `Corpulse.log_rag_request()` stores request traces with timestamp, session ID, query, output token count, components, timings, timeout, and error state.
- `AsyncCorpulse.alog_rag_request()` stores the same shape through async backends.
- Components support source taxonomy values, token counts, refs, and content hashes.
- In-memory, SQLite, Postgres, and async Postgres backends implement the same storage contract.
- Existing retrieval, engagement, generation trace, report, cleanup, wrapper, and import behavior remains compatible.

## Required Tests

- In-memory round trip and ordering for workload traces.
- SQLite round trip and JSON decoding for workload traces.
- Sync/async API parity for workload trace capture.
- Backend contract updates.
- Existing generation trace tests unchanged.
- Package import test unchanged.

## Verification Commands

```bash
pytest tests/test_trace_capture.py
pytest tests/test_backend_contract.py
pytest tests/test_postgres_backend.py tests/test_async_postgres_backend.py
pytest tests/test_import.py tests/test_package.py
```

## Acceptance Signals

- `rg "class RagRequestTraceRow" corpulse/models.py` exits 0.
- `rg "def insert_rag_request_trace|def rag_request_traces" corpulse/backends/base.py` exits 0.
- `rg "CREATE TABLE IF NOT EXISTS rag_request_traces" corpulse/backends/sqlite.py corpulse/backends/postgres.py` exits 0.
- `rg "def log_rag_request|async def alog_rag_request" corpulse/core.py corpulse/async_core.py` exits 0.
- `rg "system_prompt|vector_db|chat_history|web_search|user_input|file_attachment|tool_result|other" corpulse tests README.md` exits 0.
