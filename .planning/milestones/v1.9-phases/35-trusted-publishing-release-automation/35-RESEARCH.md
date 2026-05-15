# Phase 35: Trusted Publishing Release Automation - Research

**Researched:** 2026-05-15
**Status:** Ready for planning

## RESEARCH COMPLETE

## Phase Boundary

Phase 35 adds GitHub Actions automation that builds release artifacts once and publishes them through PyPI Trusted Publishing. It covers `REL-01`, `REL-02`, `REL-03`, and `REL-04`.

It does not perform the first real release, update public install docs, or validate published packages after release. Those remain Phase 36 concerns.

## Current State

- No `.github/workflows/` files exist yet.
- `pyproject.toml` uses Hatchling and can build wheel/sdist artifacts from the package source.
- Phase 33 and 34 established artifact and install verification tests:
  - `tests/test_package.py` checks package metadata and built artifact contents.
  - `tests/test_distribution_installs.py` verifies clean installs from built wheels when `CORPULSE_RUN_INSTALL_TESTS=1`.
- Release requirements for this phase are scoped to GitHub Actions, PyPI Trusted Publishing, TestPyPI, PyPI, and an explicit production release gate.

## Trusted Publishing Findings

Current official docs and action guidance support this implementation shape:

- PyPI Trusted Publishing uses OpenID Connect rather than a long-lived PyPI API token.
- GitHub Actions publish jobs need `permissions: id-token: write`; this permission should be job-scoped to publishing jobs rather than granted to the entire workflow.
- `pypa/gh-action-pypi-publish@release/v1` is the canonical publishing action for PyPI/TestPyPI in GitHub Actions.
- TestPyPI publishing uses the same action with `repository-url: https://test.pypi.org/legacy/`.
- GitHub environments are the repository-native way to add deployment gates. The workflow can name `environment: pypi`, but reviewer protection rules are configured in GitHub settings, so the repo should include explicit setup instructions and tests that the workflow uses the environment.

Sources checked:
- PyPI Trusted Publishers: https://docs.pypi.org/trusted-publishers/
- PyPI GitHub publisher setup: https://docs.pypi.org/trusted-publishers/adding-a-publisher/
- GitHub OIDC with PyPI: https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-pypi
- PyPA publish action: https://github.com/pypa/gh-action-pypi-publish
- GitHub deployment environments: https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment
- GitHub artifact actions: https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-what-your-workflow-does/storing-and-sharing-data-from-a-workflow

## Recommended Technical Approach

### Workflow Layout

Create one workflow file at `.github/workflows/release.yml`.

Triggers:

- `workflow_dispatch` for explicit TestPyPI validation runs.
- `push.tags: ["v*"]` for production PyPI publishing from version tags.

Jobs:

1. `build`
   - Runs on `ubuntu-latest`.
   - Uses `actions/checkout`.
   - Uses `actions/setup-python` with Python `3.12`.
   - Installs `.[dev]` and `build`.
   - Runs `python -m pytest`.
   - Runs `python -m build`.
   - Uploads `dist/*` as a single artifact, for example `python-package-distributions`.
   - Does not request `id-token: write`.

2. `publish-testpypi`
   - Needs `build`.
   - Runs only for `workflow_dispatch`.
   - Uses `environment: testpypi`.
   - Requests `permissions: id-token: write`.
   - Downloads the built artifact.
   - Publishes with `pypa/gh-action-pypi-publish@release/v1`.
   - Sets `repository-url: https://test.pypi.org/legacy/`.
   - Does not set `password`, `username`, `api-token`, or any PyPI secret.

3. `publish-pypi`
   - Needs `build`.
   - Runs only for `refs/tags/v*`.
   - Uses `environment: pypi`.
   - Requests `permissions: id-token: write`.
   - Downloads the built artifact.
   - Publishes with `pypa/gh-action-pypi-publish@release/v1`.
   - Does not set `password`, `username`, `api-token`, or any PyPI secret.

### Static Workflow Tests

Add `tests/test_release_workflow.py` so CI behavior is testable without contacting GitHub, TestPyPI, or PyPI.

Use `yaml.safe_load` if PyYAML is available in the environment. Because this repo does not currently declare PyYAML as a dev dependency, the test can parse the workflow text directly with `pathlib` and exact string checks. Text checks are enough for this phase because the requirements are about concrete workflow structure and forbidden secret usage.

Recommended assertions:

- `.github/workflows/release.yml` exists.
- The workflow contains `python -m pytest`.
- The workflow contains `python -m build`.
- The workflow uploads `dist/*`.
- The workflow uses `pypa/gh-action-pypi-publish@release/v1`.
- The workflow contains `repository-url: https://test.pypi.org/legacy/`.
- The workflow contains `environment: testpypi`.
- The workflow contains `environment: pypi`.
- The workflow contains `id-token: write`.
- The workflow contains no `password:`, `username:`, `api-token`, `PYPI_API_TOKEN`, or `__token__`.
- Production publish has a tag guard such as `startsWith(github.ref, 'refs/tags/v')`.

### External Setup Notes

Trusted Publishing requires out-of-repo settings. Add `.github/TRUSTED_PUBLISHING.md` with:

- TestPyPI trusted publisher values:
  - owner: `arkadyb`
  - repository: `corpulse`
  - workflow: `release.yml`
  - environment: `testpypi`
- PyPI trusted publisher values:
  - owner: `arkadyb`
  - repository: `corpulse`
  - workflow: `release.yml`
  - environment: `pypi`
- GitHub environment guidance:
  - Create `testpypi` and `pypi` environments.
  - Configure `pypi` with required reviewers or equivalent explicit approval gate.
  - Do not add PyPI API tokens as repository secrets.

This document is not a user-facing install doc. It is release automation setup guidance, so it belongs in Phase 35 rather than Phase 36.

## Validation Architecture

Phase 35 should be validated with:

1. Static release workflow tests:
   - `python -m pytest tests/test_release_workflow.py`
2. Existing packaging checks:
   - `python -m pytest tests/test_package.py`
3. Build check:
   - `/tmp/corpulse-gsd-tools/bin/python -m build` when that venv exists, otherwise `python -m build`
4. Optional local workflow syntax inspection if `actionlint` is installed:
   - `actionlint .github/workflows/release.yml`
   - This should be treated as optional because `actionlint` is not currently a project dependency.

No automated verification should publish to TestPyPI or PyPI during this phase.

## Files Likely To Change

- `.github/workflows/release.yml`
- `.github/TRUSTED_PUBLISHING.md`
- `tests/test_release_workflow.py`
- `tests/test_package.py` if package metadata tests need a release automation smoke assertion

## Planning Notes

- Keep `id-token: write` scoped to publish jobs.
- Keep build artifacts as the source of truth for both TestPyPI and PyPI publish jobs.
- Use GitHub environments to represent release gates in workflow YAML, but include manual setup instructions because reviewer protection rules are not stored in the repository.
- Avoid storing PyPI API tokens or secret names in workflow YAML.
- Do not run a publish during phase execution.

---
*Phase: 35-trusted-publishing-release-automation*
*Research complete: 2026-05-15*
