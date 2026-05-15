---
phase: 36-user-install-docs-and-release-validation
plan: "36-02"
subsystem: testing
tags: [pypi, release, trusted-publishing, qdrant, pytest]
requires:
  - phase: 35-trusted-publishing-release-automation
    provides: GitHub release workflow with Trusted Publishing gates
provides:
  - exact published PyPI smoke checks for the base package and qdrant extra
  - static regression guards for release checklist wording
affects: [release-process, package-installation, release-validation]
tech-stack:
  added: []
  patterns:
    - manual published-package smoke checks documented as exact shell commands
    - checklist-as-source-of-truth release validation
key-files:
  created:
    - .planning/phases/36-user-install-docs-and-release-validation/36-02-SUMMARY.md
  modified:
    - .github/RELEASE_CHECKLIST.md
    - tests/test_release_workflow.py
key-decisions:
  - Kept the published-package smoke checks manual and exact because they depend on external PyPI state.
  - Used separate clean virtual environments for the base package and qdrant extra smoke checks.
requirements-completed: [VAL-01, VAL-02]
duration: 12m
completed: 2026-05-15
---

# Phase 36: User Install Docs and Release Validation Summary

**Exact post-publish PyPI smoke checks for `corpulse` and `corpulse[qdrant]`, with tests pinning the release checklist wording**

## Performance

- **Duration:** 12 min
- **Started:** 2026-05-15T08:07:00Z
- **Completed:** 2026-05-15T08:19:29Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added explicit VAL-01 and VAL-02 post-publish PyPI smoke sections to `.github/RELEASE_CHECKLIST.md`.
- Kept the TestPyPI validation command and no-token Trusted Publishing guidance intact.
- Added regression tests that assert the exact base and qdrant smoke command fragments.

## Task Commits

1. **Task 1: update release checklist smoke checks** - `9fd7c23`
2. **Task 2: pin checklist wording in tests** - `51bddcf`

## Files Created/Modified

- `.github/RELEASE_CHECKLIST.md` - documents exact clean-environment post-publish smoke commands for base and qdrant extra installs.
- `tests/test_release_workflow.py` - asserts the checklist contains the required VAL-01 and VAL-02 fragments.

## Decisions Made

- Kept the published-package smoke checks manual and exact because they depend on external PyPI state.
- Used separate clean virtual environments for the base package and qdrant extra smoke checks.

## Deviations from Plan

None within the requested scope. The shared `.planning/STATE.md` and `.planning/ROADMAP.md` files were intentionally left untouched per the user instruction for this worktree-like run.

## Issues Encountered

- The repository already contained unrelated `.planning/` changes and untracked planning artifacts; they were left untouched.
- External PyPI/TestPyPI validation was not run in this turn because the requested scope was limited to checklist/docs guards and local pytest verification.

## Next Phase Readiness

- The release checklist now states the exact validation commands required for VAL-01 and VAL-02.
- The repo is ready for the broader release-validation step that exercises build and install artifacts if the orchestrator schedules it.

## Self-Check: PASSED

- `.planning/phases/36-user-install-docs-and-release-validation/36-02-SUMMARY.md` exists.
- Commits `9fd7c23`, `51bddcf`, and `1cac15e` exist in git history.
