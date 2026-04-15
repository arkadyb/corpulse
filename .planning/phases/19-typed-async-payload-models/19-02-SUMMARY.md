---
phase: 19
plan: 02
subsystem: core
tags: [typing, async, models, refactoring]
requirements: [MODEL-01, MODEL-02, MODEL-03, MODEL-04]
requires: [01]
provides: [Typed return values for the async public API, IDE support]
affects: [corpulse/core.py, corpulse/async_core.py, corpulse/models.py]
tech-stack: [Python, typing.TypedDict]
key-files: [corpulse/core.py, corpulse/async_core.py, corpulse/models.py]
metrics:
  duration: 20 min
  completed_date: "2026-04-15"
---

# Phase 19 Plan 02: Typed Async Payload Models - Public API Integration Summary

## One-liner
Updated `corpulse/core.py` and `corpulse/async_core.py` with the new typed models to provide full IDE autocompletion and static safety for consumers.

## Description
This plan successfully integrated the centralized `TypedDict` models into the core library's public and internal APIs.

Key actions:
1.  **Model Expansion:** Added `DuplicatePair` and `CorpusHealth` models to `corpulse/models.py` to support full coverage of analysis return values.
2.  **Core Builder Typing:** Updated all internal builder functions in `corpulse/core.py` (e.g., `_build_report_rows`, `_build_cleanup_payload`) with explicit return and parameter type hints using the new models.
3.  **Sync API Updates:** Updated `Corpulse` analysis methods (`get_ghosts`, `corpus_health`, etc.) to return the appropriate `TypedDict` models.
4.  **Async API Updates:** Updated `AsyncCorpulse` public methods (`report`, `cleanup_report`, `get_duplicates`, etc.) with model return types, providing full IDE support for async consumers.
5.  **MODEL-04 Verification:** Confirmed that `cleanup_report()` in `AsyncCorpulse` remains strictly analysis-only and does not mutate document data. Added an explicit code comment in `async_core.py` per requirement.
6.  **Static Verification:** Created and ran a verification script (`verify_types.py`) using `inspect.get_type_hints` to ensure that public methods indeed return the expected `TypedDict` models rather than generic dictionaries.

## Key Decisions
- **Rule 2 - Missing Models:** Added `DuplicatePair` and `CorpusHealth` to `models.py` during implementation as they were required for full API typing but absent from the initial model set.
- **MODEL-04 Compliance:** Verified that all builders called by `cleanup_report` only perform read operations and data transformations, ensuring that the cleanup report remains safe to call without side effects.

## Deviations from Plan
- **Rule 2 - Type Expansion:** Added missing `DuplicatePair` and `CorpusHealth` models to `corpulse/models.py` to allow full typing of the `corpus_health` and `get_duplicates` methods.

## Threat Flags
None.

## Known Stubs
None.

## Self-Check: PASSED
- [x] All `AsyncCorpulse` public methods are fully typed.
- [x] `corpulse/core.py` internal builders are fully typed.
- [x] `cleanup_report()` is confirmed non-mutating with a comment.
- [x] Static verification via `inspect.get_type_hints` passed.
- [x] All existing tests pass.
- [x] Commits 19cf19d and f926638 exist in the history.
