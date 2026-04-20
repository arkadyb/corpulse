---
phase: 24-generation-trace-capture-foundation
plan: 01
subsystem: storage
tags: [generation-trace, trace-capture, backend-contract, async, sqlite, postgres, testing]
requires:
  - phase: 23-user-acceptance-rate-analytics
    provides: storage backend parity patterns, shared helper conventions, and async facade structure
provides:
  - Typed `GenerationTraceRow` model
  - Additive backend insert/read contract for generation traces
  - Sync and async `log_generation_trace()` / `get_generation_traces()` APIs
  - Append-only trace persistence across SQLite, Postgres, async Postgres, and in-memory backends
affects: [README, backend contract, async facade, trace-capture tests, future generation-metric planning]
tech-stack:
  added: [none]
  patterns: [append-only evaluation trace table, deterministic ordering by captured_at/id, JSON encoding for list fields in SQL backends, sync/async parity on read-only capture APIs]
key-files:
  created:
    - .planning/phases/24-generation-trace-capture-foundation/24-01-SUMMARY.md
    - tests/test_trace_capture.py
  modified:
    - corpulse/models.py
    - corpulse/backends/base.py
    - corpulse/backends/sqlite.py
    - corpulse/backends/postgres.py
    - corpulse/backends/postgres_async.py
    - corpulse/backends/memory.py
    - corpulse/backends/__init__.py
    - corpulse/core.py
    - corpulse/async_core.py
    - README.md
    - tests/conftest.py
    - tests/test_backend_contract.py
    - tests/test_postgres_backend.py
    - tests/test_async_postgres_backend.py
    - tests/test_docstrings.py
requirements-completed: [v1.6-01, v1.6-02, v1.6-03]

# Metrics
duration: 0min
completed: 2026-04-20
---

# Phase 24: Generation trace capture foundation Summary

**Append-only generation-trace storage and sync/async capture APIs, shipped with deterministic backend parity and regression coverage**

## Accomplishments
- Added `GenerationTraceRow` plus additive `insert_generation_trace()` and `generation_traces()` backend methods.
- Implemented append-only trace storage across SQLite, Postgres, async Postgres, and in-memory backends with deterministic ordering.
- Added `log_generation_trace()` and `get_generation_traces()` to both `Corpulse` and `AsyncCorpulse`.
- Documented the capture-only surface in the README and locked behavior with backend, parity, docstring, and regression tests.

## Test Results
- `python -m compileall corpulse tests`
- `pytest tests/test_trace_capture.py tests/test_backend_contract.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_docstrings.py -q`
- `pytest tests/test_analytics.py tests/test_async_core_integration.py tests/test_backend_contract.py tests/test_trace_capture.py tests/test_docstrings.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py -q`
- Result: passed; PostgreSQL live checks were skipped because the required connection environment was not available

## Key Decisions
- Trace records are stored in a separate append-only table so document deletion does not mutate capture history.
- SQL backends serialize `retrieved_context_refs` and `evaluation_labels` explicitly to preserve parity with native Python list storage in memory.
- Ordering is deterministic on `captured_at` plus the backend row id so future generation metrics can consume stable traces.

## Files Changed
- `corpulse/models.py`
- `corpulse/backends/base.py`
- `corpulse/backends/sqlite.py`
- `corpulse/backends/postgres.py`
- `corpulse/backends/postgres_async.py`
- `corpulse/backends/memory.py`
- `corpulse/backends/__init__.py`
- `corpulse/core.py`
- `corpulse/async_core.py`
- `README.md`
- `tests/conftest.py`
- `tests/test_backend_contract.py`
- `tests/test_postgres_backend.py`
- `tests/test_async_postgres_backend.py`
- `tests/test_docstrings.py`
- `tests/test_trace_capture.py`
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`

## Deviations from Plan
- None. The phase stayed capture-only and did not introduce generation scoring.

## Issues Encountered
- None. Live PostgreSQL integration tests were skipped in the default environment, but the targeted regression suite passed.

## Next Phase Readiness
- Phase 24 is complete.
- The v1.6 milestone now has a capture layer ready for future generation-metric work.

---
*Phase: 24-generation-trace-capture-foundation*
*Completed: 2026-04-20*
