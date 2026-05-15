---
phase: 34-optional-extras-install-verification
plan: 34-03
subsystem: packaging
tags: [postgres, asyncpg, fastapi, guidance, testing]
requires:
  - phase: 34-optional-extras-install-verification
    provides: optional extra install matrix and base wheel verification
provides:
  - actionable missing-extra guidance for postgres and async postgres
  - package-level guidance assertions for optional dependency failures
  - final Phase 34 verification across build, unit, and install tests
affects:
  - Phase 35 release automation
tech-stack:
  added: []
  patterns: [actionable ImportError messages, post-build verification]
key-files:
  created: []
  modified:
    - corpulse/backends/postgres.py
    - corpulse/backends/postgres_async.py
    - tests/test_postgres_backend.py
    - tests/test_async_postgres_backend.py
    - tests/test_package.py
requirements-completed: [EXTRA-03]
duration: 0.5h
completed: 2026-05-15
---

# Phase 34: Optional Extras Install Verification Summary

**Optional dependency failures now tell users exactly what to install, and the full phase verification suite passes against the rebuilt wheel.**

## Performance

- **Duration:** 0.5h
- **Started:** 2026-05-15T07:39:58Z
- **Completed:** 2026-05-15T07:42:35Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Updated postgres and async postgres failure messages to include direct `pip install corpulse[...]` commands.
- Added a package-level guidance test that locks all optional dependency instructions in place.
- Re-ran the focused unit suite, the opt-in install matrix, and the build gate after the postgres extra fix.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tighten missing-postgres guidance** - `a059b1a` (`test`)
2. **Task 2: Lock optional dependency guidance** - `91862e7` (`test`)
3. **Task 3: Final Phase 34 verification** - no code commit; verification only

**Plan metadata:** postgres extra was corrected earlier in Phase 34 with commit `5f414b4` so the install matrix could pass in a clean venv.

## Files Created/Modified
- `corpulse/backends/postgres.py` - direct install guidance for missing psycopg pool support.
- `corpulse/backends/postgres_async.py` - direct install guidance for missing asyncpg support.
- `tests/test_postgres_backend.py` - regex assertions for actionable postgres guidance.
- `tests/test_async_postgres_backend.py` - regex assertions for actionable async postgres guidance.
- `tests/test_package.py` - package-level optional dependency guidance assertions.

## Decisions Made
- Kept the FastAPI and Qdrant guidance strings unchanged because they were already actionable.
- Kept pandas as a direct-install instruction instead of promoting it to a package extra.

## Deviations from Plan

### Auto-fixed Issues

**1. [EXTRA-04 - Packaging] postgres extra did not import cleanly in a clean venv**
- **Found during:** Wave 2 extras matrix
- **Issue:** `import psycopg` failed after `corpulse[postgres]` install when the extra only requested `psycopg[pool]>=3.2`.
- **Fix:** Changed the extra to `psycopg[binary,pool]>=3.2` so the built wheel installs cleanly in isolated environments.
- **Files modified:** `pyproject.toml`, `tests/test_package.py`
- **Verification:** `CORPULSE_RUN_INSTALL_TESTS=1 python -m pytest tests/test_distribution_installs.py -k "optional_extra or qdrant_extra"` passed after rebuild.
- **Committed in:** `5f414b4`

**Total deviations:** 1 auto-fixed (1 packaging issue)
**Impact on plan:** Required to satisfy the phase goal. The matrix now reflects a truly installable artifact.

## Issues Encountered
- The first extras-matrix run exposed the postgres binary safety gap described above.

## Next Phase Readiness
- Phase 34 is complete and Phase 35 can now focus on release automation.
- The repo now has explicit, copyable install guidance for every optional integration failure path.

---
*Phase: 34-optional-extras-install-verification*
*Completed: 2026-05-15*
