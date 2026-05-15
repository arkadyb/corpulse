---
phase: 33-package-metadata-and-build-readiness
plan: 33-03
subsystem: documentation
tags: [readme, twine, pypi, build, packaging, testing]
requires:
  - phase: 33-package-metadata-and-build-readiness
    provides: built artifacts and metadata contract tests
provides:
  - PyPI-first installation instructions in README
  - README metadata tests for install text and `readme = "README.md"`
  - verified PyPI long-description rendering for built artifacts
affects:
  - Phase 34 optional extras install verification
tech-stack:
  added: [twine]
  patterns: [PyPI-first install docs, long-description rendering gate]
key-files:
  created: []
  modified:
    - README.md
    - tests/test_package.py
requirements-completed: [PKG-01, PKG-03]
duration: 3min
completed: 2026-05-15
---

# Phase 33: Package Metadata and Build Readiness Summary

**README installation instructions now lead with PyPI commands, and the built artifacts pass `twine check` with the new long-description content.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-15T07:24:40Z
- **Completed:** 2026-05-15T07:25:34Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Replaced GitHub-first install instructions with PyPI-first commands and kept the source install fallback.
- Added tests that lock the README install text and the `readme = "README.md"` metadata contract.
- Confirmed `python -m twine check dist/*` passes for both built release artifacts.

## Task Commits

Each task was committed atomically:

1. **Task 1: Switch README to PyPI install commands** - `a5d8fc1` (`docs`)
2. **Task 2: Lock PyPI install text** - `42e9c91` (`test`)

**Plan metadata:** pending bookkeeping commit for this summary and phase tracking update.

## Files Created/Modified
- `README.md` - PyPI-first install block and source-install fallback.
- `tests/test_package.py` - README install text and metadata assertions.

## Decisions Made
- Kept the source-install fallback so users can still install from GitHub when needed.
- Kept the `[qdrant]` extra guidance in prose while switching the primary install commands to PyPI.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `twine` was missing from the active system interpreter because the environment is externally managed.
- Resolved by using the temporary `/tmp/corpulse-gsd-tools` venv created for the build gate and installing `twine` there.

## Next Phase Readiness
- Phase 34 can now validate optional-extra installs from built artifacts using the PyPI-first install commands documented in the README.
- The release surface is ready for installation and import checks without additional metadata changes.

---
*Phase: 33-package-metadata-and-build-readiness*
*Completed: 2026-05-15*
