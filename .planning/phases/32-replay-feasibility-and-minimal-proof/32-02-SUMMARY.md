---
phase: 32
plan: 32-02
subsystem: api
tags: [replay, sync-api, typed-dicts]
requires:
  - phase: 32-01
    provides: replay implementation boundary
provides:
  - sync callable replay helper
  - sync Corpulse replay facade
affects: [corpulse-core, replay, tests]
tech-stack:
  added: []
  patterns: [dependency-free-helper, public-facade]
key-files:
  created:
    - corpulse/replay.py
    - tests/test_replay.py
  modified:
    - corpulse/models.py
    - corpulse/core.py
key-decisions:
  - "Replay reports record handler success/failure but never store handler return values."
  - "Default replay performs no sleeping unless time_scale is provided."
patterns-established:
  - "Replay helpers accept injected sleep and clock callables for deterministic tests."
requirements-completed: [REPLAY-02]
duration: 25min
completed: 2026-05-05
---

# Phase 32 Plan 32-02: Shared Replay Helper and Sync Facade Summary

**Dependency-free sync callable replay helper with typed request/result payloads and Corpulse facade**

## Performance

- **Duration:** 25 min
- **Started:** 2026-05-05
- **Completed:** 2026-05-05
- **Tasks:** 4
- **Files modified:** 4

## Accomplishments

- Added `ReplayRequest`, `ReplayResult`, `ReplaySummary`, and `ReplayReportPayload` typed payloads.
- Implemented deterministic trace ordering, scaled delay calculation, handler invocation, error capture, stop-on-error, and summary counting.
- Added `Corpulse.replay_rag_request_traces(...)` over existing trace retrieval APIs.
- Added sync replay tests for ordering, no-sleep default, scaled delays, invalid scale, handler errors, stop-on-error, and facade behavior.

## Task Commits

No commits were created because `commit_docs` is false for this project configuration.

## Files Created/Modified

- `corpulse/replay.py` - Dependency-free replay helper implementation.
- `tests/test_replay.py` - Sync replay helper and facade tests.
- `corpulse/models.py` - Replay payload TypedDicts.
- `corpulse/core.py` - Sync public replay facade.

## Decisions Made

- Handler return values are intentionally ignored and absent from replay result payloads.
- Trace delay defaults to `0.0` with no sleep when `time_scale is None`.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for async replay parity and docstring coverage.

## Self-Check: PASSED

---
*Phase: 32*
*Completed: 2026-05-05*
