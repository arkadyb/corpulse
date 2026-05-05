# Phase 28 Pattern Map

## Closest Existing Patterns

| New Work | Existing Analog | Files |
|----------|-----------------|-------|
| Workload trace row models | Generation trace row model | `corpulse/models.py` |
| Backend write/read methods | `insert_generation_trace()` / `generation_traces()` | `corpulse/backends/base.py`, `corpulse/backends/*` |
| SQLite table and JSON decode | `generation_traces` table | `corpulse/backends/sqlite.py` |
| Postgres tenant-safe schema | `build_schema_sql()` table generation | `corpulse/backends/postgres.py` |
| Async Postgres parity | async backend method mirrors sync backend | `corpulse/backends/postgres_async.py` |
| In-memory append-only storage | `_generation_traces` list | `corpulse/backends/memory.py` |
| Sync facade | `Corpulse.log_generation_trace()` | `corpulse/core.py` |
| Async facade | `AsyncCorpulse.log_generation_trace()` | `corpulse/async_core.py` |
| Sync/async parity tests | `tests/test_trace_capture.py` | `tests/test_trace_capture.py` |

## Files To Modify

- `corpulse/models.py`
- `corpulse/backends/base.py`
- `corpulse/backends/memory.py`
- `corpulse/backends/sqlite.py`
- `corpulse/backends/postgres.py`
- `corpulse/backends/postgres_async.py`
- `corpulse/core.py`
- `corpulse/async_core.py`
- `tests/test_trace_capture.py`
- `tests/test_backend_contract.py`
- `tests/test_postgres_backend.py`
- `tests/test_async_postgres_backend.py`
- `README.md`

## Source Taxonomy

Use these values exactly:

- `system_prompt`
- `vector_db`
- `chat_history`
- `web_search`
- `user_input`
- `file_attachment`
- `tool_result`
- `other`

## MVP Schema Fields

Use these row keys exactly:

- `trace_id`
- `request_id`
- `session_id`
- `query_text`
- `query_hash`
- `input_token_count`
- `output_token_count`
- `components`
- `timings`
- `timeout`
- `error`
- `captured_at`
