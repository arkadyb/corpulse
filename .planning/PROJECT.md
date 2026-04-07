# rag-memento

## What This Is

A Python library that tracks and analyzes RAG corpus health for RAG teams. It detects ghost documents, near-duplicates, obsolete versions, stale embeddings, and low-engagement content — telling teams exactly which documents are hurting their retrieval quality and what to do about them.

## Core Value

RAG teams can point rag-memento at their vector DB and immediately understand what's wrong with their corpus — no guessing, no manual audits.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Ghost detection (documents never retrieved within a time window) — existing
- ✓ Duplicate detection via embedding cosine similarity — existing
- ✓ Obsolete version detection (v1 alongside v2) — existing
- ✓ Stale embedding detection (source changed, embedding not updated) — existing
- ✓ Low-engagement suspect identification (high retrieval, low action) — existing
- ✓ Overall corpus health scoring with noise estimate — existing
- ✓ Manual ingestion API (log_retrieval, log_engagement, log_source_update) — existing
- ✓ SQLite persistence layer — existing
- ✓ Human-readable report and cleanup report output — existing
- ✓ Pandas DataFrame export — existing

### Active

<!-- Current scope. Building toward these. -->

- ✓ Qdrant wrapper — automatic query and result capture without manual instrumentation — Validated in Phase 3: Qdrant Wrapper
- ✓ Proper Python packaging (pyproject.toml, extras for optional deps) — Validated in Phase 1: Package Foundation
- ✓ Test suite for existing analytics engine — Validated in Phase 2: Core Tests and Bug Fixes
- ✓ Documentation (README with usage examples, API reference) — Validated in Phase 4: Documentation

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- ChromaDB wrapper — Qdrant chosen as first integration target; others follow later
- Pinecone wrapper — deferred to future milestone
- LangChain/LlamaIndex plugin — future milestone after wrapper pattern is proven
- Standalone audit mode (crawl vector DB without runtime) — future milestone
- CLI tool — future milestone
- PyPI publishing — distributing via GitHub only for now
- Web dashboard / UI — keep it library-first

## Context

- Existing codebase is a working v0.1.0 with all core analytics implemented
- Architecture is clean: Memento facade → analysis methods → DB persistence layer
- Packaging in place (pyproject.toml, extras for optional deps) — Phase 1
- Analytics engine fully tested (22 tests), WAL mode and duplicate-detection bugs fixed — Phase 2
- Qdrant wrapper complete (sync + async), 35 tests total, lazy imports verified — Phase 3
- Documentation complete: README rewritten with verified examples, all public methods have Google-style docstrings, 39 tests total — Phase 4
- Manual API still works alongside wrapper — wrapper is additive, not a replacement
- Target audience: RAG teams who need corpus observability without heavy instrumentation
- Long-term vision: multiple integration layers (wrappers, framework plugins, standalone audit)

## Constraints

- **Tech stack**: Python, SQLite for local persistence — keep zero-infrastructure requirement
- **Dependencies**: numpy is the only hard dependency; sklearn/pandas/tabulate stay optional
- **Distribution**: GitHub-only for v1; no PyPI publishing yet
- **Vector DB**: Qdrant as first wrapper target
- **Compatibility**: Python 3.10+ (modernize from current 3.7+ baseline)

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Qdrant as first wrapper | Growing production adoption in RAG pipelines; good Python client | — Pending |
| GitHub-only distribution | Keep overhead low for v1; PyPI later when stable | — Pending |
| Wrapper-first over audit-first | Query-dependent features (ghosts, engagement) are the most actionable; wrapper enables them automatically | — Pending |
| Keep manual API alongside wrapper | Existing API still useful for custom integrations; wrapper is additive | — Pending |

---
*Last updated: 2026-04-07 after Phase 4 completion — all milestone phases complete*
