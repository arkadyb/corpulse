---
phase: 32
plan: 32-03
subsystem: api
tags: [replay, async-api, docstrings]
requires:
  - phase: 32-02
    provides: shared replay helper and sync semantics
provides:
  - async callable replay helper
  - AsyncCorpulse replay facade
affects: [async-core, replay, docs-tests]
tech-stack:
  added: []
  patterns: [async-parity, shared-helper-semantics]
key-files:
  created: []
  modified:
    - corpulse/replay.py
    - corpulse/async_core.py
    - tests/test_replay.py
    - tests/test_docstrings.py
key-decisions:
  - "Async replay reuses the same ordering, delay, envelope, and summary semantics as sync replay."
patterns-established:
  - "Async facades fetch traces then delegate to a shared helper instead of duplicating aggregation in async_core.py."
requirements-completed: [REPLAY-02]
duration: 20min
completed: 2026-05-05
---

# Phase 32 Plan 32-03: Async Replay Facade and Docstring Coverage Summary

**Async callable replay parity with shared semantics and public method docstring coverage**

## Performance

- **Duration:** 20 min
- **Started:** 2026-05-05
- **Completed:** 2026-05-05
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Added `AsyncReplayHandler` and `async_replay_rag_request_traces(...)`.
- Added `AsyncCorpulse.areplay_rag_request_traces(...)`.
- Extended replay tests for async handler invocation, async sleep injection, and async facade trace retrieval.
- Added sync and async replay methods to docstring parameter coverage tests.

## Task Commits

No commits were created because `commit_docs` is false for this project configuration.

## Files Created/Modified

- `corpulse/replay.py` - Async replay helper.
- `corpulse/async_core.py` - Async public replay facade.
- `tests/test_replay.py` - Async parity tests.
- `tests/test_docstrings.py` - Replay method Args checks.

## Decisions Made

- Async replay awaits the user-provided callable and injected sleep callable, preserving sync summary semantics.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for README documentation, planning artifact updates, and full regression verification.

## Self-Check: PASSED

---
*Phase: 32*
*Completed: 2026-05-05*
