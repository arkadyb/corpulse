---
phase: 20-fastapi-optional-integration
plan: 01
subsystem: integrations
tags: [fastapi, async, router]
dependency_graph:
  requires: [AsyncCorpulse, TypedDict models]
  provides: [FastAPI router helper]
  affects: [pyproject.toml, corpulse/fastapi.py]
tech-stack: [FastAPI, Pydantic, httpx]
key-files: [corpulse/fastapi.py, pyproject.toml]
decisions:
  - Added optional 'fastapi' extra to pyproject.toml to avoid forcing dependency.
  - Implemented get_corpulse_router factory in a new corpulse.fastapi module.
  - Used top-level try-except for FastAPI imports to support optional installation.
  - Wired all 7 AsyncCorpulse analysis methods to REST endpoints.
  - Mapped AsyncCorpulse RuntimeError (missing sklearn) to FastAPI 501 Not Implemented.
metrics:
  duration: 600
  completed_date: "2026-04-15"
---

# Phase 20 Plan 01: FastAPI Optional Integration Summary

Added optional `corpulse[fastapi]` extras and implemented a FastAPI router factory in `corpulse.fastapi` to expose corpus analytics as REST endpoints.

## One-liner
FastAPI router factory providing REST endpoints for all AsyncCorpulse analysis methods with typed response models.

## Key Changes

### Infrastructure
- **pyproject.toml**: Added `fastapi` and `pydantic` to optional-dependencies.
- **pyproject.toml**: Added `httpx` to dev dependencies for testing.

### Integration Layer
- **corpulse/fastapi.py**: Created a new module containing `get_corpulse_router`.
- **Factory Pattern**: The router factory accepts a `get_corpulse` dependency provider, enabling flexible tenant-scoping or backend configuration.
- **Endpoint Coverage**:
    - `GET /report`: Full corpus health report.
    - `GET /cleanup-report`: Structured cleanup action payload.
    - `GET /ghosts`: List of inactive documents.
    - `GET /duplicates`: Similarity-based duplicate detection (with 501 fallback if sklearn missing).
    - `GET /obsolete`: List of superseded documents.
    - `GET /stale`: List of documents with outdated embeddings.
    - `GET /suspects`: High-retrieval, low-engagement documents.
- **Typing**: All endpoints use `response_model` with `TypedDict` models from `corpulse.models` for automatic validation and OpenAPI documentation.

## Deviations from Plan

None - plan executed exactly as written.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: information_disclosure | corpulse/fastapi.py | REST endpoints expose internal corpus metrics; access control is delegated to the consumer's FastAPI app. |

## Self-Check: PASSED

- [x] pyproject.toml contains `corpulse[fastapi]` extras.
- [x] `corpulse/fastapi.py` exists and exports `get_corpulse_router`.
- [x] Factory can be imported and successfully handles missing FastAPI (returns error on call).
- [x] All 7 analysis endpoints are implemented and correctly typed.
