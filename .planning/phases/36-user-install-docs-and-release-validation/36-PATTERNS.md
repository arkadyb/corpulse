# Phase 36: User Install Docs and Release Validation - Patterns

**Mapped:** 2026-05-15
**Status:** Ready for planning

## Existing Patterns

- `README.md` is the public install and quickstart surface.
- `.github/TRUSTED_PUBLISHING.md` is the existing release setup document for PyPI/TestPyPI Trusted Publishing.
- `tests/test_package.py` uses direct text assertions for package metadata and README install wording.
- `tests/test_release_workflow.py` uses direct text assertions for release workflow and release setup docs.
- `tests/test_distribution_installs.py` is the existing isolated local wheel install test harness.

## New File Analogues

| New or Modified File | Closest Existing Analogue | Pattern To Follow |
|----------------------|---------------------------|-------------------|
| `.github/RELEASE_CHECKLIST.md` | `.github/TRUSTED_PUBLISHING.md` | Plain maintainer-facing markdown with exact commands and no API-token flow. |
| `README.md` | existing Installation section | Keep PyPI-first commands concise; add only a small maintainer release link. |
| `tests/test_release_workflow.py` | existing trusted-publishing tests | Add static checklist assertions beside workflow assertions. |
| `tests/test_package.py` | `test_readme_uses_pypi_install_commands` | Keep README command assertions exact. |
| `tests/test_distribution_installs.py` | existing opt-in wheel install tests | Reuse for pre-publish local artifact verification, not published PyPI smoke checks. |

## Constraints

- Do not add API token instructions or secret names.
- Do not require external PyPI/TestPyPI network calls in the normal automated test suite.
- Do not make `qdrant-client` a base dependency.
- Do not track `dist/`, `build/`, or `*.egg-info/` artifacts.
- Published PyPI validation is manual/external and should be expressed as checklist commands.

## Verification Commands

- `python -m pytest tests/test_package.py tests/test_release_workflow.py`
- `python -m build`
- `CORPULSE_RUN_INSTALL_TESTS=1 python -m pytest tests/test_distribution_installs.py`

---
*Phase: 36-user-install-docs-and-release-validation*
*Pattern mapping complete: 2026-05-15*
