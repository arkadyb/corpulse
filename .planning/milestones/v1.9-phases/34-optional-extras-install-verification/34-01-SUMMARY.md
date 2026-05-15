---
phase: 34-optional-extras-install-verification
plan: 34-01
subsystem: testing
tags: [venv, wheel, install, pytest, packaging]
requires:
  - phase: 33-package-metadata-and-build-readiness
    provides: built wheel and base package metadata
provides:
  - isolated venv install harness for built wheels
  - base install verification for optional-dependency absence
  - opt-in install-test gating via `CORPULSE_RUN_INSTALL_TESTS`
affects:
  - Phase 34 optional extras install matrix
tech-stack:
  added: [venv]
  patterns: [opt-in install tests, built-wheel verification]
key-files:
  created:
    - tests/test_distribution_installs.py
  modified:
    - tests/test_package.py
requirements-completed: [PKG-04, EXTRA-02]
duration: 0.5h
completed: 2026-05-15
---

# Phase 34: Optional Extras Install Verification Summary

**A gated venv-based harness now proves the built wheel installs cleanly without optional dependencies and keeps the install tests opt-in for normal runs.**

## Performance

- **Duration:** 0.5h
- **Started:** 2026-05-15T07:31:00Z
- **Completed:** 2026-05-15T07:37:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `tests/test_distribution_installs.py` with reusable helpers for clean venv creation and wheel installation.
- Verified the base wheel imports `corpulse` and `Corpulse` while `qdrant_client`, `psycopg`, `asyncpg`, `fastapi`, `pandas`, and `tabulate` remain absent.
- Kept the install test suite gated behind `CORPULSE_RUN_INSTALL_TESTS=1` so normal test runs stay fast.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add install harness scaffold** - `965dbc9` (`test`)
2. **Task 2: Add base wheel install check** - `b44566b` (`test`)

**Plan metadata:** pending bookkeeping commit for this summary and phase tracking update.

## Files Created/Modified
- `tests/test_distribution_installs.py` - venv helpers, gating, and base wheel install check.
- `tests/test_package.py` - static gate assertion for the install-test harness.

## Decisions Made
- Used a direct wheel install from `dist/` instead of a source install so Phase 34 verifies the release artifact itself.
- Kept the install tests opt-in via environment variable to avoid making normal test runs depend on networked package installation.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- None.

## Next Phase Readiness
- The harness is ready for the extra-install matrix in Wave 2.
- Base install regression risk is now covered by an artifact-level check.

---
*Phase: 34-optional-extras-install-verification*
*Completed: 2026-05-15*
