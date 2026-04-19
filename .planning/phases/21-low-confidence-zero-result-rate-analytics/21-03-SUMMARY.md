---
phase: 21-low-confidence-zero-result-rate-analytics
plan: 03
subsystem: api
tags: [analytics, qdrant, sqlite, postgres, async, pytest, typedict]

# Dependency graph
requires:
  - phase: 21-01
    provides: backend query aggregate contract keyed by `query_hash`
  - phase: 21-02
    provides: sync/async analytics facades and typed query rows
provides:
  - durable query-attempt storage for empty-result searches
  - zero-result analytics driven by `query_attempt_counts()`
  - sync/async parity and live wrapper coverage for empty attempts
affects: [phase 21 follow-on analytics, qdrant integration, backend contract]

# Tech tracking
tech-stack:
  added: []
  patterns: [durable query-attempt aggregate, separate retrieval vs attempt analytics, wrapper logs empty attempts through existing ingestion path, sync/async parity over read-only TypedDict payloads]

key-files:
  created: [.planning/phases/21-low-confidence-zero-result-rate-analytics/21-03-SUMMARY.md]
  modified: [corpulse/backends/base.py, corpulse/backends/sqlite.py, corpulse/backends/postgres.py, corpulse/backends/postgres_async.py, corpulse/backends/memory.py, corpulse/backends/__init__.py, corpulse/integrations/qdrant.py, corpulse/core.py, corpulse/async_core.py, corpulse/models.py, tests/conftest.py, tests/test_backend_contract.py, tests/test_postgres_backend.py, tests/test_async_postgres_backend.py, tests/test_qdrant_wrapper.py, tests/test_analytics.py, tests/test_async_core_integration.py, tests/test_core_backend_integration.py]

key-decisions:
  - "Persist zero-result usage in a dedicated query_attempts table instead of overloading retrieval rows."
  - "Keep low-confidence analytics on retrieval aggregates and zero-result analytics on attempt aggregates."
  - "Record query attempts once per `log_retrieval()` call so wrappers and manual logging stay in sync."

patterns-established:
  - "Pattern 1: write the durable query-attempt signal first, then derive zero-result analytics from that read-only surface."
  - "Pattern 2: keep retrieval-derived low-confidence analytics unchanged so existing score-based behavior stays stable."
  - "Pattern 3: treat empty wrapper responses as analytics-bearing events, not no-ops."

requirements-completed: [v1.4-02, v1.4-03]

# Metrics
duration: 8min
completed: 2026-04-19
---

# Phase 21 Plan 03: Low-Confidence / Zero-Result Rate analytics Summary

Durable query-attempt logging now backs zero-result analytics while low-confidence stays on the existing retrieval aggregate surface.

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-19T07:05:58Z
- **Completed:** 2026-04-19T07:14:12Z
- **Tasks:** 2
- **Files modified:** 18

## Accomplishments

- Added a durable `query_attempts` storage surface across SQLite, Postgres, async Postgres, and in-memory backends.
- Reworked zero-result analytics to consume query-attempt aggregates while keeping low-confidence analytics on retrieval aggregates.
- Proved the live path in both wrapper and manual logging flows by persisting empty query attempts exactly once.
- Preserved sync/async parity and the read-only TypedDict payload style used throughout the phase.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add a durable query-attempt signal to the storage and wrapper layers** - `a8c7ad3` (feat)
2. **Task 2: Rebase zero-result analytics on the durable signal and prove live-path parity** - `74b1741` (feat)

## Files Created/Modified

- `corpulse/backends/base.py` - Added the query-attempt contract to the storage interface.
- `corpulse/backends/sqlite.py` - Persisted and aggregated query attempts in SQLite.
- `corpulse/backends/postgres.py` - Added the Postgres query-attempt table and aggregate query.
- `corpulse/backends/postgres_async.py` - Mirrored the async Postgres query-attempt surface.
- `corpulse/backends/memory.py` - Added in-memory query-attempt persistence and aggregation.
- `corpulse/backends/__init__.py` - Re-exported the new backend row type.
- `corpulse/integrations/qdrant.py` - Logged empty Qdrant query attempts on both sync and async paths.
- `corpulse/core.py` - Rebased zero-result analytics onto the durable attempt aggregate.
- `corpulse/async_core.py` - Mirrored the zero-result attempt aggregate in async parity.
- `corpulse/models.py` - Added the typed query-attempt row shape.
- `tests/conftest.py` - Cleared the new query-attempt table in live backend fixtures.
- `tests/test_backend_contract.py` - Locked the new storage contract and row shape.
- `tests/test_postgres_backend.py` - Covered query-attempt SQL and live backend parity.
- `tests/test_async_postgres_backend.py` - Covered async query-attempt SQL and live backend parity.
- `tests/test_qdrant_wrapper.py` - Proved empty wrapper searches still persist a live attempt.
- `tests/test_analytics.py` - Proved manual empty logging moves zero-result analytics.
- `tests/test_async_core_integration.py` - Locked async parity for both retrieval and attempt aggregates.
- `tests/test_core_backend_integration.py` - Updated live Postgres cleanup to include query attempts.

## Decisions Made

- Use a dedicated `query_attempts` table so zero-result analytics are truthful without polluting retrieval aggregates.
- Keep low-confidence analytics on the existing retrieval aggregate surface to avoid regressions.
- Record the attempt row in `log_retrieval()` before any retrieval inserts so empty searches are durable and first-class.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added a durable query-attempt storage path for zero-result analytics**
- **Found during:** Task 1 (Add a durable query-attempt signal to the storage and wrapper layers)
- **Issue:** Zero-result analytics had no live stored signal because empty retrieval attempts were skipped entirely.
- **Fix:** Added a `query_attempts` table plus `insert_query_attempt()` / `query_attempt_counts()` across all backends, and made Qdrant wrappers call `log_retrieval()` even on empty responses.
- **Files modified:** `corpulse/backends/base.py`, `corpulse/backends/sqlite.py`, `corpulse/backends/postgres.py`, `corpulse/backends/postgres_async.py`, `corpulse/backends/memory.py`, `corpulse/integrations/qdrant.py`, `tests/test_backend_contract.py`, `tests/test_postgres_backend.py`, `tests/test_async_postgres_backend.py`, `tests/test_qdrant_wrapper.py`, `tests/conftest.py`, `tests/test_core_backend_integration.py`
- **Verification:** `pytest -q tests/test_backend_contract.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_qdrant_wrapper.py tests/test_analytics.py tests/test_async_core_integration.py tests/test_core_backend_integration.py`
- **Committed in:** `a8c7ad3` (part of task commit)

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Necessary to make zero-result analytics reflect live usage. No unrelated behavior changes.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Zero-result analytics are now grounded in live stored query attempts.
- Low-confidence analytics remain on the retrieval aggregate and still pass parity tests.
- Phase 21 can continue with the remaining milestone analytics work.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/21-low-confidence-zero-result-rate-analytics/21-03-SUMMARY.md`.
- Task commit `a8c7ad3` exists in git history.
- Task commit `74b1741` exists in git history.
