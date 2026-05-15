---
phase: 36-user-install-docs-and-release-validation
status: passed
verified_at: 2026-05-15T08:25:17Z
requirements_checked:
  - DOC-01
  - DOC-02
  - DOC-03
  - VAL-01
  - VAL-02
---

# Phase 36 Verification

## Result

Passed.

## Requirements

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DOC-01 | 36-01 | README/docs show `pip install corpulse` as the primary installation path. | passed | `README.md` contains `pip install corpulse`; `tests/test_package.py` asserts the PyPI-first install commands and rejects obsolete source-first wording. |
| DOC-02 | 36-01 | README/docs show `pip install corpulse[qdrant]` as the primary Qdrant installation path. | passed | `README.md` contains `pip install "corpulse[qdrant]"`; `tests/test_package.py` asserts this exact command. |
| DOC-03 | 36-01 | Maintainer has a release checklist covering version bump, build, TestPyPI validation, PyPI publish, and post-publish smoke checks. | passed | `.github/RELEASE_CHECKLIST.md` contains the release stages, Trusted Publishing no-token guidance, TestPyPI validation command, and production publish steps; `tests/test_release_workflow.py` asserts the checklist content. |
| VAL-01 | 36-02 | Maintainer can verify a clean environment install from the published PyPI package. | passed | `.github/RELEASE_CHECKLIST.md` documents the exact `/tmp/corpulse-pypi-smoke` clean venv commands and base import assertions; tests assert the VAL-01 fragments. |
| VAL-02 | 36-02 | Maintainer can verify a clean environment install from the published `corpulse[qdrant]` extra and wrapper surface. | passed | `.github/RELEASE_CHECKLIST.md` documents the exact `/tmp/corpulse-qdrant-smoke` clean venv commands and Qdrant wrapper import assertions; tests assert the VAL-02 fragments. |

## Checks

- `python -m pytest tests/test_package.py tests/test_release_workflow.py`
- Local build and opt-in install tests are covered by Phase 34 and referenced in the release checklist for pre-publish validation.

## Notes

- Published PyPI and TestPyPI smoke checks depend on external release state. Phase 36 records the exact commands and keeps them under static regression tests; real release execution remains a manual release step.
- The checklist explicitly prohibits PyPI API tokens for the Trusted Publishing workflow.

## Self-Check: PASSED
