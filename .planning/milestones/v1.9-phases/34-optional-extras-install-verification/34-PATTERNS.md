# Phase 34: Optional Extras Install Verification - Patterns

**Mapped:** 2026-05-15
**Status:** Ready for planning

## Existing Patterns

- `tests/test_import.py` is the local source for package import and lazy optional dependency checks.
- `tests/test_package.py` already checks package metadata and built artifact contents.
- `tests/test_postgres_backend.py` and `tests/test_async_postgres_backend.py` use monkeypatched loaders to verify missing dependency behavior without requiring real drivers.
- `tests/test_report_helpers.py` uses monkeypatched imports for pandas and tabulate behavior.
- `corpulse/integrations/qdrant.py` and `corpulse/fastapi.py` already include explicit `pip install corpulse[...]` guidance.

## New File Analogues

| New or Modified File | Closest Existing Analogue | Pattern To Follow |
|----------------------|---------------------------|-------------------|
| `tests/test_distribution_installs.py` | `tests/test_package.py` | Artifact-aware tests that inspect `dist/` and skip when prerequisites are absent. |
| `tests/test_distribution_installs.py` | `tests/test_import.py` | Assert package-root import behavior and lazy optional dependencies. |
| `corpulse/backends/postgres.py` | `corpulse/integrations/qdrant.py` | Missing optional dependency error should include `pip install corpulse[extra]`. |
| `corpulse/backends/postgres_async.py` | `corpulse/fastapi.py` | Missing optional dependency error should name the feature and the install command. |
| `tests/test_postgres_backend.py` | existing `test_postgres_backend_requires_psycopg` | Keep monkeypatch-loader tests, update expected message. |
| `tests/test_async_postgres_backend.py` | existing `test_async_postgres_backend_requires_asyncpg` | Keep async loader test, update expected message. |

## Constraints

- Do not make Qdrant, Postgres, async Postgres, FastAPI, pandas, or tabulate base dependencies.
- Do not add pandas or tabulate extras in this phase; they remain ad hoc optional helpers.
- Do not require external service connections during isolated install checks.
- Do not track `dist/`, `build/`, or `*.egg-info/` outputs.

## Verification Commands

- `python -m pytest tests/test_import.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_fastapi.py tests/test_report_helpers.py`
- `python -m build`
- `CORPULSE_RUN_INSTALL_TESTS=1 python -m pytest tests/test_distribution_installs.py`

---
*Phase: 34-optional-extras-install-verification*
*Pattern mapping complete: 2026-05-15*
