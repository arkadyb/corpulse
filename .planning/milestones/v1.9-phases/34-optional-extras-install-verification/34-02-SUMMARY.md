---
phase: 34-optional-extras-install-verification
plan: 34-02
subsystem: packaging
tags: [extras, qdrant, postgres, fastapi, venv, install]
requires:
  - phase: 34-optional-extras-install-verification
    provides: base wheel install harness and gated install testing
provides:
  - isolated install matrix for all declared optional extras
  - qdrant wrapper surface verification from a built wheel
  - binary-safe postgres extra packaging fix
affects:
  - Phase 34 missing-extra guidance
tech-stack:
  added: [importlib]
  patterns: [PEP 508 direct wheel installs, optional-extra matrix]
key-files:
  created: []
  modified:
    - pyproject.toml
    - tests/test_distribution_installs.py
    - tests/test_package.py
requirements-completed: [EXTRA-01, EXTRA-04]
duration: 0.75h
completed: 2026-05-15
---

# Phase 34: Optional Extras Install Verification Summary

**The built wheel now installs all declared extras in isolated venvs, and the Qdrant wrapper surface resolves from the `corpulse[qdrant]` extra.**

## Performance

- **Duration:** 0.75h
- **Started:** 2026-05-15T07:37:05Z
- **Completed:** 2026-05-15T07:39:55Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added a parametrized venv-based install matrix covering `qdrant`, `postgres`, `postgres-async`, and `fastapi`.
- Verified the Qdrant extra exposes `QdrantCorpulseClient` and `AsyncQdrantCorpulseClient` from the built wheel.
- Fixed the `postgres` extra to install a binary-safe psycopg distribution so `import psycopg` succeeds in a clean environment.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add optional extras matrix** - `5b112d0` (`test`)
2. **Task 2: Add qdrant extra surface check** - `5b112d0` (`test`)

**Plan metadata:** included a follow-up fix commit for the postgres extra packaging issue.

## Files Created/Modified
- `tests/test_distribution_installs.py` - parametrized install matrix and qdrant surface check.
- `tests/test_package.py` - extra-declaration contract assertions.
- `pyproject.toml` - `postgres` extra now uses `psycopg[binary,pool]>=3.2`.

## Decisions Made
- Used PEP 508 direct wheel references so pip can resolve extras from the built artifact while still pulling dependencies from the index.
- Made the postgres extra binary-safe because the plain `psycopg[pool]` extra was not sufficient in clean venvs.

## Deviations from Plan

### Auto-fixed Issues

**1. [EXTRA-04 - Packaging] postgres extra did not import cleanly in a clean venv**
- **Found during:** Task 1 (`test_optional_extra_installs_from_wheel`)
- **Issue:** `import psycopg` failed after `corpulse[postgres]` install because the extra did not include a binary-safe psycopg distribution.
- **Fix:** Changed `postgres = ["psycopg[binary,pool]>=3.2"]` in `pyproject.toml` and updated the package contract tests.
- **Files modified:** `pyproject.toml`, `tests/test_package.py`
- **Verification:** `CORPULSE_RUN_INSTALL_TESTS=1 python -m pytest tests/test_distribution_installs.py -k "optional_extra or qdrant_extra"` passed after rebuild.
- **Committed in:** `5f414b4`

**Total deviations:** 1 auto-fixed (1 packaging issue)
**Impact on plan:** Required for the phase goal. The matrix now verifies a real installable artifact.

## Issues Encountered
- The first matrix run exposed the postgres extra packaging gap described above.

## Next Phase Readiness
- The extras matrix is now green and ready for the missing-guidance cleanup in Wave 3.
- Optional extra installs are verified from built artifacts, not the source tree.

---
*Phase: 34-optional-extras-install-verification*
*Completed: 2026-05-15*
