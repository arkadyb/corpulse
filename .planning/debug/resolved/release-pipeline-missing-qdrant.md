---
status: resolved
trigger: "GH Actions release pipeline failed after publishing tag: ModuleNotFoundError: No module named 'qdrant_client' while collecting tests/test_qdrant_helpers.py and tests/test_qdrant_wrapper.py"
created: "2026-05-15"
updated: "2026-05-15"
---

# Debug Session: Release Pipeline Missing Qdrant

## Symptoms

- Expected behavior: The tag-triggered release pipeline should run the pre-publish test gate successfully before building and publishing artifacts.
- Actual behavior: The Release workflow `build` job failed during pytest collection because `qdrant_client` was not installed.
- Error messages: `ModuleNotFoundError: No module named 'qdrant_client'` from `tests/test_qdrant_helpers.py` and `tests/test_qdrant_wrapper.py`.
- Timeline: First observed when checking GitHub Actions after publishing a tag.
- Reproduction: Push a `v*` tag so `.github/workflows/release.yml` runs and executes `python -m pytest` after installing only `".[dev]" build`.

## Current Focus

- hypothesis: The release workflow runs all tests but installs only development tooling, not optional extras required by default-collected integration tests.
- test: Inspect release workflow install command and Qdrant tests' import behavior.
- expecting: `release.yml` installs `".[dev]"`, while Qdrant tests import `qdrant_client` at module import time.
- next_action: Install Qdrant/FastAPI extras in the release pre-publish test environment and lock the workflow contract in tests.

## Evidence

- timestamp: 2026-05-15
  finding: `.github/workflows/release.yml` installed `".[dev]" build`, then ran `python -m pytest`.
- timestamp: 2026-05-15
  finding: `pyproject.toml` defines `dev` as pytest tooling only and defines `qdrant` separately as `qdrant-client>=1.7`.
- timestamp: 2026-05-15
  finding: `tests/test_qdrant_helpers.py` and `tests/test_qdrant_wrapper.py` import `qdrant_client` during module collection, so a missing dependency is a collection error rather than a skipped test.
- timestamp: 2026-05-15
  finding: `tests/test_fastapi.py` skips when FastAPI/httpx are missing, but installing the `fastapi` extra in the release gate lets that integration coverage run too.
- timestamp: 2026-05-15
  finding: After installing Qdrant locally, focused tests exposed `NameError: name 'inspect' is not defined` in `ensure_collection()`.

## Eliminated

- hypothesis: Trusted Publishing failed.
  reason: The failure occurred in the `build` job before artifact publishing jobs.
- hypothesis: The package forgot to declare the Qdrant extra.
  reason: `pyproject.toml` declares `qdrant = ["qdrant-client>=1.7"]`.

## Resolution

- root_cause: Release workflow test environment did not install optional extras required by tests included in the full pytest suite.
- fix: Changed release workflow install command to `python -m pip install ".[dev,qdrant,fastapi]" build` and imported `inspect` in `corpulse/integrations/qdrant.py`.
- verification: Run release workflow contract test and Qdrant/FastAPI tests locally.
- files_changed:
  - `.github/workflows/release.yml`
  - `corpulse/integrations/qdrant.py`
  - `tests/test_release_workflow.py`
  - `.planning/debug/release-pipeline-missing-qdrant.md`
