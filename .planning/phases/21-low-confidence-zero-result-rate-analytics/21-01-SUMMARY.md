---
phase: 21-low-confidence-zero-result-rate-analytics
plan: 01
subsystem: database
tags: [sqlite, postgres, asyncpg, pytest, typedict]

# Dependency graph
requires:
  - phase: 16-03
    provides: postgres tenancy via schema/table-prefix validation that the new aggregate SQL paths must preserve
  - phase: 20-01
    provides: async/backend parity patterns that informed the mirrored sync and async aggregate implementations
provides:
  - stable backend-level query aggregation contract keyed by `query_hash`
  - typed query aggregate rows with count, rank/score stats, and retrieval-window timestamps
  - aligned query aggregation implementations across SQLite, Postgres, async Postgres, and in-memory backends
affects: [phase 21-02, low-confidence analytics, zero-result analytics]

# Tech tracking
tech-stack:
  added: []
  patterns: [read-only derived query aggregates, deterministic query_hash ordering, symmetric sync/async backend surface]

key-files:
  created: []
  modified: [corpulse/backends/base.py, corpulse/backends/sqlite.py, corpulse/backends/postgres.py, corpulse/backends/postgres_async.py, corpulse/backends/memory.py, corpulse/models.py, tests/test_backend_contract.py, tests/test_postgres_backend.py, tests/test_async_postgres_backend.py]

key-decisions:
  - "Query aggregates are keyed only by `query_hash` and expose aggregate stats, not raw query text."
  - "The aggregate row shape includes count, average/min/max rank and score, plus first/last retrieval timestamps for downstream analytics."
  - "Query aggregate SQL is ordered by `query_hash` to keep sync and async backend parity deterministic."

patterns-established:
  - "Pattern 1: extend the storage contract first, then mirror the same aggregate semantics across every concrete backend."
  - "Pattern 2: keep query analytics read-only and derived only from persisted retrieval rows."
  - "Pattern 3: keep backend tests aligned with tenant-qualified SQL so schema and table-prefix modes stay covered."

requirements-completed: [v1.4-02, v1.4-03]

# Metrics
duration: 4min
completed: 2026-04-19
---

# Phase 21: Low-Confidence / Zero-Result Rate analytics Summary

Query-level retrieval aggregation now exists in the storage layer, with the same hashed-query aggregate surface implemented across SQLite, Postgres, async Postgres, and in-memory backends.

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-19T06:49:17Z
- **Completed:** 2026-04-19T06:53:30Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added a typed `QueryRow` contract and a new `StorageBackend.query_counts()` method.
- Implemented query aggregation across all storage backends using persisted retrieval rows only.
- Locked backend parity with contract tests and tenant-aware SQL tests for schema and prefix modes.

## Task Commits

Each task was committed atomically:

1. **Task 1: Define the query aggregate contract and typed row shape** - `1f8f4cf` (feat)
2. **Task 2: Implement query aggregation across all backends** - `12a248a` (feat)

## Files Created/Modified

- `corpulse/backends/base.py` - Added the `query_counts()` abstract contract.
- `corpulse/models.py` - Added the typed `QueryRow` aggregate shape.
- `corpulse/backends/sqlite.py` - Implemented grouped query aggregation for SQLite.
- `corpulse/backends/postgres.py` - Implemented grouped query aggregation for sync Postgres.
- `corpulse/backends/postgres_async.py` - Implemented grouped query aggregation for async Postgres.
- `corpulse/backends/memory.py` - Implemented grouped query aggregation for the in-memory backend.
- `tests/test_backend_contract.py` - Froze the new backend contract and query aggregate semantics.
- `tests/test_postgres_backend.py` - Covered tenant-aware query aggregation in sync Postgres tests.
- `tests/test_async_postgres_backend.py` - Covered tenant-aware query aggregation in async Postgres tests.

## Decisions Made

- Query aggregates are exposed by hashed query identifier only, with no raw query text in the contract.
- The row shape exposes enough grouped retrieval statistics for downstream low-confidence analysis without any schema changes.
- Deterministic `ORDER BY query_hash` is part of the backend SQL surface to keep sync and async parity stable.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed async live-test indentation after adding query aggregate coverage**
- **Found during:** Task 2 (Implement query aggregation across all backends)
- **Issue:** The initial async test patch introduced a syntax/indentation error in `tests/test_async_postgres_backend.py`.
- **Fix:** Reindented the live round-trip assertions inside the `try` block and reran the backend test set.
- **Files modified:** `tests/test_async_postgres_backend.py`
- **Verification:** `pytest tests/test_backend_contract.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py`
- **Committed in:** `12a248a` (part of task commit)

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** No scope creep. The fix was necessary to restore a valid test module and complete the planned backend coverage.

## Issues Encountered

- No blocking issues. The only issue was the async test indentation error introduced during patching, which was fixed immediately.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Storage contract and backend parity are in place for the next analytics plan.
- Phase 21-02 can build low-confidence and zero-result analytics directly on the new query aggregate surface.

## Self-Check: PASSED
