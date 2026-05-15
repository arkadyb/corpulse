---
phase: 36-user-install-docs-and-release-validation
plan: 01
subsystem: testing
tags: [pypi, trusted-publishing, release, pytest, documentation]

# Dependency graph
requires:
  - phase: 35-trusted-publishing-release-automation
    provides: GitHub Actions release workflow with Trusted Publishing and environment gates
provides:
  - PyPI-first installation guidance in README.md
  - Maintainer release checklist for version bump, build, TestPyPI, PyPI publish, and smoke checks
  - Static tests that lock the release docs and checklist wording
affects: [release-process, maintainer-docs, packaging-validation]

# Tech tracking
tech-stack:
  added: [markdown documentation, pytest text assertions]
  patterns: [PyPI-first user install docs, checklist-driven release ops, token-free Trusted Publishing]

key-files:
  created: [.github/RELEASE_CHECKLIST.md]
  modified: [README.md, .github/TRUSTED_PUBLISHING.md, tests/test_package.py, tests/test_release_workflow.py]

key-decisions:
  - "Keep README installation short and PyPI-first, with only a brief maintainer link to the release checklist."
  - "Make .github/RELEASE_CHECKLIST.md the authoritative first-release runbook and keep it token-free."

patterns-established:
  - "Pattern 1: Use static pytest assertions to lock public install commands and release-doc wording."
  - "Pattern 2: Put maintainer release operations in .github/RELEASE_CHECKLIST.md instead of expanding README scope."

requirements-completed: [DOC-01, DOC-02, DOC-03, VAL-01, VAL-02]

# Metrics
duration: 17min
completed: 2026-05-15
---

# Phase 36: User Install Docs and Release Validation Summary

PyPI-first install docs and a maintainer release checklist for Trusted Publishing, TestPyPI validation, and post-publish smoke checks.

## Performance

- **Duration:** 17 min
- **Started:** 2026-05-15T08:00:00Z
- **Completed:** 2026-05-15T08:17:27Z
- **Tasks:** 1
- **Files modified:** 5

## Accomplishments
- Kept README installation PyPI-first while preserving the source-install fallback and Qdrant quickstart examples.
- Added `.github/RELEASE_CHECKLIST.md` as the first-release runbook with version bump, build, TestPyPI, PyPI, and smoke-check steps.
- Extended static pytest coverage so the README and release docs stay aligned with the intended release flow.

## Task Commits

1. **Task 1: PyPI-first install docs and release checklist** - `8ad75e3` (docs)

**Plan metadata:** `8ad75e3` (docs: complete plan implementation)

## Files Created/Modified
- `README.md` - Keeps PyPI install commands first and links maintainers to the release checklist.
- `.github/RELEASE_CHECKLIST.md` - First-release runbook with exact publish and smoke-check commands.
- `.github/TRUSTED_PUBLISHING.md` - Points maintainers at the release checklist for operational steps.
- `tests/test_package.py` - Locks the README installation wording and checklist link.
- `tests/test_release_workflow.py` - Verifies the checklist flow and rejects token-based publish guidance.

## Decisions Made
- Keep the maintainer guidance in `.github/RELEASE_CHECKLIST.md` rather than expanding `README.md` into a long release guide.
- Treat Trusted Publishing as the only release path and document token usage only as a prohibition.

## Deviations from Plan

None - plan executed exactly as specified.

## Issues Encountered

None.

## Next Phase Readiness
- Public install docs now point users to PyPI-first commands.
- Release operations are documented for maintainers and locked by tests.
- No blockers introduced for later release work.

## Self-Check: PASSED

All referenced files exist and commit `8ad75e3` is present in git history.

---
*Phase: 36-user-install-docs-and-release-validation*
*Completed: 2026-05-15*
