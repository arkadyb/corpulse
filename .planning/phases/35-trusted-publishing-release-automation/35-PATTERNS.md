# Phase 35: Trusted Publishing Release Automation - Patterns

**Mapped:** 2026-05-15
**Status:** Ready for planning

## Existing Patterns

- `tests/test_package.py` uses direct text checks against packaging and documentation files.
- Phase 33 and Phase 34 plans use artifact-oriented tests that skip or stay static when external systems are unavailable.
- `pyproject.toml` is the packaging source of truth and already supports `python -m build`.
- There is no existing `.github/workflows/` directory, so release automation starts from a new workflow file.

## New File Analogues

| New or Modified File | Closest Existing Analogue | Pattern To Follow |
|----------------------|---------------------------|-------------------|
| `.github/workflows/release.yml` | `pyproject.toml` build configuration | Keep release configuration explicit and small; do not add runtime dependencies. |
| `.github/TRUSTED_PUBLISHING.md` | `.planning/phases/34-optional-extras-install-verification/34-VALIDATION.md` | Separate out-of-repo manual setup from automated checks. |
| `tests/test_release_workflow.py` | `tests/test_package.py` | Use focused static assertions for exact strings and forbidden token references. |
| `tests/test_release_workflow.py` | `tests/test_distribution_installs.py` | Avoid live external service calls in default tests. |

## Constraints

- Do not publish to TestPyPI or PyPI during phase execution.
- Do not add PyPI API tokens or token secret names.
- Scope `id-token: write` to publish jobs, not the build job.
- Build artifacts once, upload them, and publish the downloaded artifacts.
- Represent production approval with `environment: pypi`; document required reviewer setup because GitHub environment protection is not stored in repo files.

## Verification Commands

- `python -m pytest tests/test_release_workflow.py`
- `python -m pytest tests/test_package.py`
- `python -m build`
- `actionlint .github/workflows/release.yml` if `actionlint` is locally installed

---
*Phase: 35-trusted-publishing-release-automation*
*Pattern mapping complete: 2026-05-15*
