---
phase: 35-trusted-publishing-release-automation
status: passed
verified_at: 2026-05-15T08:25:17Z
requirements_checked:
  - REL-01
  - REL-02
  - REL-03
  - REL-04
---

# Phase 35 Verification

## Result

Passed.

## Requirements

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| REL-01 | 35-01 | CI tests, builds, and stores the exact sdist/wheel artifacts intended for release. | passed | `.github/workflows/release.yml` has a build job that runs tests, runs `python -m build`, and uploads `dist/*` as `python-package-distributions`; tests assert this contract. |
| REL-02 | 35-02 | TestPyPI publishing uses GitHub Actions and PyPI Trusted Publishing. | passed | `publish-testpypi` depends on `build`, uses `environment: testpypi`, has job-scoped `id-token: write`, downloads the built artifact, and publishes via `pypa/gh-action-pypi-publish@release/v1`. |
| REL-03 | 35-03 | Tagged releases publish to PyPI using Trusted Publishing. | passed | `publish-pypi` runs only when `startsWith(github.ref, 'refs/tags/v')`, uses OIDC Trusted Publishing, and omits `repository-url` so the action targets PyPI. |
| REL-04 | 35-03 | PyPI publishing is protected by an explicit release gate. | passed | `publish-pypi` declares `environment: pypi`, and `.github/TRUSTED_PUBLISHING.md` instructs maintainers to configure required reviewers or equivalent explicit approval before first production release. |

## Checks

- `python -m pytest tests/test_release_workflow.py tests/test_package.py`
- `/tmp/corpulse-gsd-tools/bin/python -m build` when available, otherwise `python -m build`
- `actionlint .github/workflows/release.yml` when available
- `git status --short dist build`

## Notes

- The build job remains unprivileged beyond `contents: read`; OIDC permission is scoped to publish jobs.
- The workflow does not contain `password:`, `username:`, `api-token`, `PYPI_API_TOKEN`, `TEST_PYPI_API_TOKEN`, or `__token__`.
- The external GitHub `pypi` environment reviewer configuration cannot be inspected locally. It is documented as a required manual setup gate before first production release.

## Self-Check: PASSED
