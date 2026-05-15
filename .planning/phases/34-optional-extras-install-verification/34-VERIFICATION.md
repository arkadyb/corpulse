---
phase: 34-optional-extras-install-verification
status: passed
verified_at: 2026-05-15T07:42:35Z
requirements_checked:
  - PKG-04
  - EXTRA-01
  - EXTRA-02
  - EXTRA-03
  - EXTRA-04
---

# Phase 34 Verification

## Result

Passed.

## Checks

- `python -m pytest tests/test_package.py tests/test_import.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_fastapi.py tests/test_report_helpers.py`
- `/tmp/corpulse-gsd-tools/bin/python -m build`
- `CORPULSE_RUN_INSTALL_TESTS=1 python -m pytest tests/test_distribution_installs.py`
- `git status --short dist build`

## Notes

- Base wheel install tests passed with optional integration packages absent from the clean venv.
- `corpulse[qdrant]`, `corpulse[postgres]`, `corpulse[postgres-async]`, and `corpulse[fastapi]` all installed cleanly from the rebuilt wheel in isolated venvs.
- The postgres extra is now binary-safe, so `import psycopg` works in the install matrix without relying on system libpq.
- `dist/` contains the rebuilt sdist and wheel, and `git status --short dist build` is clean.
