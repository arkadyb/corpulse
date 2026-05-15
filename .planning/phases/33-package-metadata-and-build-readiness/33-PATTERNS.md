# Phase 33: Pattern Map

**Created:** 2026-05-15

## Existing Patterns

### Packaging Metadata

- `pyproject.toml` is the packaging source of truth.
- Hatchling is already established as the build backend.
- Optional extras are already declared in `[project.optional-dependencies]`.

### Runtime Version

- `corpulse/__init__.py` exposes `__version__`.
- Existing import tests already assert `corpulse.__version__` is a string.

### Package Tests

- `tests/test_package.py` uses direct text checks against `pyproject.toml`.
- `tests/test_import.py` verifies lazy import behavior for optional dependencies.

## Closest Analogs

| Planned File | Existing Analog | Pattern To Follow |
|--------------|-----------------|-------------------|
| `pyproject.toml` | existing `pyproject.toml` | Keep Hatchling and optional extras; add metadata without changing runtime deps. |
| `tests/test_package.py` | existing metadata smoke tests | Add explicit string/metadata checks in small focused tests. |
| `tests/test_import.py` | existing version/import tests | Preserve `corpulse.__version__` access and lazy optional imports. |
| `README.md` | existing install section | Keep concise bash install block; replace GitHub-first commands with PyPI-first commands. |

## Constraints

- Do not make optional integrations hard dependencies.
- Do not add release workflow files in Phase 33.
- Do not move package modules.
- Do not make PyPI publishing commands part of Phase 33 verification; only build/render locally.

---
*Pattern map: 2026-05-15*
