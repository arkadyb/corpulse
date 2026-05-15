---
phase: 35-trusted-publishing-release-automation
plan: "35-01"
subsystem: release
tags: [github-actions, build, artifacts, testing]
requires:
  - phase: 33-package-metadata-and-build-readiness
    provides: PyPI-ready package metadata and buildable artifacts
provides:
  - Release workflow build job that runs tests and builds distributions
  - Uploaded `python-package-distributions` artifact containing `dist/*`
  - Static tests for the build job and artifact upload contract
affects: [release-process, packaging-validation]
tech-stack:
  added: [github-actions]
  patterns: [build-once-publish-later, static workflow tests]
key-files:
  created:
    - .github/workflows/release.yml
    - tests/test_release_workflow.py
  modified: []
requirements-completed: [REL-01]
duration: reconstructed
completed: 2026-05-15
---

# Phase 35: Trusted Publishing Release Automation Summary

The release workflow now has a build job that tests the package, builds source and wheel distributions, and uploads the exact `dist/*` outputs as `python-package-distributions` for downstream publish jobs.

## Performance

- **Duration:** reconstructed from existing implementation
- **Completed:** 2026-05-15
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `.github/workflows/release.yml` with `workflow_dispatch` and `v*` tag triggers.
- Kept top-level workflow permissions at `contents: read`.
- Added the build job using checkout, Python 3.12, `python -m pytest`, `python -m build`, and `actions/upload-artifact@v4`.
- Added release workflow tests that assert the build job uploads the expected artifact and does not receive OIDC publish permission.

## Task Commits

No dedicated Phase 35 task commits were found in recent git history. This summary reconstructs the completed plan from the current files and passing tests so the milestone audit has the required GSD evidence.

## Files Created/Modified

- `.github/workflows/release.yml` - build job, artifact upload, and release triggers.
- `tests/test_release_workflow.py` - static release workflow tests.

## Decisions Made

- Build once in the unprivileged build job and publish the uploaded artifact in later jobs.
- Keep OIDC `id-token: write` out of the build job.

## Deviations from Plan

- Summary was reconstructed after implementation because the original Phase 35 execution did not leave `35-*-SUMMARY.md` artifacts.

## Issues Encountered

- None in the current implementation evidence.

## Self-Check: PASSED

The release workflow and tests contain the REL-01 evidence expected by the plan.
