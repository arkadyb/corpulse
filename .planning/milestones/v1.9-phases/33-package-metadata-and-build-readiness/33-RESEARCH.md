# Phase 33: Package Metadata and Build Readiness - Research

**Researched:** 2026-05-15
**Status:** Ready for planning

## RESEARCH COMPLETE

## Phase Boundary

Phase 33 prepares the package itself for PyPI. It covers package metadata, version consistency, README rendering, and source/wheel artifact build verification for `PKG-01`, `PKG-02`, and `PKG-03`.

It does not prove `pip install corpulse[qdrant]` from artifacts; that belongs to Phase 34.

## Current State

- `pyproject.toml` uses Hatchling with `hatchling>=1.27`.
- `pyproject.toml` declares static `version = "0.1.0"`.
- `corpulse/__init__.py` also declares `__version__ = "0.1.0"`.
- README install instructions still say GitHub install and "not yet on PyPI".
- `python -m build` failed in the current environment because the `build` module is not installed.
- `tests/test_package.py` covers basic metadata but not classifiers, project URLs, README/license artifact inclusion, or version drift.

## Recommended Technical Approach

### Version Source

Use `corpulse/__init__.py` as the runtime version source and configure Hatchling dynamic version extraction:

```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
path = "corpulse/__init__.py"
```

This preserves `corpulse.__version__` for users while removing the duplicate static version from `pyproject.toml`.

### Metadata Additions

Add PyPI-oriented metadata to `pyproject.toml`:

- `authors`
- `keywords`
- `classifiers`
- additional `[project.urls]` entries such as `Homepage`, `Issues`, and `Source`
- explicit source distribution include rules for `corpulse`, `README.md`, `LICENSE`, and `pyproject.toml`

The package should keep dependencies and optional extras unchanged in this phase.

### README Rendering

Use `twine check dist/*` after building artifacts. This is the low-cost validation that PyPI long description metadata is parseable.

### Build Validation

Use the PyPA build frontend:

```bash
python -m build
python -m twine check dist/*
```

If the current environment lacks these tools, install them in the existing virtual environment or document the missing tool as a blocker during execution.

## Validation Architecture

Phase 33 should be validated with:

1. Static tests checking `pyproject.toml` contains required PyPI metadata and dynamic version configuration.
2. Runtime/version tests checking `corpulse.__version__` remains available and metadata version matches it after building.
3. Artifact commands:
   - `python -m build`
   - `python -m twine check dist/*`
4. Artifact inspection confirming `README.md`, `LICENSE`, and `corpulse/` files are present in the sdist and wheel as appropriate.

## Files Likely To Change

- `pyproject.toml`
- `corpulse/__init__.py`
- `README.md`
- `tests/test_package.py`
- `tests/test_import.py`
- optionally `.gitignore` if `dist/` is not ignored

## Planning Notes

- Keep install verification from PyPI and optional extras for Phase 34.
- Avoid adding release workflows in this phase; that is Phase 35.
- Avoid changing package import paths or public API names.

---
*Phase: 33-package-metadata-and-build-readiness*
*Research complete: 2026-05-15*
