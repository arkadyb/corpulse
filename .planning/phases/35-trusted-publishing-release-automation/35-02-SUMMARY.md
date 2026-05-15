---
phase: 35-trusted-publishing-release-automation
plan: "35-02"
subsystem: release
tags: [github-actions, testpypi, trusted-publishing, oidc]
requires:
  - phase: 35-trusted-publishing-release-automation
    provides: build artifact workflow
provides:
  - TestPyPI publish job using PyPI Trusted Publishing
  - TestPyPI trusted publisher setup documentation
  - Static tests that reject long-lived PyPI credentials
affects: [release-process, trusted-publishing]
tech-stack:
  added: []
  patterns: [oidc-publishing, token-free-release-docs]
key-files:
  created:
    - .github/TRUSTED_PUBLISHING.md
  modified:
    - .github/workflows/release.yml
    - tests/test_release_workflow.py
requirements-completed: [REL-02]
duration: reconstructed
completed: 2026-05-15
---

# Phase 35: Trusted Publishing Release Automation Summary

The release workflow now publishes manually dispatched builds to TestPyPI using OIDC Trusted Publishing and the already-built `python-package-distributions` artifact.

## Performance

- **Duration:** reconstructed from existing implementation
- **Completed:** 2026-05-15
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Added `publish-testpypi` with `needs: build`, `environment: testpypi`, and job-scoped `id-token: write`.
- Downloaded the previously uploaded `python-package-distributions` artifact into `dist`.
- Used `pypa/gh-action-pypi-publish@release/v1` with `repository-url: https://test.pypi.org/legacy/`.
- Documented TestPyPI Trusted Publishing values in `.github/TRUSTED_PUBLISHING.md`.
- Added tests that verify TestPyPI Trusted Publishing and reject token-based publishing inputs.

## Task Commits

No dedicated Phase 35 task commits were found in recent git history. This summary reconstructs the completed plan from the current files and passing tests so the milestone audit has the required GSD evidence.

## Files Created/Modified

- `.github/workflows/release.yml` - TestPyPI publish job.
- `.github/TRUSTED_PUBLISHING.md` - TestPyPI Trusted Publishing setup values.
- `tests/test_release_workflow.py` - TestPyPI and no-token release workflow tests.

## Decisions Made

- Scope OIDC permission to publish jobs only.
- Use TestPyPI as a manual dispatch path and keep production PyPI out of this plan.

## Deviations from Plan

- Summary was reconstructed after implementation because the original Phase 35 execution did not leave `35-*-SUMMARY.md` artifacts.

## Issues Encountered

- None in the current implementation evidence.

## Self-Check: PASSED

The release workflow and docs contain the REL-02 evidence expected by the plan.
