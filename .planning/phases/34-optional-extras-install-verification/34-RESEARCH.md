# Phase 34: Optional Extras Install Verification - Research

**Researched:** 2026-05-15
**Status:** Ready for planning

## RESEARCH COMPLETE

## Phase Boundary

Phase 34 proves that the artifacts produced by Phase 33 install correctly in clean environments and that optional integrations remain explicit extras. It covers `PKG-04`, `EXTRA-01`, `EXTRA-02`, `EXTRA-03`, and `EXTRA-04`.

It does not publish to PyPI or TestPyPI. It should install from local built artifacts under `dist/`.

## Current State

- `pyproject.toml` declares base dependencies only as `numpy>=1.24` and `scikit-learn>=1.3`.
- Optional extras are declared:
  - `qdrant = ["qdrant-client>=1.7"]`
  - `postgres = ["psycopg[pool]>=3.2"]`
  - `postgres-async = ["asyncpg>=0.29"]`
  - `fastapi = ["fastapi>=0.110.0", "pydantic>=2.0.0"]`
- `tests/test_import.py` already checks lazy imports for Qdrant, psycopg, asyncpg, and package-root `AsyncCorpulse`.
- Qdrant wrapper constructors raise `ImportError` with `pip install corpulse[qdrant]`.
- Postgres and async Postgres missing dependency errors currently say `Install corpulse[postgres].` and `Install corpulse[postgres-async].`; these should become explicit `pip install ...` guidance.
- FastAPI missing dependency guidance already says `pip install corpulse[fastapi]`.
- `to_dataframe()` raises `RuntimeError("pip install pandas to use to_dataframe()")`; pandas is not declared as a package extra.
- `report()` treats `tabulate` as an opportunistic enhancement and falls back to plain text without raising.

## Recommended Technical Approach

### Install Verification Harness

Add a pytest module dedicated to distribution install verification, likely `tests/test_distribution_installs.py`. The test should create temporary virtual environments with `venv`, install from the newest local wheel in `dist/`, and run subprocess Python snippets inside the venv.

Because isolated install tests may require network access for dependencies and are slower than normal unit tests, gate them behind an environment variable such as `CORPULSE_RUN_INSTALL_TESTS=1`. Normal test runs should skip these tests with a clear reason. Execution plans should still run the gated tests explicitly.

Recommended helper functions:

- `_repo_root() -> pathlib.Path`
- `_latest_wheel() -> pathlib.Path`
- `_create_venv(tmp_path: pathlib.Path) -> pathlib.Path`
- `_python(venv_dir: pathlib.Path) -> pathlib.Path`
- `_run(py: pathlib.Path, args: list[str]) -> subprocess.CompletedProcess[str]`
- `_install_wheel(py: pathlib.Path, wheel: pathlib.Path, extra: str | None = None) -> None`

For extra installs from a local wheel, use a direct URL requirement with extras:

```bash
python -m pip install 'corpulse[qdrant] @ file:///absolute/path/to/corpulse-0.1.0-py3-none-any.whl'
```

This lets pip resolve optional extra dependencies from package indexes while installing corpulse from the built artifact.

### Base Install Assertions

After installing the base wheel in a clean venv:

- `import corpulse` succeeds.
- `corpulse.__version__ == "0.1.0"`.
- `from corpulse import Corpulse` succeeds.
- `importlib.util.find_spec("qdrant_client") is None`.
- `importlib.util.find_spec("psycopg") is None`.
- `importlib.util.find_spec("asyncpg") is None`.
- `importlib.util.find_spec("fastapi") is None`.
- `importlib.util.find_spec("pandas") is None`.
- `importlib.util.find_spec("tabulate") is None`.

This directly covers `PKG-04` and `EXTRA-02`.

### Optional Extra Install Matrix

Verify the local wheel can install these extras in clean venvs:

- `qdrant`
- `postgres`
- `postgres-async`
- `fastapi`

For each extra, assert the relevant dependency can be imported:

- `qdrant-client`: `import qdrant_client`
- `postgres`: `import psycopg`
- `postgres-async`: `import asyncpg`
- `fastapi`: `import fastapi; import pydantic`

For Qdrant specifically, also assert the public wrapper surface is importable after installing `corpulse[qdrant]`:

```python
from corpulse import QdrantCorpulseClient, AsyncQdrantCorpulseClient
assert QdrantCorpulseClient.__name__ == "QdrantCorpulseClient"
assert AsyncQdrantCorpulseClient.__name__ == "AsyncQdrantCorpulseClient"
```

This covers `EXTRA-01` and `EXTRA-04`.

### Missing-Extra Guidance

Tighten all missing optional integration messages to include actionable install commands:

- Qdrant: `pip install corpulse[qdrant]`
- Postgres: `pip install corpulse[postgres]`
- Async Postgres: `pip install corpulse[postgres-async]`
- FastAPI: `pip install corpulse[fastapi]`
- pandas helper: `pip install pandas`

Tabulate should remain a fallback-only optional dependency: no error should be raised when it is absent.

## Validation Architecture

Phase 34 should be validated with:

1. Unit tests for missing-extra guidance and lazy imports:
   - `python -m pytest tests/test_import.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_fastapi.py tests/test_report_helpers.py`
2. Build artifact creation:
   - `/tmp/corpulse-gsd-tools/bin/python -m build` or `python -m build` when available.
3. Gated isolated install tests:
   - `CORPULSE_RUN_INSTALL_TESTS=1 python -m pytest tests/test_distribution_installs.py`
4. Final focused suite:
   - `python -m pytest tests/test_package.py tests/test_import.py tests/test_distribution_installs.py`

## Files Likely To Change

- `tests/test_distribution_installs.py`
- `tests/test_package.py`
- `tests/test_postgres_backend.py`
- `tests/test_async_postgres_backend.py`
- `tests/test_fastapi.py`
- `tests/test_report_helpers.py`
- `corpulse/backends/postgres.py`
- `corpulse/backends/postgres_async.py`
- optionally `README.md` if constraints need documentation

## Planning Notes

- Keep generated `dist/` artifacts untracked.
- Do not add pandas or tabulate as first-party extras unless a separate product decision is made.
- Do not require live Qdrant, Postgres, or FastAPI server processes; this phase verifies package installation and import surfaces only.
- Keep isolated install tests opt-in for normal development speed, but require them in the phase execution plan.

---
*Phase: 34-optional-extras-install-verification*
*Research complete: 2026-05-15*
