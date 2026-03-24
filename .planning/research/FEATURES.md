# Feature Research

**Domain:** RAG corpus analytics / vector DB observability library (Python)
**Researched:** 2026-03-24
**Confidence:** MEDIUM-HIGH

---

## Context

rag-memento v0.1.0 already ships a working analytics engine. This research focuses on
the **next milestone**: the Qdrant wrapper and packaging. Feature classification below
reflects what users of a corpus-health library expect, what differentiates the product,
and what to deliberately avoid.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features whose absence makes the library feel broken or require too much manual work.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Zero-instrumentation query capture** (wrapper) | RAG teams won't adopt a library that needs manual `log_retrieval()` calls on every search path | MEDIUM | Core reason the Qdrant wrapper exists; subclass or `__getattr__` delegation of `QdrantClient` is the standard Python proxy pattern |
| **Automatic doc_id + score extraction** from `ScoredPoint` | `query_points()` returns `ScoredPoint` objects with `.id`, `.score`, `.payload`; wrapper must map these to memento's schema without user code | LOW | `ScoredPoint.id` is the natural `doc_id`; filename can fall back to payload field or string repr of id |
| **Async client support** (`AsyncQdrantClient`) | Most production Qdrant setups use async; wrapper that only works sync is a non-starter for FastAPI/async RAG stacks | MEDIUM | `AsyncQdrantClient` is a separate class from `QdrantClient` since client v1.6.1; requires its own async wrapper class |
| **Ghost detection** | Most actionable corpus metric; users want to know which documents are never retrieved | LOW | Already implemented in `Memento.get_ghosts()` |
| **Duplicate detection** | Teams accumulate near-identical documents across data pipeline runs; expected in any corpus audit tool | MEDIUM | Already implemented; requires stored embeddings and scikit-learn |
| **Stale embedding detection** | "I updated the source, did my index re-embed it?" — standard operational question | LOW | Already implemented; requires `log_source_update()` or file-watcher hook |
| **Human-readable report** | `print(memento.report())` or similar one-liner is the minimum bar for a health check tool | LOW | Already implemented as `report()` and `cleanup_report()` |
| **Pandas DataFrame export** | Data teams expect to pipe results into notebooks; a dict/list API alone is not enough | LOW | Already implemented as `to_dataframe()` |
| **Configurable thresholds** | Ghost window, similarity threshold, stale lag — these must be tunable without subclassing | LOW | Already implemented as constructor params |
| **pyproject.toml / pip-installable package** | Library without proper packaging is a script, not a library; GitHub install must work cleanly | LOW | Not yet implemented; blocking adoption |

### Differentiators (Competitive Advantage)

Features that set rag-memento apart from Ragas, Arize Phoenix, LangSmith, and similar tools.
Those tools focus on trace-level and answer-quality evaluation; none focus on corpus-health
as a first-class concern.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Corpus noise score** (single number) | "What percentage of my index is junk?" — no other tool gives a single actionable health number for the corpus | LOW | Already implemented as `corpus_health()["noise_estimate"]`; needs to be prominently surfaced |
| **Obsolete version detection** | v1/v2 co-existence is a universal problem in enterprise RAG; no existing tool detects this | LOW | Already implemented via regex pattern matching on filenames |
| **Low-engagement suspect flagging** | "Retrieved often but users never acted" is a re-chunking signal; RAG evaluation tools only look at answer quality | MEDIUM | Already implemented as `get_suspects()`; engagement data requires either wrapper capture or explicit `log_engagement()` calls |
| **Drop-in Qdrant wrapper** (no import changes except class name) | OpenTelemetry QdrantInstrumentor exists but produces traces, not corpus analytics; rag-memento is the only tool capturing corpus-health-relevant signals automatically | MEDIUM | Class must be a true drop-in: `QdrantMemento(client)` or `class MementoClient(QdrantClient)` |
| **Per-document status classification** | `ghost / obsolete / stale / low_engagement / healthy` taxonomy gives teams a triage list, not just a score | LOW | Already implemented; needs clear docs |
| **Zero infrastructure requirement** | SQLite-backed, no Kafka, no cloud, no separate server; installable in a notebook | LOW | Strong differentiator vs Arize/Maxim which require accounts; must stay this way |
| **Cleanup report with prioritized action list** | Most monitoring tools show dashboards; rag-memento tells teams exactly which documents to delete/re-embed/re-chunk | LOW | Already implemented as `cleanup_report()`; expand to suggest automated remediation |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Web dashboard / UI** | Looks impressive in demos | Requires a server process, authentication, frontend build chain; destroys the zero-infrastructure value prop; users already have notebooks and Grafana | `to_dataframe()` + Jupyter; export-to-CSV for BI tools |
| **Answer quality / faithfulness metrics** | Teams conflate retrieval and answer quality | Ragas and DeepEval already do this well; building it here splits focus and competes in a crowded space | Document the boundary clearly: rag-memento is a corpus health tool, not an answer evaluator; point to Ragas for that |
| **LangChain / LlamaIndex plugins at v1** | Large ecosystems = large reach | Plugin API churn in framework-heavy ecosystems means perpetual maintenance; wrapper pattern is proven and framework-agnostic | Prove the Qdrant wrapper pattern first; framework plugins follow using the same pattern |
| **Real-time streaming capture** | "Why not capture every query in real-time?" | Synchronous write-to-SQLite on every query introduces lock contention under load; async write queue adds complexity | Batch writes (buffer N retrievals, flush periodically) or write on the same thread but with WAL mode; no streaming required for corpus health |
| **Automatic engagement inference** | "Infer engagement from query patterns without explicit signals" | Heuristic engagement inference has high false-positive rate; misleads corpus triage | Keep engagement explicit: wrapper captures retrievals automatically, but engagement always requires a deliberate `log_engagement()` call |
| **PyPI publishing at v1** | Standard distribution channel | Creates versioning obligations, changelog requirements, deprecation pressure before the API is stable | GitHub-only install keeps pressure low; add PyPI when API stabilizes |
| **Multi-tenancy / per-user corpus tracking** | Enterprise request | Multiplies DB schema complexity; SQLite doesn't scale to concurrent multi-tenant writes | Single-corpus-per-instance model is sufficient; teams with multi-tenant needs run one instance per corpus |

---

## Feature Dependencies

```
[pyproject.toml / packaging]
    └──enables──> [pip install from GitHub]
                      └──enables──> [Adoption by RAG teams]

[Qdrant sync wrapper (MementoQdrantClient)]
    └──requires──> [query_points() / search() method interception]
                       └──requires──> [ScoredPoint → doc_id/score mapping]
                                          └──feeds──> [log_retrieval() in Memento]

[Qdrant async wrapper (AsyncMementoQdrantClient)]
    └──mirrors──> [Qdrant sync wrapper]
    └──requires──> [async def query_points() override]

[Duplicate detection]
    └──requires──> [Embeddings stored in DB]
                       └──requires──> [Wrapper passes with_vectors=True OR embeddings registered separately]

[Low-engagement suspect detection]
    └──requires──> [Retrieval data] ← provided by wrapper automatically
    └──enhanced by──> [Engagement data] ← still requires explicit log_engagement()

[Stale embedding detection]
    └──requires──> [source_updated_at timestamps]
                       └──requires──> [log_source_update() calls] (not automatable by wrapper)

[Cleanup report with action list]
    └──requires──> [All analysis methods: get_ghosts(), get_obsolete(), get_stale_embeddings(), get_suspects()]
    └──enhanced by──> [More retrieval data] ← wrapper provides automatically

[corpus_health() noise score]
    └──aggregates──> [get_ghosts(), get_obsolete(), get_stale_embeddings(), get_duplicates()]
    └──note──> [duplicate count is 0 if scikit-learn not installed; noise score is understated]
```

### Dependency Notes

- **Wrapper requires ScoredPoint mapping:** `query_points()` returns `QueryResponse` containing `ScoredPoint` objects. Wrapper must extract `.id` (doc_id), `.score`, and optionally payload fields for filename. Deprecated `search()` returns the same type; wrapper should intercept both for backward compatibility.
- **Async wrapper mirrors sync wrapper:** `AsyncQdrantClient` is a parallel class hierarchy in qdrant-client ≥ 1.6.1. A separate `AsyncMementoQdrantClient` is needed; they share the same underlying `Memento` instance.
- **Duplicate detection requires embeddings at write time:** The wrapper can request vectors via `with_vectors=True` on `query_points()`, but this increases payload size. An opt-in flag on the wrapper (e.g., `capture_vectors=True`) is the right default.
- **Stale detection is not automatable by a query wrapper:** It requires knowing when source documents changed. This remains an explicit `log_source_update()` call, or a future file-watcher integration.
- **scikit-learn is optional:** Duplicate detection silently degrades (returns 0 pairs) when sklearn is absent. `corpus_health()` noise estimate is therefore understated without it. Document this clearly.

---

## MVP Definition

### Launch With (v1 — current milestone)

The goal is removing the manual instrumentation barrier.

- [ ] **Qdrant sync wrapper** — drop-in replacement for `QdrantClient`; intercepts `query_points()` and deprecated `search()`; calls `memento.log_retrieval()` automatically
- [ ] **Qdrant async wrapper** — same as sync but for `AsyncQdrantClient`; required because production FastAPI stacks are async
- [ ] **pyproject.toml with extras** — `pip install rag-memento[qdrant]` installs `qdrant-client`; `[sklearn]` installs scikit-learn; `[pandas]` installs pandas; `[full]` installs all
- [ ] **Test suite for existing analytics** — before adding wrapper, existing `Memento` methods need tests so wrapper integration doesn't regress them
- [ ] **Basic README with wrapper usage example** — one code block showing before/after instrumentation

### Add After Validation (v1.x)

- [ ] **`capture_vectors` flag on wrapper** — opt-in to storing embeddings for duplicate detection (increases memory/storage, so off by default)
- [ ] **ChromaDB wrapper** — second integration target; same proxy pattern, different client API
- [ ] **Standalone audit mode** — crawl a Qdrant collection without runtime query capture (for teams doing batch audits, not live monitoring)
- [ ] **CLI tool** — `python -m rag_memento audit --collection my_collection` for one-off corpus checks

### Future Consideration (v2+)

- [ ] **LangChain / LlamaIndex plugin** — framework plugin built on top of proven wrapper pattern
- [ ] **Pinecone wrapper** — deferred per PROJECT.md
- [ ] **PyPI publishing** — after API stabilizes
- [ ] **Automated remediation suggestions with code generation** — "Here is the Qdrant delete call to remove these 12 ghost documents"

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Qdrant sync wrapper | HIGH | MEDIUM | P1 |
| Qdrant async wrapper | HIGH | LOW (mirrors sync) | P1 |
| pyproject.toml + extras | HIGH | LOW | P1 |
| Test suite for analytics | MEDIUM | MEDIUM | P1 (prerequisite) |
| README + usage docs | HIGH | LOW | P1 |
| capture_vectors opt-in flag | MEDIUM | LOW | P2 |
| ChromaDB wrapper | MEDIUM | MEDIUM | P2 |
| Standalone audit mode | MEDIUM | HIGH | P2 |
| CLI tool | LOW | LOW | P3 |
| LangChain plugin | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for this milestone
- P2: Add when wrapper pattern is proven
- P3: Future consideration

---

## Competitor Feature Analysis

The existing corpus-health tooling gap is the key market insight: existing RAG observability
tools focus on trace-level and answer-quality evaluation, not corpus health.

| Feature | Ragas | Arize Phoenix | LangSmith | rag-memento |
|---------|-------|---------------|-----------|-------------|
| Answer faithfulness metrics | Yes | Yes | Yes | Deliberately excluded |
| Context precision/recall | Yes | Yes | Yes | Excluded |
| Trace visualization | No | Yes | Yes | Excluded |
| Ghost document detection | No | No | No | Core feature |
| Duplicate detection | No | Partial (cluster viz) | No | Core feature |
| Stale embedding detection | No | No | No | Core feature |
| Obsolete version detection | No | No | No | Core feature |
| Low-engagement suspects | No | No | No | Core feature |
| Corpus noise score | No | No | No | Core feature |
| Zero infrastructure required | Yes (open-source) | Yes (local mode) | No (cloud) | Yes (SQLite) |
| Drop-in vector DB wrapper | No | No | No | v1 target |
| Cleanup action list | No | No | No | Core feature |

**Key finding:** No existing tool treats the document corpus itself as an observable system.
rag-memento owns this niche entirely. The risk is market education, not competition.

---

## Wrapper Pattern Design Notes

These are implementation-relevant findings that affect feature behavior:

**Methods to intercept in `QdrantClient`:**
- `query_points()` — current universal endpoint (primary target)
- `search()` — deprecated but still widely used; intercept for backward compatibility
- `query_batch_points()` — batch version; each request in the batch should log independently

**`ScoredPoint` field mapping:**
- `point.id` → `doc_id` (str or int; normalize to str)
- `point.score` → `score`
- `point.payload` → check for a configurable `filename_field` key (default: `"filename"`, fall back to `str(point.id)`)
- `point.vector` → `embedding` (only if `with_vectors=True` was requested)

**Proxy pattern recommendation:** Use explicit method override (`def query_points(self, ...)`) rather than `__getattr__` delegation for the intercepted methods. `__getattr__` is a fallback mechanism and can miss methods defined on the parent class. Explicit override is clearer and type-checker friendly. All non-intercepted methods pass through to the underlying client via normal inheritance.

**Async pattern:** `AsyncQdrantClient` is not a subclass of `QdrantClient`; it is a parallel implementation. The async wrapper must subclass `AsyncQdrantClient` separately and override `async def query_points(...)`. Both wrappers should accept a single `Memento` instance as a constructor argument so the same analytics DB is used across sync and async calls.

---

## Sources

- [Qdrant Python Client — `qdrant_client.qdrant_client` module](https://python-client.qdrant.tech/qdrant_client.qdrant_client) — HIGH confidence (official docs)
- [Qdrant Search and Query — DeepWiki](https://deepwiki.com/qdrant/qdrant-client/4.3-search-and-query) — MEDIUM confidence (third-party but detailed)
- [opentelemetry-instrumentation-qdrant on PyPI](https://pypi.org/project/opentelemetry-instrumentation-qdrant/) — HIGH confidence (official package; shows prior art for interception pattern)
- [Building Production RAG — PremAI 2026 Guide](https://blog.premai.io/building-production-rag-architecture-chunking-evaluation-monitoring-2026-guide/) — MEDIUM confidence (web source; monitoring standards discussed)
- [Top 5 RAG Observability Platforms 2026 — Maxim AI](https://www.getmaxim.ai/articles/top-5-rag-observability-platforms-in-2026/) — MEDIUM confidence (vendor-authored; useful for competitor landscape)
- [Python proxy / delegation patterns — wrapt docs](https://wrapt.readthedocs.io/en/latest/wrappers.html) — HIGH confidence (official library docs)
- [RAG corpus quality — EvidentlyAI guide](https://www.evidentlyai.com/llm-guide/rag-evaluation) — MEDIUM confidence (practitioner guide)
- [RAG Monitoring Benchmark 2026 — AIM Research](https://research.aimultiple.com/rag-monitoring/) — LOW confidence (analyst site; used for market context only)

---
*Feature research for: RAG corpus analytics / vector DB wrapper (rag-memento)*
*Researched: 2026-03-24*
