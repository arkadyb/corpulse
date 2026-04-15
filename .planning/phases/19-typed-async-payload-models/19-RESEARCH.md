# Phase 19: Typed Async Payload Models - Research

**Researched:** 2026-04-15
**Domain:** Python Typing / API Modeling
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MODEL-01 | Typed models for AsyncCorpulse.report() payloads. | Defined `ReportPayload` and sub-models mirroring existing structure. |
| MODEL-02 | Typed models for AsyncCorpulse.cleanup_report() payloads. | Defined `CleanupPayload` and sub-models mirroring existing structure. |
| MODEL-03 | Backward-compatible typed integration. | `TypedDict` ensures builders return valid dicts while providing types for IDEs. |
| MODEL-04 | No overloading of cleanup_report(). | Research confirms `cleanup_report()` remains analysis-only; mutating APIs will be separate. |
</phase_requirements>

## Summary

This phase introduces typed models for the `AsyncCorpulse.report()` and `AsyncCorpulse.cleanup_report()` payloads. The current implementation returns generic `dict[str, Any]` objects, which lack IDE support and static analysis for consumers. 

The research confirms that `typing.TypedDict` is the optimal solution for this project. It provides the necessary type hinting and structured modeling while maintaining full runtime backward compatibility with existing dict-based consumers. The project already uses `TypedDict` for database row models in `corpulse/backends/base.py`, establishing a clear precedent.

**Primary recommendation:** Centralize all API payload models in a new `corpulse/models.py` file, update the internal builders in `corpulse/core.py` to return these typed models, and update the async method type hints in `corpulse/async_core.py`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typing.TypedDict` | Built-in (3.8+) | Model definitions | Zero runtime overhead, full dict compatibility |
| `typing.List` | Built-in (3.9+) | Type hinting collections | Native Python typing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| `corpulse/models.py` | New | Centralized types | For both sync and async consumers |

**Installation:**
No new packages are required.

## Architecture Patterns

### Recommended Project Structure
```
corpulse/
├── models.py        # New: Typed models for all public API payloads
├── core.py          # Updated: Use models in internal _build_* functions
└── async_core.py    # Updated: Typed return values for public async methods
```

### Pattern 1: Centralized Type Modeling
Instead of defining types in `async_core.py`, they should live in a standalone `models.py`. This avoids circular imports and allows future reuse by sync methods or integration layers.

### Pattern 2: Explicit Section Types
Since `TypedDict` does not support generics in Python 3.10, each report section (ghosts, obsolete, etc.) should have its own specific `TypedDict` definition to ensure full type safety for nested lists.

### Anti-Patterns to Avoid
- **Hand-rolling classes:** Using `class` or `dataclass` would break backward compatibility as they are not dictionaries at runtime.
- **Generic `dict[str, Any]`:** Continuing to use untyped dicts makes the library harder to use in typed environments.
- **Circular Imports:** Defining models in `core.py` and using them in `async_core.py` while `core.py` also imports from `async_core.py` (though not currently the case) should be avoided by using a dedicated `models.py`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Object mapping | Custom `.asdict()` | `TypedDict` | `TypedDict` is already a dict; no mapping needed. |
| Model Validation | Custom validators | `TypedDict` | Static analysis is sufficient; runtime overhead should be avoided. |

## Common Pitfalls

### Pitfall 1: Type Inconsistency
**What goes wrong:** `engagement_rate` is a `str` (e.g., `"15%"`) in the `report()` payload but a `float` (e.g., `0.15`) in other contexts.
**Why it happens:** Historical implementation choices for specific outputs.
**How to avoid:** Define separate models for each payload that mirror existing behavior exactly to avoid breaking changes.

### Pitfall 2: Key Renaming
**What goes wrong:** Renaming keys for "consistency" (e.g., `doc_id` vs `id`) breaks existing consumers.
**How to avoid:** Use exact key names from the current `dict` structures in the `TypedDict` definitions.

## Code Examples

### Report Payload Models
```python
# corpulse/models.py

from __future__ import annotations
from typing import TypedDict, List

class ReportRow(TypedDict):
    filename: str
    retrievals: int
    engagement_rate: str  # e.g., "15%"
    status: str
    status_display: str

class ReportSummary(TypedDict):
    total_docs: int
    window_days: int
    bloat_warning: bool
    noise_pct: float
    ghosts: int
    obsolete: int
    duplicates: int
    stale: int
    recommendation: str

class ReportPayload(TypedDict):
    summary: ReportSummary
    rows: List[ReportRow]
```

### Cleanup Report Payload Models
```python
# corpulse/models.py

class GhostItem(TypedDict):
    doc_id: str
    filename: str

class ObsoleteItem(TypedDict):
    doc_id: str
    filename: str
    superseded_by: str

class SuspectItem(TypedDict):
    doc_id: str
    filename: str
    retrievals: int
    engagement_rate: float  # Note: float here, not str

class GhostSection(TypedDict):
    count: int
    top5: List[GhostItem]
    overflow: int

class CleanupPayload(TypedDict):
    total_docs: int
    noise_pct: float
    bloat_warning: bool
    recommendation: str
    ghost_threshold_days: int
    ghosts: GhostSection
    obsolete: ObsoleteSection  # Similarly defined
    stale: StaleSection        # Similarly defined
    suspects: SuspectSection   # Similarly defined
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Generic `dict` | `TypedDict` | This phase | Better DX, IDE autocompletion, static safety |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `TypedDict` is the preferred project pattern | Summary | Misalignment with project style |

## Open Questions (RESOLVED)

1. **Consolidation of backend types? (RESOLVED)**
   - Decision: Yes, move all `TypedDict` models from `corpulse/backends/base.py` (like `DocumentRow`, `ReportRow`, etc.) to the new `corpulse/models.py` for a unified, import-safe type system across the library.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Core Runtime | ✓ | 3.14 | Required >= 3.10 |
| typing.TypedDict | Models | ✓ | Built-in | — |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml |
| Quick run command | `pytest tests/test_async_core_integration.py` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODEL-01 | report() returns TypedDict | unit | `pytest tests/test_async_core_integration.py` | ✅ |
| MODEL-02 | cleanup_report() returns TypedDict | unit | `pytest tests/test_async_core_integration.py` | ✅ |
| MODEL-03 | Integration doesn't break dicts | unit | `pytest tests/test_async_core_integration.py` | ✅ |
| MODEL-04 | No overloading of cleanup_report() | unit | `pytest tests/test_async_core_integration.py` | ✅ |

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements. Typing will be verified via static analysis (e.g., `mypy` or `pyright`).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | `TypedDict` (static) |

## Sources

### Primary (HIGH confidence)
- `corpulse/async_core.py` - Current payload structures
- `corpulse/core.py` - Internal builder functions
- `corpulse/backends/base.py` - Existing `TypedDict` patterns

### Metadata

**Confidence breakdown:**
- Standard stack: HIGH - `TypedDict` is standard Python
- Architecture: HIGH - Centralization is a proven pattern
- Pitfalls: HIGH - Inconsistencies were explicitly identified

**Research date:** 2026-04-15
**Valid until:** 2026-05-15
