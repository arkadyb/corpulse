# corpulse

## What This Is

A Python library that tracks and analyzes RAG corpus health for RAG teams. It detects ghost documents, near-duplicates, obsolete versions, stale embeddings, and low-engagement content, showing which documents are hurting retrieval quality and what to do about them.

## Core Value

RAG teams can point corpulse at their vector DB and immediately understand what's wrong with their corpus without manual audits.

## Completed Milestone: v1.9 PyPI Distribution and Release Readiness

**Goal:** Make corpulse installable from PyPI with verified optional extras and a repeatable release path.

**Target features:**
- PyPI-ready package metadata, README rendering, package contents, license inclusion, and version consistency
- Verified install surfaces for `pip install corpulse`, `pip install corpulse[qdrant]`, and existing optional extras
- GitHub Actions release automation using PyPI Trusted Publishing for TestPyPI and PyPI
- Documentation updated from GitHub install syntax to PyPI install syntax
- Release checklist covering build artifacts, clean-environment installs, imports, extras, and Qdrant wrapper availability

## Current Milestone

None. Start the next milestone with `$gsd-new-milestone`.

The next milestone should start from fresh requirements. Candidate directions include release-note maturity, signed artifacts, PyPI adoption reporting, or the next integration adapter.

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
- ✓ SQLAlchemy-style DSN normalization for sync and async Postgres backends — Phase 15
- ✓ Postgres multi-tenancy via validated `schema` / `table_prefix` — Phase 16
- ✓ Additive Qdrant tenant helper functions for collection naming, chunk IDs, delete-by-filter, and collection setup — Phase 17
- ✓ A minimal indexing pipeline over AsyncCorpulse + Qdrant with rollback semantics — Phase 18
- ✓ Typed async payload models that preserve current `report()` / `cleanup_report()` compatibility — Phase 19
- ✓ Optional FastAPI router helpers built on the typed payload layer — Phase 20
- ✓ Low-Confidence / Zero-Result Rate analytics — Phase 21
- ✓ Generation trace capture foundation — Phase 24
- ✓ Generic sync/async wrapper engine for retrieval client integrations — v1.7
- ✓ Qdrant wrappers migrated onto the shared engine with no API regression — v1.7
- ✓ Public extension surface and docs for thin future integration adapters — v1.7
- ✓ Workload trace feasibility and append-only schema direction — Phase 27
- ✓ First-class sync/async RAG request trace capture — Phase 28
- ✓ Privacy-preserving workload trace JSONL import/export — Phase 29
- ✓ Workload and serving reports over captured/imported traces — Phase 30
- ✓ Session analytics and repeated-context reuse signals — Phase 31
- ✓ Replay feasibility and dependency-free callable replay proof — Phase 32
- ✓ PyPI-ready package metadata, README rendering, package contents, license inclusion, and version consistency — v1.9
- ✓ Verified install surfaces for `pip install corpulse`, `pip install corpulse[qdrant]`, and existing optional extras — v1.9
- ✓ GitHub Actions release automation using PyPI Trusted Publishing for TestPyPI and PyPI — v1.9
- ✓ PyPI-first installation documentation and release checklist with post-publish smoke checks — v1.9

### Active

<!-- Current scope. Building toward these. -->

(None. Define fresh requirements with `$gsd-new-milestone`.)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- ChromaDB wrapper — Qdrant chosen as first integration target; others follow later
- Pinecone wrapper — deferred to future milestone
- LangChain/LlamaIndex plugin — future milestone after wrapper pattern is proven
- Standalone audit mode (crawl vector DB without runtime) — future milestone
- CLI tool — future milestone
- Web dashboard / UI — keep it library-first
- **Faithfulness / Hallucination Rate** — requires LLM-as-judge to verify generated answer against retrieved context; not measurable from retrieval logs alone; use Ragas or TruLens for generation-layer evaluation
- **Context Precision** — requires ground-truth relevance labels per query; corpulse has no label store and no annotation workflow; belongs in offline eval frameworks
- **Contradictory Information Density** — requires periodic LLM scan of high-similarity embedding clusters; adds LLM dependency and async job infrastructure incompatible with the library's zero-inference design principle
- **Answer Relevance / Context Utilization** — measures generation quality (how much retrieved context was used); a generation-layer metric requiring prompt + completion access; out of scope for a retrieval-layer analytics library

## Current State

corpulse completed milestone `v1.9`, moving distribution readiness from GitHub-only installs to a PyPI-first release posture. The package metadata, source distribution, wheel contents, optional extras, release workflow, Trusted Publishing documentation, and install docs are now covered by static tests, build checks, and milestone verification artifacts.

The release workflow builds once, uploads the tested `dist/*` artifacts, publishes to TestPyPI on manual dispatch, and publishes to PyPI only from `v*` tags through OIDC Trusted Publishing. The production `pypi` GitHub environment approval gate and the live TestPyPI/PyPI smoke checks remain explicit manual release-time actions documented in `.github/RELEASE_CHECKLIST.md`.

corpulse completed milestone `v1.7`, adding a shared generic wrapping engine and migrating the Qdrant compatibility wrappers onto that architecture. The library now supports a documented advanced adapter path for future integrations while preserving lazy optional dependency behavior and Qdrant compatibility.

The shipped `v1.8` milestone was seeded by `.planning/research/RAGPULSE-COMPARISON-FEATURES.md`, which found that RAGPulse is most useful as a workload trace and replay reference rather than as a corpus-health competitor. corpulse kept its corpus-health core while adding an optional workload/serving layer for request composition, traffic shape, latency, sessions, and replayable exports.

Phase 27 completed the feasibility decision record and locked the MVP direction on an append-only request-trace schema. Phases 28-31 delivered trace capture, JSONL import/export, workload and serving reports, and session analytics with repeated-context reuse signals. Phase 32 validated that callable replay is feasible and delivered dependency-free sync/async replay helpers. v1.8 shipped on 2026-05-05. It did not add a built-in OpenAI endpoint client; richer benchmark export and endpoint adapters remain future work.

The v1.9 milestone moved distribution from GitHub-only to PyPI-ready. `pyproject.toml` uses Hatchling dynamic versioning, optional extras are verified from built artifacts, README is PyPI-first, and `.github/workflows/release.yml` implements the Trusted Publishing release path.

## Next Milestone Goals

- Define fresh requirements before starting implementation.
- Consider release maturity: release notes, signed artifacts, and PyPI adoption reporting.
- Consider the next integration adapter now that generic wrapping and distribution readiness are in place.

<details>
<summary>Archived v1.7 milestone framing</summary>

### Milestone Goal

Replace dedicated wrapper boilerplate with a shared sync/async wrapping engine while preserving the current Qdrant public API and documenting the extension path for future integrations.

### Delivered Scope

- Shared `wrap()` / `WrapMethod` infrastructure for sync and async retrieval clients
- Qdrant wrappers rebuilt on top of the shared engine with lazy optional dependency behavior preserved
- Public documentation and tests that show how future integrations can use thin adapter specs instead of full wrapper classes

</details>

## Previous Milestone: v1.3 Multi-Tenant Integrations (COMPLETE)

**Goal:** Make corpulse easier to run as a tenant-scoped service backend by improving Postgres tenancy support, normalizing real-world DSNs, adding reusable Qdrant indexing primitives, and exposing typed integration surfaces without breaking current async payload consumers.

**Target features:**
- ✓ Native SQLAlchemy-style DSN support for sync and async Postgres backends
- ✓ Postgres multi-tenancy via validated `schema` and `table_prefix`
- ✓ Tenant-friendly Qdrant helpers plus an indexing pipeline MVP with rollback semantics
- ✓ Typed async payload models that preserve current `report()` / `cleanup_report()` contracts
- ✓ Optional FastAPI router helpers layered on the typed payloads

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
- Spike 001 established the key boundary for future wrapper work: interception can be generic, but response normalization still needs explicit per-client recipes
- RAGPulse comparison on 2026-05-02 suggests workload observability and replay are the highest-leverage expansion areas: sessionized request traces, prompt component breakdown, serving latency metrics, traffic shape analytics, benchmark export, and cacheability/reuse signals

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
- **Distribution**: v1.9 targets PyPI publication with GitHub source install kept as a fallback path
- **Vector DB**: Qdrant remains the first wrapper target
- **Compatibility**: Python 3.10+
- **Backwards compat**: `Corpulse()` with no args must still work exactly as before
- **Public contract stability**: Existing async `report()` / `cleanup_report()` dict payload semantics remain valid during v1.3

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Qdrant as first wrapper | Growing production adoption in RAG pipelines; good Python client | Shipped |
| GitHub-only distribution | Keep overhead low before the first public package release | Superseded by v1.9 |
| Wrapper-first over audit-first | Query-dependent features are the most actionable; wrapper enables them automatically | Shipped |
| Keep manual API alongside wrapper | Existing API still useful for custom integrations; wrapper is additive | Shipped |
| Pluggable backend interface | Service repo needs Postgres; library should support multiple backends | Shipped in v1.1 |
| Explicit backend config over connection strings | More flexible and clearer than implicit string configuration | Shipped in v1.1 |
| Narrow async facade for v1.1 | Async service integration was needed now; full async analytics parity was not yet justified | Shipped in v1.1 |
| PyPI Trusted Publishing over API tokens | Avoid long-lived publishing credentials and keep release automation auditable | Shipped in v1.9 |
| PyPI-first install docs with GitHub source fallback | PyPI is the user path; source install remains useful for unreleased fixes | Shipped in v1.9 |
| Evidence-gated requirement closure | Milestone claims should match recorded verification, not just landed code | Shipped in v1.1 |
| Structured-payload async reports | Avoids coupling `AsyncCorpulse` to stdout and keeps output consumable by services/tests; sync `report`/`cleanup_report` become a thin formatter over the same payload | Shipped in Phase 12 |
| Pandas stays optional on async path | Keeps install footprint small for async service users who don't need DataFrames; mirrors sync behavior | Shipped in Phase 12 |
| Live async parity must be env-gated | Keeps the default suite deterministic while still allowing real-Postgres evidence for the async path | Shipped in Phase 13 |
| Async demo defaults to in-memory adapter | Keeps the example runnable without external services or library-level async memory backend changes | Shipped in Phase 14 |
| v1.3 follows integration-readiness order over showcase order | DSN normalization and Postgres tenancy reduce immediate service friction; typed models and FastAPI helpers come later after payload semantics are preserved | Shipped in v1.3 |
| Typed async payload work must preserve current method semantics | README and tests already define dict payloads for `report()` and `cleanup_report()`; model layers should mirror rather than replace that contract | Shipped in Phase 19 |
| Generic wrapping should replace proxy boilerplate, not backend-specific normalization | The spike proved interception is reusable, but result-shape extraction still varies across clients and must stay explicit | Shipped in v1.7 |
| Qdrant remains first-class while the generic API serves advanced adapter authors | Keeps the common path simple for existing users while making future integrations cheaper to build | Shipped in v1.7 |
| Workload observability is the v1.8 priority over a second vector DB adapter | RAGPulse comparison showed the bigger product gap is production request behavior, not another retrieval-client wrapper | Shipped through Phase 31 |
| Callable replay over built-in endpoint replay | Current traces do not guarantee canonical messages, raw component content, tool payloads, streamed chunks, or response bodies; user callables can bridge private endpoint-specific payloads without new core dependencies | Shipped in Phase 32 |
| PyPI Trusted Publishing over long-lived release tokens | OIDC avoids storing a long-lived PyPI API token in GitHub secrets and gives PyPI a verifiable source repository link | Shipped in v1.9 |

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
*Last updated: 2026-05-15 after starting milestone v1.9*
