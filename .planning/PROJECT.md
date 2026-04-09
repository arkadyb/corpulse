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

### Active

<!-- Current scope. Building toward these. -->

- [ ] Define the next milestone after v1.1
- [ ] Choose which future wrapper or distribution goal ships next
- [ ] Decide whether the next async milestone expands `AsyncCorpulse` beyond the narrow v1.1 surface

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- ChromaDB wrapper — Qdrant chosen as first integration target; others follow later
- Pinecone wrapper — deferred to future milestone
- LangChain/LlamaIndex plugin — future milestone after wrapper pattern is proven
- Standalone audit mode (crawl vector DB without runtime) — future milestone
- CLI tool — future milestone
- PyPI publishing — distributing via GitHub only for now
- Web dashboard / UI — keep it library-first

## Current State

corpulse has shipped milestone `v1.1` and now supports pluggable persistence across SQLite, in-memory, sync Postgres, and async Postgres backends. Sync services use `Corpulse` with explicit backend injection, and async services have the shipped narrow `AsyncCorpulse` path over `AsyncPostgresBackend`.

## Next Milestone Goals

- Choose the next milestone scope and create fresh requirements.
- Decide whether to prioritize more integrations, packaging/distribution, or broader async parity.
- Keep the shipped v1.1 storage architecture stable while expanding product reach.

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

---
*Last updated: 2026-04-09 after milestone v1.1 completion*
