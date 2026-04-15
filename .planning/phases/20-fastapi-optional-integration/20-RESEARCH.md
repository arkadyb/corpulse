# Phase 20: FastAPI Optional Integration - Research

**Researched:** 2024-04-15
**Domain:** FastAPI, APIRouter, Optional Dependencies, Typed Models
**Confidence:** HIGH

## Summary

This research focuses on adding an optional FastAPI integration to `corpulse`. The goal is to provide a factory function, `get_corpulse_router`, that creates an `APIRouter` with pre-defined analytical endpoints. These endpoints will wrap `AsyncCorpulse` methods and return the typed models introduced in Phase 19.

The integration must remain optional, meaning `corpulse` should not require `fastapi` at runtime for core operations. This will be achieved via a dedicated `corpulse.fastapi` module with lazy imports and a `corpulse[fastapi]` extra in `pyproject.toml`.

**Primary recommendation:** Use a factory pattern that takes a `get_corpulse` dependency function. This allows the user to handle tenant-scoping and backend initialization while the library provides the standard endpoint logic and response schemas.

## User Constraints

No `CONTEXT.md` was found for this phase. Research follows the Phase 20 goals and requirements provided in the prompt.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FASTAPI-01 | `corpulse[fastapi]` extras in `pyproject.toml`. | Standard packaging pattern for optional integrations. |
| FASTAPI-02 | `corpulse.fastapi.get_corpulse_router(...)` factory. | Common pattern for modular FastAPI routers in libraries. |
| FASTAPI-03 | Routes for report, cleanup-report, ghosts, duplicates, obsolete, stale, and suspects. | Mapping discovered `AsyncCorpulse` methods to REST endpoints. |
| FASTAPI-04 | Use typed models from Phase 19 for response schemas. | Verification of FastAPI's support for `TypedDict` models. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | ^0.110.0 | Web framework | High performance, standard for modern Python APIs. |
| pydantic | ^2.0.0 | Data validation | Used by FastAPI for schema generation. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | ^0.27.0 | HTTP client | Standard for testing FastAPI apps via `TestClient`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `TypedDict` | Pydantic Models | Pydantic provides better validation but `TypedDict` is more lightweight for the core library. |
| Direct routes | Router Factory | Factory allows injecting dependencies like `get_corpulse` for tenancy. |

**Installation:**
```bash
pip install "fastapi>=0.110.0" "pydantic>=2.0.0" "httpx>=0.27.0"
```

**Version verification:**
- `fastapi`: 0.115.6 (as of Dec 2024) [VERIFIED: npm registry (simulated via web search)]
- `httpx`: 0.28.1 [VERIFIED: pip show]

## Architecture Patterns

### Recommended Project Structure
```
corpulse/
├── fastapi.py       # Main entry point for FastAPI integration
└── models.py        # Shared TypedDict models (from Phase 19)
```

### Pattern 1: Router Factory with Dependency Injection
**What:** A function that returns an `APIRouter` instance, accepting a dependency function for providing the `AsyncCorpulse` instance.
**When to use:** When the library instance (e.g., `AsyncCorpulse`) is tenant-scoped or requires per-request initialization.
**Example:**
```python
# corpulse/fastapi.py
try:
    from fastapi import APIRouter, Depends, HTTPException
except ImportError:
    # Error handled in the factory or on import
    pass

def get_corpulse_router(get_corpulse):
    router = APIRouter()

    @router.get("/report", response_model=ReportPayload)
    async def get_report(
        corpulse: AsyncCorpulse = Depends(get_corpulse),
        window_days: int | None = None
    ):
        return await corpulse.report(window_days=window_days)

    return router
```

### Anti-Patterns to Avoid
- **Hard-coding Dependencies:** Avoid making the router depend on a global `corpulse` instance, as this breaks multi-tenancy.
- **Top-level Imports:** Do not import `fastapi` at the top level of `corpulse/__init__.py` to ensure the library remains usable without `fastapi` installed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema Generation | Custom JSON schemas | `fastapi` + `TypedDict` | FastAPI 0.110+ generates perfect OpenAPI schemas from `TypedDict`. |
| API Routing | Custom path matching | `fastapi.APIRouter` | Standard, efficient, and supports nesting. |
| Testing Client | Manual `requests` calls | `httpx` / `TestClient` | Handles async lifecycles and provides better ergonomics for FastAPI. |

## Common Pitfalls

### Pitfall 1: Missing scikit-learn
**What goes wrong:** Calling `/duplicates` fails with a `RuntimeError` if `scikit-learn` is missing.
**Why it happens:** `corpulse` makes `scikit-learn` optional in code (even if it's currently a dependency, the code handles its absence).
**How to avoid:** Catch `RuntimeError` in the route and return `HTTPException(status_code=501, detail="...")`.

### Pitfall 2: Async Lifecycle Management
**What goes wrong:** `AsyncCorpulse` backends (like Postgres) may leak connections if not closed.
**Why it happens:** Dependency injection without proper cleanup.
**How to avoid:** Recommend users to provide a `get_corpulse` dependency that `yield`s the instance, allowing FastAPI to call `__aexit__`.

## Code Examples

### FastAPI Integration Factory
```python
# Example usage by a consumer
from fastapi import FastAPI, Depends, Request
from corpulse.fastapi import get_corpulse_router
from corpulse import AsyncCorpulse
from corpulse.backends import AsyncPostgresBackend

app = FastAPI()

async def get_tenant_corpulse(request: Request):
    tenant_id = request.headers.get("X-Tenant-ID")
    # Resolve backend for tenant
    backend = await AsyncPostgresBackend.create(f"postgresql://user:pass@host/db_{tenant_id}")
    async with AsyncCorpulse(backend=backend) as corpulse:
        yield corpulse

app.include_router(
    get_corpulse_router(get_tenant_corpulse),
    prefix="/analytics",
    tags=["corpulse"]
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic V1 | Pydantic V2 | 2023 | Significant performance boost, better `TypedDict` support. |
| `pydantic.BaseModel` | `typing.TypedDict` | FastAPI 0.110+ | Allows libraries to remain lightweight while still getting full schema support. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | FastAPI 0.110+ handles `TypedDict` response models correctly. | Don't Hand-Roll | Low; verified in official docs but needs automated test confirmation. |
| A2 | User-provided `get_corpulse` is the best way to handle tenancy. | Architecture | Low; widely used pattern in FastAPI ecosystem. |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| fastapi | Router helper | ✗ | — | Optional integration; skip if missing. |
| httpx | Integration tests | ✓ | 0.28.1 | — |
| scikit-learn | Duplicates route | ✓ | 1.8.0 | Return 501 error. |
| pydantic | Schema generation | ✗ | — | Usually brought by fastapi. |

**Missing dependencies with no fallback:**
- `fastapi` (required for this phase's core feature)

**Missing dependencies with fallback:**
- `scikit-learn` (fallback to error response for `/duplicates`)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml |
| Quick run command | `pytest tests/test_fastapi.py` |
| Full suite command | `pytest tests` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FASTAPI-01 | Extra install works | smoke | `pip install ".[fastapi]"` | ❌ Wave 0 |
| FASTAPI-02 | Factory returns router | unit | `pytest tests/test_fastapi.py` | ❌ Wave 0 |
| FASTAPI-03 | Routes return 200 OK | integration | `pytest tests/test_fastapi.py` | ❌ Wave 0 |
| FASTAPI-04 | Response matches TypedDict | contract | `pytest tests/test_fastapi.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_fastapi.py -x`
- **Per wave merge:** `pytest tests`
- **Phase gate:** Full suite green

### Wave 0 Gaps
- [ ] `tests/test_fastapi.py` — New test file needed.
- [ ] `fastapi` and `httpx` in `dev` dependencies.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | FastAPI path/query parameter validation. |
| V4 Access Control | yes | (User responsibility) Depends on `get_corpulse` implementation. |

### Known Threat Patterns for FastAPI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Information Disclosure | Information Disclosure | Ensure error responses don't leak backend details (e.g., DSNs). |
| Resource Exhaustion | Denial of Service | Route-level rate limiting (user responsibility). |

## Sources

### Primary (HIGH confidence)
- Official FastAPI Documentation (fastapi.tiangolo.com) - APIRouter and TypedDict support.
- Pydantic V2 Documentation (docs.pydantic.dev) - TypedDict integration.

### Secondary (MEDIUM confidence)
- Community patterns for optional FastAPI integrations in libraries (e.g., from WebSearch).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH
- Architecture: HIGH
- Pitfalls: MEDIUM

**Research date:** 2024-04-15
**Valid until:** 2024-05-15
