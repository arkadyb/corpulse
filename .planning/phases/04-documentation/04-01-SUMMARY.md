---
phase: 04-documentation
plan: 01
subsystem: documentation
tags: [readme, markdown, installation, quickstart, qdrant, mpl-2.0]

# Dependency graph
requires:
  - phase: 03-qdrant-wrapper
    provides: QdrantMementoClient and AsyncQdrantMementoClient API surface

provides:
  - Complete README.md with verified install command, manual API quickstart, Qdrant wrapper examples
  - Scope statement distinguishing corpus health from answer quality
  - Reconciled license field in pyproject.toml (MPL-2.0)

affects: [05-release, future-contributors, end-users]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GitHub-only install documented via git+ pip URL"
    - "Lazy import pattern for optional extras (qdrant) reflected in docs"

key-files:
  created: []
  modified:
    - README.md
    - pyproject.toml

key-decisions:
  - "LICENSE file is legal authority: MPL-2.0 used in README and pyproject.toml, overriding prior MIT entry"
  - "Users import QdrantMementoClient directly from rag_memento (not rag_memento.integrations) — matches __init__.py lazy __getattr__"
  - "README omits fabricated integrations (ChromaMemento, LlamaIndex, LangChain) that never existed in codebase"

patterns-established:
  - "Every code snippet in README verified against actual source files before inclusion"

requirements-completed: [DOC-01, DOC-02, DOC-03, DOC-04]

# Metrics
duration: 2min
completed: 2026-04-07
---

# Phase 4 Plan 1: Documentation Summary

**README rewritten with verified GitHub install command, manual API + Qdrant wrapper quickstarts, and scope statement clarifying corpus health vs answer quality; license reconciled to MPL-2.0.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-07T04:04:53Z
- **Completed:** 2026-04-07T04:06:07Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Replaced fabricated integrations section (ChromaMemento, LlamaIndex, LangChain) with real, verified API examples
- Added exact GitHub pip install command for both core and `[qdrant]` extra
- Added manual API quickstart with `log_retrieval`, `log_engagement`, and `report()`
- Added Qdrant wrapper before/after example showing sync `QdrantMementoClient` and async `AsyncQdrantMementoClient`
- Added explicit scope statement: corpus health not answer quality, referencing Ragas/DeepEval for the latter
- Reconciled license discrepancy — pyproject.toml updated from `"MIT"` to `"MPL-2.0"` to match LICENSE file

## Task Commits

1. **Task 1: Rewrite README.md with verified content** - `3d945b0` (feat)

**Plan metadata:** (final docs commit — see below)

## Files Created/Modified

- `README.md` — complete rewrite: verified install, manual quickstart, Qdrant wrapper examples, scope statement, MPL-2.0 license footer
- `pyproject.toml` — license field corrected from `"MIT"` to `"MPL-2.0"`

## Decisions Made

- LICENSE file is legal authority over pyproject.toml. The LICENSE file contains full MPL 2.0 text, so `license = "MPL-2.0"` is the correct SPDX identifier in pyproject.toml.
- Import path for Qdrant wrappers is `from rag_memento import QdrantMementoClient` (not `from rag_memento.integrations import ...`). This matches the lazy `__getattr__` pattern established in Phase 03.
- `pip install rag-memento` (PyPI form) is explicitly excluded since the package is GitHub-only distribution.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Pre-existing test failure in `tests/test_docstrings.py` (`test_memento_docstrings_have_args_section`) was already failing before this plan's changes. It is part of the TDD RED cycle for plan 04-02 (docstring completeness). Not caused by and not fixed by this plan. All other tests pass.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- README accurately represents the actual API; ready for 04-02 (docstring completeness)
- pyproject.toml license field reconciled; no further discrepancy with LICENSE file
- All fabricated integrations removed; future contributors see only real API surface

---
*Phase: 04-documentation*
*Completed: 2026-04-07*
