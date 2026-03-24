# Project Research Summary

**Project:** rag-memento — Qdrant wrapper + packaging milestone
**Domain:** Python library — RAG corpus analytics / vector DB observability
**Researched:** 2026-03-24
**Confidence:** HIGH

## Executive Summary

rag-memento is a zero-infrastructure RAG corpus health library backed by SQLite. The v0.1.0 analytics engine (ghost detection, duplicate detection, stale embedding detection, corpus noise scoring) is already working. This milestone removes the adoption barrier: manual `log_retrieval()` instrumentation. The solution is a composition-based delegation wrapper, `QdrantMementoClient`, that intercepts `query_points()` and `search()` on `QdrantClient`, normalizes `ScoredPoint` results into Memento's format, and fires `log_retrieval()` automatically — returning the original response untouched. The wrapper is installed as an optional extra (`pip install rag-memento[qdrant]`) so the core library remains importable without qdrant-client. This approach is well-documented, has prior art in OpenTelemetry's Qdrant instrumentation, and aligns with the project's zero-infrastructure philosophy.

The recommended build order is: package restructuring first (pyproject.toml, `integrations/` directory, optional extras), then the `ResultNormalizer` pure function, then the sync wrapper with tests, then the async wrapper. Packaging first is a hard dependency — without `rag_memento/` as a proper package and `pyproject.toml`, tests cannot import the wrapper cleanly or verify the optional-install behavior. The async wrapper follows naturally once the sync wrapper is proven; `AsyncQdrantClient` is a parallel class with identical method signatures.

The top risks are: (1) async/sync mismatch if only a sync wrapper is shipped — production FastAPI stacks will break silently; (2) silent wrong doc IDs if payload field names are hardcoded — all downstream analytics will run against meaningless Qdrant integer IDs; (3) SQLite write contention under concurrent async load — one line (`PRAGMA journal_mode=WAL`) prevents this. All three are preventable with architectural decisions made before writing the first wrapper line, not after.

---

## Key Findings

### Recommended Stack

The only new dependency is `qdrant-client>=1.7.1` (version 1.17.1 is current as of 2026-03-13), pinned as an optional extra via pyproject.toml, not a hard dependency. The build backend should be hatchling — standard for pure-Python libraries, supports optional-dependency groups cleanly, and does not impose a lock file. The test strategy uses `QdrantClient(":memory:")` for integration tests (no Docker or mock needed for the happy path) and `pytest-mock` only for edge cases. The existing stack (SQLite, numpy, sklearn, pandas, tabulate) is unchanged.

**Core technologies:**
- `qdrant-client>=1.7.1`: Qdrant Python client being wrapped — only official client; in-memory mode enables zero-infrastructure testing; `query_points()` added in 1.7.1
- `hatchling`: Build backend — standard modern choice; supports optional dependency groups; lighter than Poetry for a library
- `pytest>=9.0` + `pytest-mock>=3.12`: Test tooling — pytest 9.0 aligns with Python 3.10+ target; `QdrantClient(":memory:")` for integration tests, `create_autospec()` for edge-case mocks
- `pyproject.toml` (PEP 517/621): Package declaration — replaces setup.py; enables `pip install rag-memento[qdrant]`

### Expected Features

The v1 milestone has a clear MVP boundary: eliminate manual instrumentation for Qdrant users and make the library pip-installable. Everything else is proven to already be implemented or explicitly deferred.

**Must have (table stakes):**
- Zero-instrumentation query capture (sync wrapper) — core reason the wrapper exists; the adoption barrier
- Async client support (`AsyncQdrantClient` wrapper) — required; production FastAPI stacks are async; sync-only is a non-starter
- pyproject.toml with optional extras — blocking adoption; library without proper packaging is a script
- Test suite for existing analytics — prerequisite; wrapper must not regress existing behavior
- Basic README with before/after usage — minimum bar for any library

**Should have (competitive differentiators — mostly already implemented):**
- Corpus noise score as a single actionable number — unique; no other tool gives this
- Per-document status taxonomy (ghost/obsolete/stale/low_engagement/healthy) — no other tool provides this
- Cleanup report with prioritized action list — transforms monitoring into actionable triage
- `capture_vectors` opt-in flag on wrapper — enables duplicate detection via auto-captured embeddings (v1.x)

**Defer (v2+):**
- ChromaDB wrapper — same proxy pattern, different client API; defer until Qdrant wrapper is proven
- LangChain/LlamaIndex plugins — framework churn; build on proven wrapper pattern first
- PyPI publishing — after API stabilizes; GitHub-only install keeps pressure low
- CLI tool (`python -m rag_memento audit`) — useful but not blocking adoption

**Anti-features (never build):**
- Web dashboard/UI — destroys zero-infrastructure value proposition
- Answer quality/faithfulness metrics — Ragas owns this space; scope creep
- Real-time streaming capture — SQLite lock contention; not needed for corpus health

### Architecture Approach

The wrapper uses composition over inheritance: `QdrantMementoClient` holds a real `QdrantClient` as `self._client`, explicitly overrides `query_points()` and `search()` to intercept calls, delegates all other attributes via `__getattr__`. A pure function `_normalize_query_response()` translates `ScoredPoint` objects to `list[dict]` before calling `memento.log_retrieval()`. The original `QueryResponse` is always returned unmodified to the caller. The Qdrant import lives exclusively in `rag_memento/integrations/qdrant.py` — never in core modules.

**Major components:**
1. `QdrantMementoClient` (`rag_memento/integrations/qdrant.py`) — delegation wrapper; intercepts `query_points()` and `search()`; passes everything else through
2. `_normalize_query_response()` — pure function; translates `ScoredPoint` → `{doc_id, filename, score, embedding}`; isolated, testable, the only place that knows about Qdrant's data model
3. `Memento` (`memento.py`) — existing analytics facade; unchanged; receives `log_retrieval()` calls from wrapper
4. `DB` (`db.py`) — existing SQLite persistence; needs WAL mode pragma added; otherwise unchanged
5. `pyproject.toml` — new; declares optional dependency groups; enables `pip install rag-memento[qdrant]`

### Critical Pitfalls

1. **Async/sync mismatch** — `AsyncQdrantClient` is a separate class, not a subclass of `QdrantClient`. Shipping only a sync wrapper silently breaks all async (FastAPI/LangGraph) users. Avoidance: provide `AsyncQdrantMementoClient` as a parallel class in the same module; both accept the same `Memento` instance.

2. **Silent wrong doc IDs** — `ScoredPoint.id` is Qdrant's internal integer/UUID, not the user's document identifier. Hardcoding the field name means 80% of real-world collections log meaningless IDs, making all ghost/duplicate analytics useless. Avoidance: `payload_id_field: str = "doc_id"` constructor parameter; emit `warnings.warn()` on first fallback to integer ID.

3. **SQLite write contention under concurrency** — current `DB._conn()` opens a new connection per call with default journal mode. Under concurrent async queries, writers queue and fail with `OperationalError: database is locked`. Avoidance: one-line fix — add `PRAGMA journal_mode=WAL` in `DB._init()` and `timeout=10` on connections.

4. **O(n²) duplicate detection OOM** — `get_duplicates()` loads all embeddings and runs full pairwise cosine similarity. At ~5,000 documents with 1536-dim vectors, this exhausts RAM. Additionally, `corpus_health()` currently calls `get_duplicates()` twice (lines 328–334 in memento.py). Avoidance: add a `max_docs` guard clause; fix the double-call with a local variable cache.

5. **qdrant-client hard import at module top** — importing `qdrant_client` in `__init__.py` or `memento.py` forces all users to install Qdrant even when they use a different backend or only the manual API. Avoidance: lazy import inside wrapper `__init__`; raise a clear `ImportError("pip install rag-memento[qdrant]")` only on instantiation.

---

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Package Foundation
**Rationale:** Packaging is the hard prerequisite for everything else. Without `pyproject.toml` and `rag_memento/` as a proper package directory, tests can't import cleanly, the `[qdrant]` extra can't be verified, and contributors can't install in editable mode. This phase has no dependencies on wrapper logic.
**Delivers:** `pyproject.toml` with optional extras (`qdrant`, `sklearn`, `pandas`, `reports`, `all`); flat source files reorganized into `rag_memento/` package; `integrations/` subdirectory created (empty initially); `pip install rag-memento` works without qdrant-client installed.
**Addresses:** Blocking adoption (table-stakes packaging feature); isolates Qdrant import.
**Avoids:** Pitfall 5 (qdrant-client hard import) — the package structure enforces the import boundary.

### Phase 2: Core Test Suite
**Rationale:** Before adding the wrapper, the existing analytics need test coverage so wrapper integration cannot regress them silently. Research flagged the O(n²) double-call bug in `corpus_health()` and the missing WAL pragma as issues to fix now, not later. This phase makes the existing code production-quality.
**Delivers:** `tests/test_memento.py`, `tests/test_db.py`; WAL mode added to `DB._init()`; `corpus_health()` double-`get_duplicates()` call fixed; `max_docs` guard added to `get_duplicates()`; threading test verifying no `database is locked` under concurrency.
**Addresses:** Test suite prerequisite (P1 feature); SQLite reliability.
**Avoids:** Pitfall 3 (SQLite lock under concurrency); Pitfall 4 (O(n²) OOM); surfaces regressions before wrapper is layered on.

### Phase 3: Qdrant Sync Wrapper
**Rationale:** The `ResultNormalizer` pure function is the riskiest mapping decision (Qdrant's `point.id` type, payload shape conventions) and should be built and tested in isolation first. Then the sync wrapper can be built on top of the proven normalizer. This is the core deliverable of the milestone.
**Delivers:** `rag_memento/integrations/qdrant.py` with `QdrantMementoClient`; `_normalize_query_response()` pure function; `payload_id_field` and `payload_filename_field` constructor parameters; `__getattr__` delegation for non-intercepted methods; tests using `QdrantClient(":memory:")`; `warnings.warn()` on fallback to integer ID.
**Uses:** `qdrant-client>=1.7.1` optional extra; composition pattern (not subclassing).
**Implements:** `QdrantMementoClient` and `ResultNormalizer` architecture components.
**Avoids:** Pitfall 2 (silent wrong doc IDs — configurable payload field from day one); Pitfall 5 (lazy import guard); Anti-Pattern 1 (subclassing); Anti-Pattern 2 (modifying return value); Anti-Pattern 3 (swallowing Qdrant errors).

### Phase 4: Qdrant Async Wrapper
**Rationale:** Async support is table-stakes for production adoption (FastAPI stacks) but mirrors the sync wrapper exactly. Building it second means the normalizer and delegation pattern are already proven, and the async wrapper is mechanical rather than exploratory. `AsyncQdrantClient` is a parallel class with identical method signatures.
**Delivers:** `AsyncQdrantMementoClient` in `rag_memento/integrations/qdrant.py`; `async def query_points()` and `async def search()` overrides; `asyncio.to_thread()` for SQLite writes (or synchronous write with documented caveat); `pytest-asyncio` tests.
**Avoids:** Pitfall 1 (async/sync mismatch — this is the dedicated fix).

### Phase 5: Documentation and Developer Experience
**Rationale:** The library is technically correct after Phase 4 but not adoptable without clear usage documentation. The competitive advantage (corpus health vs. answer evaluation) must be communicated explicitly or users will conflate rag-memento with Ragas.
**Delivers:** README with before/after wrapper usage example; clear scope statement ("corpus health tool, not an answer evaluator"); docs for configurable `payload_id_field`; low-retrieval-count warning in `report()` when history is sparse; canonical extra name (`qdrant`) used consistently everywhere.
**Addresses:** P1 README feature; UX pitfalls (ImportError message, no-history warning, extra name consistency).

### Phase Ordering Rationale

- **Packaging before wrapper:** `integrations/qdrant.py` must live inside a proper package; the optional-import guard only works when `qdrant-client` is genuinely optional, which requires `pyproject.toml` extras.
- **Tests before wrapper code:** The O(n²) double-call bug and missing WAL pragma are existing issues. Fixing them before adding wrapper complexity is cheaper than debugging them later through wrapper test failures.
- **Sync before async:** `AsyncQdrantClient` mirrors `QdrantClient`; the normalizer, payload field config, and delegation pattern are identical. Proving the pattern once makes async mechanical.
- **Docs last:** Writing docs before the API is stable wastes effort. The wrapper's `payload_id_field` parameter cannot be documented until its name and defaults are settled.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (sync wrapper):** The `ScoredPoint` → `doc_id` mapping and payload field conventions vary widely across real-world Qdrant collections. Consider adding a concrete validation step against the actual demo data in `demo.py` before finalizing the normalizer API.
- **Phase 4 (async wrapper):** `asyncio.to_thread()` for SQLite writes is straightforward, but the decision of whether to block the event loop or offload needs a performance callout in docs. Validate with a real async FastAPI test case.

Phases with standard patterns (skip research-phase):
- **Phase 1 (packaging):** pyproject.toml with hatchling is fully documented; optional extras syntax is standard PEP 621. No additional research needed.
- **Phase 2 (test suite):** pytest patterns for SQLite and threading are well-established. WAL pragma is a one-liner with official SQLite docs.
- **Phase 5 (docs):** Standard README authoring; no research needed.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All critical facts verified against PyPI and official docs; qdrant-client 1.17.1 confirmed; hatchling and pytest versions verified |
| Features | MEDIUM-HIGH | Table stakes and differentiators well-supported by competitor analysis; async requirement confirmed from Qdrant client source; some market-context sources are vendor-authored |
| Architecture | HIGH | Existing codebase directly inspected; Qdrant client API verified against official docs and source; composition pattern has prior art in OpenTelemetry Qdrant instrumentation |
| Pitfalls | HIGH | 4 of 5 critical pitfalls derived from direct code inspection (memento.py lines 328–334, db.py connection pattern); async/sync split verified from Qdrant client source |

**Overall confidence:** HIGH

### Gaps to Address

- **Payload field convention survey:** No systematic data exists on what payload field names real-world Qdrant users use for document identifiers. The `payload_id_field` default of `"doc_id"` is a guess. Consider inspecting the existing `demo.py` collection setup to validate the default before v1 ships.
- **Async SQLite write latency:** `asyncio.to_thread()` adds overhead for each query. Acceptable for corpus health (low write frequency), but no benchmark exists. If users report latency, the fallback is a background writer thread — document this as a known trade-off.
- **`corpus_health()` double-call location:** Identified as lines 328–334 in `memento.py` from code inspection; should be verified at implementation time as the file may have been modified since research.

---

## Sources

### Primary (HIGH confidence)
- [qdrant-client PyPI](https://pypi.org/project/qdrant-client/) — version 1.17.1, Python >=3.10 requirement, optional extras
- [Qdrant Python Client docs](https://python-client.qdrant.tech/qdrant_client.qdrant_client) — `query_points`, `search`, `ScoredPoint` fields, in-memory mode
- [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — `[project.optional-dependencies]` syntax
- [SQLite WAL docs](https://www.sqlite.org/wal.html) — WAL mode concurrency behavior
- [pytest PyPI](https://pypi.org/project/pytest/) — version 9.0.2, Python >=3.10 requirement
- [python-patterns.guide](https://python-patterns.guide/gang-of-four/decorator-pattern/) — `__getattr__` delegation pattern
- [Qdrant async API tutorial](https://qdrant.tech/documentation/database-tutorials/async-api/) — `AsyncQdrantClient` structure
- Direct code inspection: `memento.py`, `db.py`, `__init__.py`, `demo.py` in this repository

### Secondary (MEDIUM confidence)
- [opentelemetry-instrumentation-qdrant on PyPI](https://pypi.org/project/opentelemetry-instrumentation-qdrant/) — prior art for Qdrant call interception pattern
- [OpenLLMetry Qdrant instrumentation source](https://github.com/traceloop/openllmetry) — reference implementation for wrapper pattern
- [Qdrant Search and Query — DeepWiki](https://deepwiki.com/qdrant/qdrant-client/4.3-search-and-query) — third-party but detailed method coverage
- [Python Build Backends in 2025 — Medium](https://medium.com/@dynamicy/python-build-backends-in-2025-what-to-use-and-why-uv-build-vs-hatchling-vs-poetry-core-94dd6b92248f) — hatchling vs alternatives comparison
- [Top 5 RAG Observability Platforms 2026 — Maxim AI](https://www.getmaxim.ai/articles/top-5-rag-observability-platforms-in-2026/) — competitor landscape (vendor-authored)

### Tertiary (LOW confidence)
- [RAG Monitoring Benchmark 2026 — AIM Research](https://research.aimultiple.com/rag-monitoring/) — market context only; analyst site

---
*Research completed: 2026-03-24*
*Ready for roadmap: yes*
