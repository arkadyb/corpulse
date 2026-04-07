# Roadmap: rag-memento

## Overview

rag-memento's analytics engine is already working. This milestone makes it adoptable: proper Python packaging, a reliable test suite for the existing engine, a zero-instrumentation Qdrant wrapper (sync and async), and documentation that communicates what the tool does and what it doesn't. Each phase unblocks the next — packaging first so tests can import cleanly, tests before wrapper code so regressions surface immediately, wrapper before docs so the API is stable when written about.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Package Foundation** - Restructure into a proper pip-installable package with optional extras (completed 2026-04-02)
- [x] **Phase 2: Core Tests and Bug Fixes** - Cover the existing analytics engine with tests and fix known reliability issues (completed 2026-04-04)
- [x] **Phase 3: Qdrant Wrapper** - Build zero-instrumentation sync and async Qdrant wrappers (completed 2026-04-07)
- [ ] **Phase 4: Documentation** - Write the README and docstrings that make the library adoptable

## Phase Details

### Phase 1: Package Foundation
**Goal**: The library is installable via pip from GitHub with the correct optional dependency structure
**Depends on**: Nothing (first phase)
**Requirements**: PKG-01, PKG-02, PKG-03, PKG-04, PKG-05
**Success Criteria** (what must be TRUE):
  1. `pip install git+https://github.com/.../rag-memento` succeeds on a clean Python 3.10+ environment
  2. `import rag_memento` succeeds without qdrant-client installed
  3. `pip install rag-memento[qdrant]` installs qdrant-client as an optional dependency
  4. Source files live under `rag_memento/` package directory (not flat at repo root)
**Plans:** 1/1 plans complete

Plans:
- [ ] 01-01-PLAN.md — Restructure into rag_memento/ package with pyproject.toml and smoke tests

### Phase 2: Core Tests and Bug Fixes
**Goal**: The existing analytics engine is covered by tests and free of known reliability bugs before the wrapper is layered on
**Depends on**: Phase 1
**Requirements**: TEST-01, FIX-01, FIX-02
**Success Criteria** (what must be TRUE):
  1. `pytest tests/` runs and all tests pass for ghost, duplicate, obsolete, stale, and suspect analytics
  2. SQLite does not raise `database is locked` errors under concurrent writes
  3. `corpus_health()` computes duplicate detection only once (not twice) per call
**Plans:** 1/1 plans complete

Plans:
- [ ] 02-01-PLAN.md — Fix WAL mode and double get_duplicates bugs, write analytics test suite

### Phase 3: Qdrant Wrapper
**Goal**: A team using Qdrant can wrap their client in one line and get automatic corpus health tracking — no manual log_retrieval() calls required
**Depends on**: Phase 2
**Requirements**: QDRT-01, QDRT-02, QDRT-03, QDRT-04, QDRT-05, QDRT-06, QDRT-07, QDRT-08, QDRT-09, QDRT-10, TEST-02, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):
  1. Wrapping a QdrantClient with QdrantMementoClient intercepts query_points() and search() calls and records retrievals automatically
  2. The wrapped client returns the original Qdrant response objects unchanged — caller code requires no modification
  3. Non-intercepted methods work identically to the unwrapped client via transparent delegation
  4. AsyncQdrantMementoClient wraps AsyncQdrantClient with identical interception behavior for async codebases
  5. The qdrant-client package is only required when the wrapper is actually instantiated (not at import time)
**Plans:** 2/2 plans complete

Plans:
- [ ] 03-01-PLAN.md — Create integrations package with sync and async Qdrant wrapper classes
- [ ] 03-02-PLAN.md — Write comprehensive test suite for both sync and async wrappers

### Phase 4: Documentation
**Goal**: A developer landing on the repo can understand what rag-memento does, install it, and start using it — both with and without the Qdrant wrapper
**Depends on**: Phase 3
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05
**Success Criteria** (what must be TRUE):
  1. README shows the exact pip install command, including the [qdrant] extra
  2. README includes a working before/after example: manual log_retrieval() versus QdrantMementoClient
  3. README states clearly that rag-memento measures corpus health, not answer quality
  4. All public methods have docstrings that describe parameters and return values
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Package Foundation | 1/1 | Complete   | 2026-04-02 |
| 2. Core Tests and Bug Fixes | 1/1 | Complete   | 2026-04-04 |
| 3. Qdrant Wrapper | 2/2 | Complete   | 2026-04-07 |
| 4. Documentation | 0/? | Not started | - |
