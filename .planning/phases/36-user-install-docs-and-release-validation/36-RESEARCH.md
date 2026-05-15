# Phase 36: User Install Docs and Release Validation - Research

**Created:** 2026-05-15
**Status:** Complete

## Research Question

What needs to be true to plan Phase 36 well: make PyPI installation the user-facing path and validate the first release end to end?

## Phase Scope

Phase 36 closes the v1.9 release-readiness milestone by turning the package work from Phases 33-35 into user-facing release instructions and smoke checks.

Requirements:

- DOC-01: README/docs show `pip install corpulse` as the primary installation command.
- DOC-02: README/docs show `pip install corpulse[qdrant]` as the primary Qdrant integration command.
- DOC-03: Maintainer has a release checklist covering version bump, build, TestPyPI validation, PyPI publish, and post-publish smoke checks.
- VAL-01: Maintainer can verify a clean environment install from the published PyPI package.
- VAL-02: Maintainer can verify a clean environment install from the published `corpulse[qdrant]` extra and instantiate/import the Qdrant wrapper surface.

## Current Repo State

- `README.md` already has a concise Installation section with:
  - `pip install corpulse`
  - `pip install "corpulse[qdrant]"`
  - source install fallback
- `tests/test_package.py` already includes `test_readme_uses_pypi_install_commands`, covering DOC-01 and DOC-02 at the static README level.
- `tests/test_distribution_installs.py` already validates local wheel installs for:
  - base wheel import without optional dependencies
  - optional extras from wheel artifacts
  - Qdrant wrapper surface from a wheel installed with the `qdrant` extra
- `.github/workflows/release.yml` already builds artifacts, publishes to TestPyPI on manual dispatch, and publishes to PyPI from `v*` tags.
- `.github/TRUSTED_PUBLISHING.md` documents the Trusted Publishing setup and environment gates.

## External Release Guidance

Primary source checks:

- PyPI Trusted Publishing docs state that GitHub Actions publishing via `pypa/gh-action-pypi-publish@release/v1` does not need usernames, passwords, or API tokens when `id-token: write` is available to the publish job.
- PyPI Trusted Publishing docs recommend a GitHub environment such as `pypi` for release jobs, and note job-level `id-token: write` as the least-exposure option.
- PyPI Trusted Publisher configuration for GitHub Actions depends on owner, repository, workflow filename, and optionally environment name matching the workflow claims.
- Python Packaging User Guide documents TestPyPI installation with:
  - `python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ your-package`

Implication for Phase 36: the release checklist should make TestPyPI and PyPI install validation explicit and should avoid token-based publishing instructions.

## Planning Implications

### Documentation

The plan should not invent a large docs site. The existing project docs surface is README plus `.github/TRUSTED_PUBLISHING.md`, so add a focused release checklist document under `.github/` and link it from README or Trusted Publishing docs.

Recommended new file:

- `.github/RELEASE_CHECKLIST.md`

Recommended README update:

- Keep PyPI install commands primary.
- Add a short release/maintainer reference link to `.github/RELEASE_CHECKLIST.md`.

### Automated Tests

Add static tests to prevent release checklist drift:

- Checklist contains `Version bump`.
- Checklist contains `python -m build`.
- Checklist contains TestPyPI validation using `--index-url https://test.pypi.org/simple/`.
- Checklist contains PyPI publish via `git tag v`.
- Checklist contains post-publish smoke checks for `pip install corpulse` and `pip install "corpulse[qdrant]"`.
- Checklist does not mention PyPI token secrets.

Existing test file to extend:

- `tests/test_release_workflow.py`

### Manual Validation

Published package validation cannot be fully automated before the package exists on PyPI. The executable plan should include manual checkpoints with exact commands:

Base PyPI smoke:

```bash
python -m venv /tmp/corpulse-pypi-smoke
/tmp/corpulse-pypi-smoke/bin/python -m pip install --upgrade pip
/tmp/corpulse-pypi-smoke/bin/python -m pip install corpulse
/tmp/corpulse-pypi-smoke/bin/python - <<'PY'
import corpulse
from corpulse import Corpulse
print(corpulse.__version__)
assert callable(Corpulse)
PY
```

Qdrant PyPI smoke:

```bash
python -m venv /tmp/corpulse-qdrant-smoke
/tmp/corpulse-qdrant-smoke/bin/python -m pip install --upgrade pip
/tmp/corpulse-qdrant-smoke/bin/python -m pip install "corpulse[qdrant]"
/tmp/corpulse-qdrant-smoke/bin/python - <<'PY'
import qdrant_client
from corpulse import AsyncQdrantCorpulseClient, QdrantCorpulseClient
assert QdrantCorpulseClient.__name__ == "QdrantCorpulseClient"
assert AsyncQdrantCorpulseClient.__name__ == "AsyncQdrantCorpulseClient"
assert qdrant_client.__name__ == "qdrant_client"
PY
```

TestPyPI smoke should use TestPyPI as the package index and PyPI as fallback for dependencies:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ corpulse
```

## Validation Architecture

Automated validation should be split into:

- Static docs tests in `tests/test_package.py` or `tests/test_release_workflow.py`.
- Local build and existing isolated wheel tests before release:
  - `python -m build`
  - `CORPULSE_RUN_INSTALL_TESTS=1 python -m pytest tests/test_distribution_installs.py`
- Manual clean-environment smoke checks after TestPyPI and PyPI publish.

Manual checks are acceptable for VAL-01 and VAL-02 because they depend on an externally published package. The plan must still make them exact and auditable in `.github/RELEASE_CHECKLIST.md`.

## Risks

- Published package names and versions are immutable. The checklist must require version bump before TestPyPI/PyPI attempts.
- TestPyPI often lacks dependencies, so validation should use PyPI as an extra index for dependencies.
- Production PyPI publish depends on external GitHub environment approval configuration, already documented in Phase 35.
- The release checklist should not tell maintainers to use API tokens, because the release workflow is Trusted Publishing based.

## Recommended Plan Shape

1. Documentation lock:
   - Add `.github/RELEASE_CHECKLIST.md`.
   - Link it from README and/or `.github/TRUSTED_PUBLISHING.md`.
   - Add static tests for checklist content and README install commands.
2. Release validation commands:
   - Encode exact TestPyPI and PyPI smoke commands in the checklist.
   - Add tests that assert commands and no-token guidance are present.
3. Final release readiness verification:
   - Run release docs tests.
   - Run local build.
   - Run opt-in install tests from local wheel.
   - Leave explicit manual checkpoints for externally published package validation.

## RESEARCH COMPLETE
