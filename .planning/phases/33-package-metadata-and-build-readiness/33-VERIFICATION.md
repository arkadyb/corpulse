---
phase: 33-package-metadata-and-build-readiness
status: passed
verified_at: 2026-05-15T07:25:34Z
requirements_checked:
  - PKG-01
  - PKG-02
  - PKG-03
---

# Phase 33 Verification

## Result

Passed.

## Checks

- `python -m pytest tests/test_package.py tests/test_import.py`
- `/tmp/corpulse-gsd-tools/bin/python -m build`
- `/tmp/corpulse-gsd-tools/bin/python -m twine check dist/*`

## Notes

- `corpulse.__version__` remains `0.1.0` while Hatchling reads the version dynamically from `corpulse/__init__.py`.
- The built artifacts include `README.md`, `LICENSE`, and `corpulse/__init__.py` in the sdist, and `corpulse/__init__.py` plus `.dist-info/METADATA` in the wheel.
- `README.md` now uses `pip install corpulse` and `pip install "corpulse[qdrant]"` as the primary install commands.
