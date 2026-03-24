# Coding Conventions

**Analysis Date:** 2026-03-24

## Naming Patterns

**Files:**
- Private modules use leading underscore in functions but not file names
- Public module names are lowercase with hyphens in package name: `rag-memento`
- Main API file: `memento.py`
- Database layer file: `db.py`
- Demo file: `demo.py`

**Functions:**
- Public functions use `snake_case`: `log_retrieval()`, `get_ghosts()`, `corpus_health()`
- Private/helper functions prefix with underscore: `_now()`, `_hash_query()`, `_vec_to_bytes()`, `_bytes_to_vec()`
- Internal methods (within classes) use underscore prefix: `_init()`, `_conn()`
- Section comments use double underscore and em-dashes for visual separation: `# ── ingestion ──`

**Variables:**
- Lowercase with underscores: `doc_id`, `query_hash`, `timestamp`, `embed_at`
- Local loop variables use short names: `d` (for dict), `r` (for row), `vec` (for vector), `i`/`j` (for indices)
- Unpacking uses clear names: `(doc_id, filename, embedding_base_key, is_popular)`
- Dictionary abbreviations where clear from context: `r_map` (retrieval map), `e_map` (engagement map)

**Types:**
- Modern Python type hints: `str`, `float`, `int`, `bool`, `dict`, `list`
- Union types use pipe operator: `float | None`, `list | np.ndarray | None`
- Dictionary types explicit: `dict[str, Any]`
- No return type annotation only where obvious (e.g., builders)

**Classes:**
- PascalCase: `Memento`, `DB`
- Single responsibility: `Memento` handles API/analysis, `DB` handles persistence only

## Code Style

**Formatting:**
- Line length: No strict limit enforced, but typically 80-100 characters
- Indentation: 4 spaces
- No trailing whitespace
- Single blank line between logical sections within methods
- Section comments use decorative separators (em-dashes with fixed character width)

**Linting:**
- No linter config files present (not enforced)
- However, style follows PEP 8 conventions
- Import organization follows Python standards

## Import Organization

**Order:**
1. Future imports: `from __future__ import annotations`
2. Standard library: `import hashlib`, `import re`, `import time`, `from datetime import ...`
3. Third-party: `import numpy as np`, `from sklearn.metrics.pairwise import cosine_similarity`
4. Local imports: `from .db import DB`

**Conditional imports:**
- Optional dependencies wrapped in try/except with feature flag
- Pattern seen in `memento.py`:
  ```python
  try:
      from sklearn.metrics.pairwise import cosine_similarity
      _SKLEARN = True
  except ImportError:
      _SKLEARN = False
  ```
- Same pattern for pandas in `to_dataframe()` method

**Path Aliases:**
- Relative imports only (no path aliases): `from .memento import Memento`, `from .db import DB`

## Error Handling

**Patterns:**
- Explicit `RuntimeError` with descriptive message when optional dependency missing:
  ```python
  if not _SKLEARN:
      raise RuntimeError(
          "scikit-learn is required for duplicate detection. "
          "Install it with: pip install scikit-learn"
      )
  ```
- Graceful degradation: optional dependencies don't block non-dependent features
- No bare `except` blocks; always catch specific exceptions
- Context managers used for resource management (seen in `DB._conn()`)

## Logging

**Framework:** No logging framework (uses `print()` for output)

**Patterns:**
- Console output via `print()` for user-facing messages in `cleanup_report()` and `report()`
- Status messages printed during demo: `print("Setting up corpus...")`, `print(f"  Registered {len(DOCS)} documents")`
- ASCII art/formatting: decorative lines `"─" * 60`, emoji indicators: `👻`, `💀`, `⚠`, `🕓`, `🔁`
- All output goes to stdout directly (no structured logging)

## Comments

**When to Comment:**
- Section headers with decorative separators separate major logical sections:
  ```python
  # ─────────────────────────────────────────────────────────────────────────────
  # helpers
  # ─────────────────────────────────────────────────────────────────────────────
  ```
- Inline comments explain logic thresholds/magic numbers:
  ```python
  if total_ret < 5:           # too little data to judge
  if eng_rate < 0.15:         # retrieved often, rarely acted on
  ```
- Comments on non-obvious algorithm steps: `# Group filenames by their base name (version token removed)`
- Comments in SQL strings as part of schema definition

**Docstrings:**
- Triple-quoted docstrings on public methods and classes
- Format: Single-line summary, blank line, optional extended description
- Example usage shown in docstrings when appropriate:
  ```python
  """
  Call this right after your vector DB search.

  Each item in *results* must contain at least ``doc_id``.
  Optional keys: ``filename``, ``score`` (float), ``embedding`` (list/array).

  Example::
      results = [...]
      memento.log_retrieval(results, query="how to install?")
  """
  ```
- Private functions have no docstrings (comments above or inline only)
- Module-level docstring at top of file

## Function Design

**Size:**
- Most functions 5-30 lines
- Analysis functions typically 15-25 lines due to query/filtering logic
- Utility functions very short (1-3 lines): `_now()`, `_hash_query()`, `_days_ago()`

**Parameters:**
- Functions explicitly list expected keys in docstrings
- Optional parameters default to `None` or sensible class defaults
- Constructor accepts configuration parameters: `ghost_threshold_days`, `duplicate_threshold`, etc.

**Return Values:**
- Consistent return types: `list[dict]` for analysis results
- Each dict in result list has consistent keys (documented in docstring)
- `None` return only where appropriate (e.g., when dependency missing and graceful fallback possible)
- Numeric return values rounded to 2-4 decimal places: `round(float(sim_matrix[i, j]), 4)`

## Module Design

**Exports:**
- Explicit `__all__` in `__init__.py`: `__all__ = ["Memento"]`
- Single public class exported at package level
- Version specified in `__init__.py`: `__version__ = "0.1.0"`

**Barrel Files:**
- Used in `__init__.py` to re-export main API: `from .memento import Memento`
- Makes package-level import simple: `from rag_memento import Memento`

**Module structure:**
- `__init__.py`: Minimal, only re-exports public API and version
- `memento.py`: Public `Memento` class with analysis and reporting methods
- `db.py`: Private `DB` class for persistence layer (context manager pattern)
- `demo.py`: Standalone demonstration script (not imported as module)

---

*Convention analysis: 2026-03-24*
