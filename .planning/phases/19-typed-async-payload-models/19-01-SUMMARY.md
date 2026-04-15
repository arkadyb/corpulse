---
phase: 19
plan: 01
subsystem: models
tags: [typing, refactoring, models]
requirements: [MODEL-01, MODEL-02, MODEL-03]
requires: []
provides: [TypedDict models for API and backend payloads]
affects: [corpulse/backends/base.py, corpulse/backends/memory.py, corpulse/backends/sqlite.py, corpulse/backends/postgres.py, corpulse/backends/postgres_async.py]
tech-stack: [Python, typing.TypedDict]
key-files: [corpulse/models.py, corpulse/backends/base.py]
metrics:
  duration: 15 min
  completed_date: "2026-04-15"
---

# Phase 19 Plan 01: Typed Async Payload Models - Models and Backend Migration Summary

## One-liner
Introduced a centralized `corpulse/models.py` with `TypedDict` definitions for all API and backend payloads, migrating existing backend row types.

## Description
This plan laid the foundation for better type safety and IDE support by centralizing all data structures into a new `corpulse/models.py` module. 

Key actions:
1.  **Centralized Models:** Created `corpulse/models.py` containing `TypedDict` definitions for:
    *   **Backend Row Types:** `DocumentRow`, `RetrievalRow`, `EngagementRow`, `EmbeddingRow`.
    *   **Report API Types:** `ReportRow`, `ReportSummary`, `ReportPayload`.
    *   **Cleanup API Types:** `GhostItem`, `ObsoleteItem`, `StaleItem`, `SuspectItem`, `CleanupSection`, `CleanupPayload`.
2.  **Backend Refactoring:**
    *   Removed `TypedDict` definitions from `corpulse/backends/base.py` and replaced them with imports (and re-exports) from `corpulse.models`.
    *   Updated all storage backend implementations (`memory.py`, `sqlite.py`, `postgres.py`, `postgres_async.py`) to import these models directly from `..models`, ensuring consistent use of the centralized types.
3.  **Verification:** Confirmed that the new models are loadable and that all existing backend contract and implementation tests pass, maintaining full backward compatibility with the existing dictionary-based API.

## Key Decisions
- **Re-exports in `base.py`:** Chose to re-export the models from `corpulse/backends/base.py` (e.g., `DocumentRow as DocumentRow`) to ensure that existing code importing from `base.py` continues to work without modification, while also updating implementations to import directly from `models.py` for clarity.
- **TypedDict for Compatibility:** Used `typing.TypedDict` for all models to provide static type checking and IDE autocompletion while remaining 100% compatible with existing runtime dictionary-based code.
- **CleanupItem Union:** Defined a `CleanupItem` union to represent the different types of items that can appear in a cleanup section, providing better typing for the generic `CleanupSection` model.

## Deviations from Plan
- None - the plan was executed as written.

## Threat Flags
None.

## Known Stubs
None.

## Self-Check: PASSED
- [x] `corpulse/models.py` exists with all required `TypedDict` definitions.
- [x] Backend row types are moved from `base.py` to `models.py`.
- [x] Backend implementations updated to use centralized models.
- [x] All existing tests pass.
- [x] Commits 6a635e1 and 7f5734d exist in the history.
