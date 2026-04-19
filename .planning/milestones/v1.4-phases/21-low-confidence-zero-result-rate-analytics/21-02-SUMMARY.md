---
phase: 21-low-confidence-zero-result-rate-analytics
plan: 02
subsystem: api
tags: [typedict, analytics, async, pytest]

# Dependency graph
requires:
  - phase: 21-01
    provides: backend query aggregation contract keyed by `query_hash`
provides:
  - sync low-confidence summary and detail analytics
  - sync zero-result summary and detail analytics
  - async parity for the same read-only analytics surface
affects: [v1.4 analytics consumers, phase 21 follow-on work]

# Tech tracking
tech-stack:
  added: []
  patterns: [query-aggregate-backed analytics, thin facade over pure result builders, sync/async parity]

key-files:
  created: [.planning/phases/21-low-confidence-zero-result-rate-analytics/21-02-SUMMARY.md]
  modified: [corpulse/core.py, corpulse/async_core.py, corpulse/models.py, tests/test_analytics.py, tests/test_async_core_integration.py]

key-decisions:
  - "Low-confidence analytics use the backend `query_counts()` surface and filter positive query aggregates by a configurable top-score threshold."
  - "Zero-result analytics stay separate from low-confidence analytics and only surface aggregates whose `cnt` is zero."
  - "The default low-confidence threshold is configurable on `Corpulse` and `AsyncCorpulse`, with 0.8 as the default cutoff."

patterns-established:
  - "Pattern 1: keep query analytics in pure builders so sync and async facades stay thin."
  - "Pattern 2: model read-only query analytics with lightweight TypedDict rows that match existing corpulse conventions."
  - "Pattern 3: keep zero-result analytics distinct from low-confidence analytics in both the code and tests."

requirements-completed: [v1.4-01, v1.4-02]

# Metrics
duration: 4min
completed: 2026-04-19
---

# Phase 21: Low-Confidence / Zero-Result Rate analytics Summary

Query-level retrieval analytics now expose a public sync and async API for low-confidence and zero-result signals, built directly on the backend query aggregate surface from Wave 1.

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-19T06:54:45Z
- **Completed:** 2026-04-19T06:58:45Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added low-confidence summary and detail methods to `Corpulse` using `query_counts()` and a configurable top-score threshold.
- Added separate zero-result summary and detail methods that stay distinct from low-confidence analytics.
- Mirrored the same read-only semantics in `AsyncCorpulse` and verified sync/async parity with fixture-backed tests.
- Kept `report()` and `cleanup_report()` behavior unchanged and regression-tested the existing helpers.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add sync analytics helpers and public methods** - `5460652` (feat)
2. **Task 2: Add async parity and cross-surface verification** - `7855a94` (feat)

## Files Created/Modified

- `corpulse/core.py` - Added shared query-analytics builders and the public sync low-confidence / zero-result methods.
- `corpulse/async_core.py` - Added async parity for the new query analytics surface.
- `corpulse/models.py` - Added TypedDicts for the new read-only query analytics rows.
- `tests/test_analytics.py` - Added sync tests covering low-confidence and zero-result semantics.
- `tests/test_async_core_integration.py` - Added async parity tests for the new analytics surface.

## Decisions Made

- Low-confidence queries are defined by the query aggregate `max_score` falling below a configurable threshold, not by average score.
- Zero-result analytics remain a separate signal and only match query aggregates with `cnt == 0`.
- The default low-confidence threshold is `0.8`, but callers can override it per call.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 21 now has the public query analytics surface needed for downstream low-confidence / zero-result consumers.
- Backend query aggregation parity from Wave 1 is fully consumed by the sync and async facades.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/21-low-confidence-zero-result-rate-analytics/21-02-SUMMARY.md`.
- Task commit `5460652` exists in git history.
- Task commit `7855a94` exists in git history.
