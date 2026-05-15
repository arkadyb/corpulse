---
phase: 33-package-metadata-and-build-readiness
plan: 33-01
subsystem: packaging
tags: [pypi, hatchling, metadata, versioning, testing]
requires:
  - phase: 32-replay-feasibility-and-minimal-proof
    provides: replay-feasibility context and milestone state
provides:
  - PyPI-ready package metadata in `pyproject.toml`
  - dynamic version extraction from `corpulse/__init__.py`
  - metadata contract tests for package and import surfaces
affects:
  - Phase 34 optional extras verification
tech-stack:
  added: [hatchling]
  patterns: [dynamic version source, metadata contract testing]
key-files:
  created: []
  modified:
    - pyproject.toml
    - tests/test_package.py
    - tests/test_import.py
requirements-completed: [PKG-01, PKG-02]
duration: 5min
completed: 2026-05-15
---

# Phase 33: Package Metadata and Build Readiness Summary

**PyPI metadata now uses Hatchling dynamic versioning, with tests enforcing the single-source version contract and the required discoverability fields.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-15T07:20:30Z
- **Completed:** 2026-05-15T07:22:58Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Replaced the static `pyproject.toml` version with Hatchling dynamic version extraction from `corpulse/__init__.py`.
- Added PyPI metadata fields, classifiers, and URLs required for the first release page.
- Strengthened package and import tests to assert the new metadata contract and preserved runtime `__version__`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Make package metadata PyPI-ready and single-source the version** - `73cc98b` (`feat`)
2. **Task 2: Update package/import tests to enforce the metadata contract** - `6d6831d` (`test`)

**Plan metadata:** pending bookkeeping commit for this summary and phase tracking update.

## Files Created/Modified
- `pyproject.toml` - Dynamic versioning, PyPI metadata, and Hatch version source configuration.
- `tests/test_package.py` - Metadata contract assertions for versioning, classifiers, and project URLs.
- `tests/test_import.py` - Runtime version contract check.

## Decisions Made
- Kept `corpulse.__version__ = "0.1.0"` at runtime until a deliberate release-version bump is planned.
- Used Hatchling's path-based version source so the package version stays single-sourced without changing the import surface.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- None.

## Next Phase Readiness
- Phase 33 can now move on to source/wheel artifact validation and README/PyPI rendering checks.
- Phase 34 can rely on the now-stable version and metadata contract when validating optional extras from built artifacts.

---
*Phase: 33-package-metadata-and-build-readiness*
*Completed: 2026-05-15*
