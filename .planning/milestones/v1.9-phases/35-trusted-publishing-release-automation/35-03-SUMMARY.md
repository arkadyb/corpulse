---
phase: 35-trusted-publishing-release-automation
plan: "35-03"
subsystem: release
tags: [github-actions, pypi, trusted-publishing, release-gate]
requires:
  - phase: 35-trusted-publishing-release-automation
    provides: build artifacts and TestPyPI Trusted Publishing
provides:
  - Tag-gated production PyPI publish job using Trusted Publishing
  - `pypi` GitHub environment gate in the workflow
  - Maintainer documentation for required reviewers or equivalent approval
affects: [release-process, production-publishing]
tech-stack:
  added: []
  patterns: [tag-gated-release, environment-gated-publishing]
key-files:
  created: []
  modified:
    - .github/workflows/release.yml
    - .github/TRUSTED_PUBLISHING.md
    - tests/test_release_workflow.py
requirements-completed: [REL-03, REL-04]
duration: reconstructed
completed: 2026-05-15
---

# Phase 35: Trusted Publishing Release Automation Summary

The release workflow now has a production PyPI publishing job guarded by `refs/tags/v*`, using OIDC Trusted Publishing and the `pypi` GitHub environment.

## Performance

- **Duration:** reconstructed from existing implementation
- **Completed:** 2026-05-15
- **Tasks:** 4
- **Files modified:** 3

## Accomplishments

- Added `publish-pypi` with `if: startsWith(github.ref, 'refs/tags/v')`.
- Set `environment: pypi` and job-scoped `id-token: write` for production publishing.
- Kept the production publish action on the default PyPI endpoint by omitting `repository-url`.
- Documented the required GitHub environment approval gate before first production release.
- Added tests that verify tag gating, environment gating, and absence of long-lived PyPI credentials.

## Task Commits

No dedicated Phase 35 task commits were found in recent git history. This summary reconstructs the completed plan from the current files and passing tests so the milestone audit has the required GSD evidence.

## Files Created/Modified

- `.github/workflows/release.yml` - production PyPI publish job.
- `.github/TRUSTED_PUBLISHING.md` - production PyPI trusted publisher and environment gate guidance.
- `tests/test_release_workflow.py` - production publish and trusted publishing gate tests.

## Decisions Made

- Production PyPI publishing only runs from version tags.
- The external GitHub `pypi` environment approval gate remains a required maintainer setup step before first release.

## Deviations from Plan

- Summary was reconstructed after implementation because the original Phase 35 execution did not leave `35-*-SUMMARY.md` artifacts.
- `actionlint` availability is checked during final verification; if absent, the verification report records the skip.

## Issues Encountered

- External GitHub environment reviewer configuration cannot be verified from the local repository and remains documented as a manual release prerequisite.

## Self-Check: PASSED

The release workflow and docs contain the REL-03 and REL-04 evidence expected by the plan.
