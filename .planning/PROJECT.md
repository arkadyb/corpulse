# corpulse

## What This Is

A Python library that tracks and analyzes RAG corpus health for RAG teams. It detects ghost documents, near-duplicates, obsolete versions, stale embeddings, and low-engagement content, showing which documents are hurting retrieval quality and what to do about them.

## Core Value

RAG teams can point corpulse at their vector DB and immediately understand what's wrong with their corpus without manual audits.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Ghost detection (documents never retrieved within a time window) — existing
- ✓ Duplicate detection via embedding cosine similarity — existing
- ✓ Obsolete version detection (v1 alongside v2) — existing
- ✓ Stale embedding detection (source changed, embedding not updated) — existing
- ✓ Low-engagement suspect identification (high retrieval, low action) — existing
- ✓ Overall corpus health scoring with noise estimate — existing
- ✓ Manual ingestion API (`log_retrieval`, `log_engagement`, `log_source_update`) — existing
- ✓ SQLite persistence layer — existing
- ✓ Human-readable report and cleanup report output — existing
- ✓ Pandas DataFrame export — existing
- ✓ Qdrant wrapper — automatic query and result capture — Phase 3
- ✓ Proper Python packaging (pyproject.toml, extras) — Phase 1
- ✓ Test suite for analytics engine — Phase 2
- ✓ Documentation (README, API reference, docstrings) — Phase 4
- ✓ Pluggable storage abstraction with explicit backend injection — v1.1
- ✓ SQLiteBackend and InMemoryBackend under a shared storage contract — v1.1
- ✓ Sync Postgres backend with pooled operation support — v1.1
- ✓ Async Postgres backend with pooled operation support — v1.1
- ✓ Narrow async `AsyncCorpulse` facade for async service integration — v1.1
- ✓ `AsyncCorpulse.to_dataframe()` with pandas kept as an optional dependency — Phase 12
- ✓ `AsyncCorpulse.report()` returning a structured payload — Phase 12
- ✓ `AsyncCorpulse.cleanup_report()` returning a structured payload — Phase 12
- ✓ Shared structured-report helpers in `corpulse/core.py` consumed by both sync and async paths — Phase 11-12
- ✓ Live asyncpg integration coverage for the new async parity surface — Phase 13
- ✓ README, docstrings, and an `examples/` script positioning AsyncCorpulse as a first-class path — Phase 14

### Active

<!-- Current scope. Building toward these. -->

- [ ] SQLAlchemy-style DSN normalization for sync and async Postgres backends
- [ ] Postgres multi-tenancy via validated `schema` / `table_prefix`
- [ ] Additive Qdrant tenant helper functions for collection naming, chunk IDs, delete-by-filter, and collection setup
- [ ] A minimal indexing pipeline over AsyncCorpulse + Qdrant with rollback semantics
- [ ] Typed async payload models that preserve current `report()` / `cleanup_report()` compatibility
- [ ] Optional FastAPI router helpers built on the typed payload layer

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- ChromaDB wrapper — Qdrant chosen as first integration target; others follow later
- Pinecone wrapper — deferred to future milestone
- LangChain/LlamaIndex plugin — future milestone after wrapper pattern is proven
- Standalone audit mode (crawl vector DB without runtime) — future milestone
- CLI tool — future milestone
- PyPI publishing — distributing via GitHub only for now
- Web dashboard / UI — keep it library-first

## Current Milestone: v1.3 Multi-Tenant Integrations

**Goal:** Make corpulse easier to run as a tenant-scoped service backend by improving Postgres tenancy support, normalizing real-world DSNs, adding reusable Qdrant indexing primitives, and exposing typed integration surfaces without breaking current async payload consumers.

**Target features:**
- Native SQLAlchemy-style DSN support for sync and async Postgres backends
- Postgres multi-tenancy via validated `schema` and `table_prefix`
- Tenant-friendly Qdrant helpers plus an indexing pipeline MVP with rollback semantics
- Typed async payload models that preserve current `report()` / `cleanup_report()` contracts
- Optional FastAPI router helpers layered on the typed payloads

## Current State

corpulse has shipped milestone `v1.2`, completing full async parity for `AsyncCorpulse`. The next milestone is not another parity pass; it is an integration-readiness milestone focused on service-oriented backend primitives and compatibility improvements discovered during the showcase work.

<details>
<summary>Archived v1.2 milestone framing</summary>

### Milestone Goal

Close the remaining gap between `AsyncCorpulse` and sync `Corpulse` so the async path is a fully at-par, documented, first-class surface for service integration.

### Delivered Scope

- `AsyncCorpulse.to_dataframe()` with pandas kept as an optional dependency
- `AsyncCorpulse.report()` returning a structured payload (no stdout coupling)
- `AsyncCorpulse.cleanup_report()` returning a structured payload (no stdout coupling)
- Shared structured-report helpers in `corpulse/core.py` consumed by both sync and async paths
- Live asyncpg integration tests (gated by `CORPULSE_POSTGRES_TEST_CONNINFO`) covering the new parity surface
- README + docstrings that position `AsyncCorpulse` as a first-class path
- A runnable async example under `examples/` showing ingestion → analysis → report end-to-end

</details>

## Context

- Existing codebase is a working v0.1.0 with all core analytics implemented
- Architecture is clean: Corpulse facade → analysis methods → DB persistence layer
- Packaging is in place with optional extras
- Manual API still works alongside wrapper integrations
- Target audience: RAG teams who need corpus observability without heavy instrumentation
- Long-term vision: multiple integration layers (wrappers, framework plugins, standalone audit)
- Library will be consumed by a separate service repo that exposes REST APIs

<details>
<summary>Archived v1.1 milestone framing</summary>

### Milestone Goal

Make the persistence layer pluggable so corpulse can use PostgreSQL in production services while keeping SQLite as the default for local use.

### Delivered Scope

- Abstract `StorageBackend` interface extracted from current DB methods
- `SQLiteBackend` refactor of the legacy implementation
- `PostgresBackend` with pooled sync operation support
- `AsyncPostgresBackend` with pooled async operation support
- `InMemoryBackend` for tests and fileless execution
- Explicit backend config: `Corpulse(backend=...)` with SQLite default
- Narrow `AsyncCorpulse` path for async service integration

</details>

## Constraints

- **Tech stack**: Python, SQLite for local persistence, PostgreSQL as the production backend target
- **Dependencies**: numpy and scikit-learn are hard dependencies; pandas and tabulate remain optional; psycopg and asyncpg are optional extras
- **Distribution**: GitHub-only for v1.x; no PyPI publishing yet
- **Vector DB**: Qdrant remains the first wrapper target
- **Compatibility**: Python 3.10+
- **Backwards compat**: `Corpulse()` with no args must still work exactly as before
- **Public contract stability**: Existing async `report()` / `cleanup_report()` dict payload semantics remain valid during v1.3

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Qdrant as first wrapper | Growing production adoption in RAG pipelines; good Python client | Pending |
| GitHub-only distribution | Keep overhead low for v1; PyPI later when stable | Pending |
| Wrapper-first over audit-first | Query-dependent features are the most actionable; wrapper enables them automatically | Pending |
| Keep manual API alongside wrapper | Existing API still useful for custom integrations; wrapper is additive | Pending |
| Pluggable backend interface | Service repo needs Postgres; library should support multiple backends | Shipped in v1.1 |
| Explicit backend config over connection strings | More flexible and clearer than implicit string configuration | Shipped in v1.1 |
| Narrow async facade for v1.1 | Async service integration was needed now; full async analytics parity was not yet justified | Shipped in v1.1 |
| Evidence-gated requirement closure | Milestone claims should match recorded verification, not just landed code | Shipped in v1.1 |
| Structured-payload async reports | Avoids coupling `AsyncCorpulse` to stdout and keeps output consumable by services/tests; sync `report`/`cleanup_report` become a thin formatter over the same payload | Shipped in Phase 12 |
| Pandas stays optional on async path | Keeps install footprint small for async service users who don't need DataFrames; mirrors sync behavior | Shipped in Phase 12 |
| Live async parity must be env-gated | Keeps the default suite deterministic while still allowing real-Postgres evidence for the async path | Shipped in Phase 13 |
| Async demo defaults to in-memory adapter | Keeps the example runnable without external services or library-level async memory backend changes | Shipped in Phase 14 |
| v1.3 follows integration-readiness order over showcase order | DSN normalization and Postgres tenancy reduce immediate service friction; typed models and FastAPI helpers come later after payload semantics are preserved | — Pending |
| Typed async payload work must preserve current method semantics | README and tests already define dict payloads for `report()` and `cleanup_report()`; model layers should mirror rather than replace that contract | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-15 after milestone v1.3 definition*
