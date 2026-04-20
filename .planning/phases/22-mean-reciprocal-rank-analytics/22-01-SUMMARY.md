---
phase: 22-mean-reciprocal-rank-analytics
plan: 01
subsystem: api
tags: [mrr, analytics, retrieval, async, sqlite, postgres, testing]
requires:
  - phase: 21-low-confidence-zero-result-rate-analytics
    provides: query-level retrieval aggregation and async/sync parity patterns
provides:
  - Proxy `mean_reciprocal_rank()` on `Corpulse` and `AsyncCorpulse`
  - Shared pure helper for document-level MRR from retrieval averages and engagement overlap
  - Backend smoke coverage proving the metric works across all shipped storage backends
affects: [README, analytics API, async facade, backend parity tests, next phase planning]
tech-stack:
  added: [none]
  patterns: [shared pure metric helper, sync/async parity on existing aggregates, deterministic proxy semantics]
key-files:
  created:
    - .planning/phases/22-mean-reciprocal-rank-analytics/22-01-SUMMARY.md
  modified:
    - corpulse/core.py
    - corpulse/async_core.py
    - tests/report_fixtures.py
    - tests/test_analytics.py
    - tests/test_async_core_integration.py
    - tests/test_backend_contract.py
    - README.md
key-decisions:
  - "MRR is a document-level proxy: average reciprocal of each engaged document's average retrieval rank."
  - "Return `0.0` when there is no retrieval/engagement overlap instead of raising or returning None."
  - "Round the public scalar result to 4 decimal places for stable cross-backend parity."
  - "Reuse the same pure helper for sync and async facades to keep semantics aligned."
patterns-established:
  - "Pattern 1: derive new retrieval-quality metrics from existing aggregates instead of adding schema."
  - "Pattern 2: prove parity with one backend smoke test plus higher-level sync/async integration tests."
requirements-completed: [v1.5-01, v1.5-03]

# Metrics
duration: 24min
completed: 2026-04-20
---

# Phase 22: Mean Reciprocal Rank analytics Summary

**Document-level proxy MRR over existing retrieval averages and engagement overlap, shipped with sync/async parity and backend smoke coverage**

## Performance

- **Duration:** 24 min
- **Started:** 2026-04-20T01:02:20Z
- **Completed:** 2026-04-20T01:26:20Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Added `_build_mean_reciprocal_rank()` and public `mean_reciprocal_rank()` methods on both `Corpulse` and `AsyncCorpulse`.
- Locked the Phase 22 proxy semantics in deterministic tests, including the no-overlap `0.0` case.
- Proved parity across the shipped backend matrix and updated the README so the metric is discoverable.

## Task Commits

Each task was committed atomically:

1. **Task 1: Define the sync MRR helper and public method** - `b0e1687` (`feat: add proxy mean reciprocal rank metric`)
2. **Task 2: Add async parity and cross-backend regression coverage** - `ccac631` (`feat: add async MRR parity and docs`)

**Plan metadata:** `825a375` (`docs: plan phase 22 mean reciprocal rank analytics`)

## Files Created/Modified
- `corpulse/core.py` - shared pure MRR helper and sync public method
- `corpulse/async_core.py` - async parity for the same MRR helper
- `tests/report_fixtures.py` - canonical fixture helper for expected MRR
- `tests/test_analytics.py` - sync metric semantics, edge cases, canonical fixture coverage
- `tests/test_async_core_integration.py` - async parity assertion for MRR
- `tests/test_backend_contract.py` - backend smoke test for the metric across shipped backends
- `README.md` - public analytics docs updated to mention MRR

## Decisions Made
- The metric is intentionally a proxy: engaged docs are treated as relevant, and their average retrieval rank is converted into a reciprocal-rank mean.
- Public behavior is `0.0` on no overlap, which keeps the API easy to consume in dashboards and checks.
- The helper rounds to 4 decimal places so sync/async/backend results remain stable.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered
- The backend smoke test initially used stale timestamps and returned `0.0`; freezing `_now` in the test fixed the lookback window and kept the assertion focused on metric semantics.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 22 is complete and ready for Phase 23 planning.
- Phase 23 can reuse the same shared-helper pattern on the existing engagement table without reopening storage concerns.

---
*Phase: 22-mean-reciprocal-rank-analytics*
*Completed: 2026-04-20*
