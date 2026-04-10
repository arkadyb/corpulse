---
phase: 12-async-parity-methods-unit-tests
plan: 01
subsystem: testing
tags: [async, pandas, parity, pytest, fixtures]
requires:
  - phase: 11-shared-report-helpers
    provides: Shared dataframe row helpers and frozen sync report expectations
provides:
  - Shared deterministic report fixtures consumed by sync and async tests
  - Async dataframe parity coverage against the sync Corpulse surface
  - AsyncCorpulse.to_dataframe with sync-matching pandas guard semantics
affects: [AsyncCorpulse, report helpers, async parity tests]
tech-stack:
  added: []
  patterns: [shared frozen fixture modules, async-to-sync parity assertions via normalized dataframe records]
key-files:
  created: [tests/report_fixtures.py, .planning/phases/12-async-parity-methods-unit-tests/12-01-SUMMARY.md]
  modified: [tests/test_report_helpers.py, tests/test_async_core_integration.py, corpulse/async_core.py]
key-decisions:
  - "Kept the Phase 11 golden report assertions untouched and moved only fixture-building logic into a shared module."
  - "Implemented AsyncCorpulse.to_dataframe as a thin async wrapper over the shared _build_dataframe_rows helper to prevent status drift."
patterns-established:
  - "Shared deterministic fixtures should expose both a seeded backend and snapshot rows so sync and async suites assert parity from identical data."
  - "Async dataframe parity should compare normalized to_dict(\"records\") output instead of DataFrame identity."
requirements-completed: [ASYNC-PAR-01, ASYNC-TEST-01]
duration: 3m
completed: 2026-04-10
---

# Phase 12 Plan 01: Async Parity Fixture and DataFrame Summary

**Shared frozen report fixtures plus AsyncCorpulse dataframe export verified against sync Corpulse on identical backend data**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-10T08:16:41Z
- **Completed:** 2026-04-10T08:20:02Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `tests/report_fixtures.py` as the single deterministic source for the frozen report corpus used by both sync and async suites.
- Rewired sync report-helper tests to consume the shared fixture without changing the existing golden stdout assertions.
- Added async dataframe parity tests and implemented `AsyncCorpulse.to_dataframe()` with the same pandas install hint and row ordering as sync `Corpulse`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract one authoritative frozen report fixture source for sync and async parity per planner discretion** - `6a09fae`, `997172c` (test, feat)
2. **Task 2: Add and implement async dataframe parity per ASYNC-PAR-01 and ASYNC-TEST-01** - `4157c5c`, `2599f3d` (test, feat)

_Note: TDD tasks used red/green commits._

## Files Created/Modified
- `tests/report_fixtures.py` - Shared frozen report corpus builder and snapshot helpers for sync and async parity tests.
- `tests/test_report_helpers.py` - Sync report-helper suite now imports the shared fixture module and keeps the established golden assertions intact.
- `tests/test_async_core_integration.py` - Async parity tests use the shared snapshot to compare normalized dataframe output against sync behavior.
- `corpulse/async_core.py` - Adds `AsyncCorpulse.to_dataframe()` backed by the shared dataframe row helper and sync pandas guard.

## Decisions Made
- Preserved the Phase 11 golden report and cleanup outputs byte-for-byte by moving only fixture construction into the shared module.
- Reused `_build_dataframe_rows(...)` in the async path so status classification and row shape stay aligned with sync behavior.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Async dataframe parity is in place and backed by one frozen fixture source, so the next async report/cleanup work can build against direct sync comparisons.
- No blockers were introduced by this plan.

## Self-Check: PASSED

- Found summary file: `.planning/phases/12-async-parity-methods-unit-tests/12-01-SUMMARY.md`
- Found commit: `6a09fae`
- Found commit: `997172c`
- Found commit: `4157c5c`
- Found commit: `2599f3d`

---
*Phase: 12-async-parity-methods-unit-tests*
*Completed: 2026-04-10*
