# Phase 24: Generation trace capture foundation - Research

**Researched:** 2026-04-20
**Domain:** append-only trace capture, backend contract expansion, sync/async facade parity, deterministic record retrieval
**Confidence:** HIGH

## Summary

Phase 24 should follow the same repository pattern used for Phase 21 and Phase 23: add one additive backend contract, implement it in every storage backend, then expose thin sync and async facade methods over the new storage surface. The difference is that this phase is not a metric. It is a capture layer for future generation metrics, so the implementation should stay read-only on retrieval, append-only on write, and isolated from the existing corpus-health analytics.

The lowest-change shape is:
- one typed trace row model in `corpulse/models.py`
- one new backend write method and one read method that returns ordered trace rows
- one append-only table in the SQL backends, with JSON-encoded context reference and label fields
- one in-memory implementation that stores the same Python shape directly
- one sync `log_generation_trace()` / `get_generation_traces()` pair and the same async pair

## User Constraints

- Preserve the existing retrieval and engagement methods unchanged.
- Keep trace capture optional and append-only.
- Capture prompt/query text, retrieved context references, final answer text, and optional evaluation labels.
- Do not add generation scoring in this milestone.
- Do not let trace capture affect corpus-health reporting or the existing analytics methods.

## Key Findings

### Existing architecture already supports the right shape
- The codebase already uses additive backend contracts with typed row models for query and engagement analytics.
- Sync and async facades are intentionally thin wrappers over backend reads and writes.
- SQL backends already standardize on explicit `ORDER BY` clauses when deterministic parity matters.

### There is no trace capture surface yet
- No current table or method captures prompt text, context references, answer text, or evaluation labels.
- No current public API exposes read-only generation-trace records.
- No current tests cover trace capture, so this phase needs fresh contract and parity coverage.

### The safest storage design is a separate append-only table
- Generation traces should not participate in `delete_document()` cleanup.
- Trace records should remain immutable logs even if referenced documents are later removed.
- Keeping trace data in a separate table avoids coupling future evaluation metrics to document lifecycle rules.

## Recommended Implementation Shape

### Contract
- Add `GenerationTraceRow` to `corpulse/models.py`.
- Extend `StorageBackend` with `insert_generation_trace(...)` and `generation_traces(since)`.
- Return rows with deterministic ordering by `captured_at` and an auto-incrementing row id.

### Record fields
- `trace_id`
- `prompt_text`
- `retrieved_context_refs`
- `final_answer_text`
- `evaluation_labels`
- `captured_at`

### Storage details
- SQL backends should store the list fields as JSON text and decode them on read.
- In-memory backend should store native Python lists.
- No foreign keys should be added from traces to documents or analytics tables.

### Facade methods
- Add `log_generation_trace()` on `Corpulse` and `AsyncCorpulse`.
- Add `get_generation_traces(window_days=None)` on `Corpulse` and `AsyncCorpulse`.
- Use the same lookback cutoff helper as the existing analysis methods so the new read path stays consistent.

## Risks and Pitfalls

### Pitfall 1: trace semantics drifting across backends
If SQLite, Postgres, async Postgres, and in-memory backends do not normalize the same list fields the same way, parity tests will become fragile. Use one shared row shape and deterministic ordering everywhere.

### Pitfall 2: accidental coupling to document cleanup
If trace rows are deleted when documents are deleted, the capture layer stops being append-only. Keep trace storage separate and avoid cascade cleanup logic.

### Pitfall 3: leaking trace data into corpus-health features
Trace records are evaluation data, not corpus-health data. They should not affect report output, cleanup output, or existing analytics semantics.

## Validation Strategy

### Test layers
- `tests/test_backend_contract.py` for the frozen backend interface and row shape
- `tests/test_postgres_backend.py` and `tests/test_async_postgres_backend.py` for SQL and tenancy parity
- `tests/test_trace_capture.py` for sync/async facade behavior and record ordering
- `tests/test_docstrings.py` for public API documentation coverage
- `tests/test_analytics.py` as a regression check that existing analytics still behave exactly the same

### Verification focus
- backend contract expansion
- deterministic ordering
- append-only semantics
- sync/async parity
- no regression in existing analytics or report surfaces

## Sources

### Primary
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/PROJECT.md`
- `.planning/STATE.md`
- `corpulse/core.py`
- `corpulse/async_core.py`
- `corpulse/backends/base.py`
- `corpulse/backends/sqlite.py`
- `corpulse/backends/postgres.py`
- `corpulse/backends/postgres_async.py`
- `corpulse/backends/memory.py`
- `corpulse/models.py`
- `tests/test_backend_contract.py`
- `tests/test_postgres_backend.py`
- `tests/test_async_postgres_backend.py`
- `tests/test_async_core_integration.py`
- `tests/test_analytics.py`

## Metadata

- Research date: 2026-04-20
- Valid until: next phase boundary change
