# Phase 27 Pattern Map

## Purpose

Phase 27 writes a planning artifact, but the artifact must be grounded in existing source patterns so downstream implementation phases do not guess.

## Closest Existing Patterns

| Target Concept | Existing Analog | Pattern to Preserve |
|----------------|-----------------|---------------------|
| Workload trace row model | `corpulse/models.py` `GenerationTraceRow` | Add typed row payloads as `TypedDict` models when implementation begins. |
| Append-only trace storage | `StorageBackend.insert_generation_trace()` and `generation_traces()` | Add explicit backend interface methods rather than hidden DB-specific helpers. |
| SQLite schema evolution | `corpulse/backends/sqlite.py` `SCHEMA` | Store JSON payloads as `TEXT` and decode at read boundaries. |
| Postgres schema evolution | `corpulse/backends/postgres.py` `build_schema_sql()` | Use tenant-safe `_qualified_name()` and `_index_name()` for all new tables/indexes. |
| Async parity | `corpulse/async_core.py` `log_generation_trace()` | Mirror sync API names and backend call shapes on `AsyncCorpulse`. |
| In-memory test backend | `corpulse/backends/memory.py` `_generation_traces` | Use lists of dicts for append-only events and sort deterministically on read. |
| Contract tests | `tests/test_trace_capture.py` | Validate append-only behavior, ordering, sync/async parity, and backend calls. |

## Files Phase 27 Executor Should Read

- `.planning/research/RAGPULSE-COMPARISON-FEATURES.md`
- `.planning/research/SUMMARY.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/phases/27-workload-trace-feasibility-and-schema-contract/27-RESEARCH.md`
- `corpulse/models.py`
- `corpulse/backends/base.py`
- `corpulse/backends/sqlite.py`
- `corpulse/backends/postgres.py`
- `corpulse/backends/postgres_async.py`
- `corpulse/backends/memory.py`
- `corpulse/core.py`
- `corpulse/async_core.py`
- `tests/test_trace_capture.py`

## Implementation Guidance for Later Phases

- Prefer an append-only `rag_request_traces` table for the first implementation unless Phase 27 finds a hard analytics blocker.
- Keep component details and timing details JSON-encoded for the MVP to reduce schema churn.
- Document a stable JSONL export shape before adding replay behavior.
- Preserve existing generation trace APIs; workload traces are additive.
