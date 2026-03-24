# Architecture Research

**Domain:** Vector DB wrapper/proxy library for RAG corpus analytics
**Researched:** 2026-03-24
**Confidence:** HIGH (existing codebase examined directly; Qdrant client API verified against official docs)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        User Application                          │
│  (RAG pipeline — embeds query, searches, uses retrieved docs)    │
└─────────────────────────┬────────────────────────────────────────┘
                          │ creates & calls
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                  QdrantMementoClient  (new)                       │
│  Thin delegation wrapper — same interface as QdrantClient        │
│                                                                  │
│  query_points()        ──►  delegate to real QdrantClient        │
│                        ◄──  receive QueryResponse                │
│                         │                                        │
│                         │  ResultNormalizer.normalize()          │
│                         ▼                                        │
│                  [ list[dict] ]  (memento's format)              │
│                         │                                        │
│                         │  memento.log_retrieval()               │
│                         ▼                                        │
│  pass-through result ──►  caller gets unmodified QueryResponse   │
└──────────┬───────────────────────────────────────────────────────┘
           │ wraps
           ▼
┌─────────────────────────┐    ┌──────────────────────────────────┐
│  qdrant_client          │    │  Memento  (existing)             │
│  QdrantClient           │    │                                  │
│  (unchanged)            │    │  log_retrieval()                 │
│                         │    │  log_engagement()                │
│  query_points()         │    │  log_source_update()             │
│  query_batch_points()   │    │  get_ghosts()  …etc              │
│  scroll()               │    └──────────────┬───────────────────┘
│  retrieve()             │                   │ writes to
└─────────────────────────┘                   ▼
                                   ┌──────────────────────┐
                                   │  DB  (existing)      │
                                   │  SQLite              │
                                   │                      │
                                   │  documents           │
                                   │  retrievals          │
                                   │  engagements         │
                                   └──────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `QdrantMementoClient` | Transparent delegation wrapper; intercepts query calls to feed Memento | New class in `rag_memento/integrations/qdrant.py` |
| `ResultNormalizer` | Converts Qdrant `ScoredPoint` objects into the `list[dict]` format `Memento.log_retrieval()` expects | Helper function/class inside the integration module |
| `Memento` | Existing analytics facade — stores events, runs analysis, produces reports | Unchanged; `memento.py` |
| `DB` | SQLite persistence for documents, retrievals, engagements | Unchanged; `db.py` |
| `QdrantClient` (upstream) | Real Qdrant network/local client being wrapped | External dependency; never subclassed |

## Recommended Project Structure

```
rag_memento/                  # renamed from flat files → package dir
├── __init__.py               # exports Memento + QdrantMementoClient
├── memento.py                # existing core (unchanged)
├── db.py                     # existing persistence (unchanged)
└── integrations/
    ├── __init__.py
    └── qdrant.py             # QdrantMementoClient + ResultNormalizer

tests/
├── test_memento.py           # unit tests for core analytics
├── test_db.py                # unit tests for DB layer
└── integrations/
    └── test_qdrant.py        # wrapper tests (with mock QdrantClient)

pyproject.toml
```

### Structure Rationale

- **`integrations/` subdirectory:** Isolates all vector-DB-specific code. When Chroma or Pinecone wrappers are added later, they land here without touching core. The `qdrant-client` import lives only in this file, so the library core stays importable without Qdrant installed.
- **`ResultNormalizer` inside `qdrant.py`:** Not a separate module — it is a small, integration-specific conversion function. Keeping it co-located with the wrapper avoids over-engineering.
- **Flat `tests/` layout:** Mirrors `rag_memento/` structure so test paths are predictable.

## Architectural Patterns

### Pattern 1: Delegation Wrapper (chosen approach)

**What:** `QdrantMementoClient` holds a real `QdrantClient` instance as `self._client` and explicitly implements each intercepted method. Every non-intercepted attribute falls through via `__getattr__` to `self._client`.

**When to use:** When you need to intercept a specific, stable set of methods (query calls) while delegating everything else (collection management, point upserts, etc.) transparently. Preferred over inheritance because `QdrantClient` is not designed to be subclassed and its constructor wires internal transport choices.

**Trade-offs:**
- (+) Caller sees a familiar interface identical to `QdrantClient`
- (+) `qdrant-client` internals can change without breaking the wrapper
- (+) Easy to test — inject a mock for `self._client`
- (-) Must explicitly list each intercepted method; new Qdrant methods are not auto-intercepted

**Example:**
```python
class QdrantMementoClient:
    def __init__(self, client: QdrantClient, memento: Memento):
        self._client = client
        self._memento = memento

    def query_points(self, collection_name, query, **kwargs):
        response = self._client.query_points(collection_name, query, **kwargs)
        records = _normalize_query_response(response)
        self._memento.log_retrieval(records)
        return response  # caller gets exactly what they expected

    def __getattr__(self, name):
        # All other attributes (upsert, create_collection, etc.) pass through
        return getattr(self._client, name)
```

### Pattern 2: Result Normalization

**What:** A pure function `_normalize_query_response(response: QueryResponse) -> list[dict]` translates Qdrant's `ScoredPoint` objects into the `dict` format `Memento.log_retrieval()` accepts (`doc_id`, `filename`, `score`, `embedding`).

**When to use:** Every time a search response is intercepted. Centralizing this translation means future Qdrant API changes only require a fix in one place.

**Trade-offs:**
- (+) Decouples Memento's format from Qdrant's format — changes to either side are isolated
- (+) Easy to unit-test independently
- (-) Requires mapping decisions (e.g., `point.id` → `doc_id`, `point.payload.get("filename")` → `filename`)

**Example:**
```python
def _normalize_query_response(response) -> list[dict]:
    records = []
    for point in response.points:
        records.append({
            "doc_id":    str(point.id),
            "filename":  (point.payload or {}).get("filename", str(point.id)),
            "score":     float(point.score),
            # embedding only if vectors were requested
            "embedding": point.vector if point.vector is not None else None,
        })
    return records
```

### Pattern 3: Async Mirror

**What:** `QdrantMementoClient` provides `async_query_points()` (or an async variant) that wraps `AsyncQdrantClient` the same way. Qdrant's sync and async clients share identical method signatures, so the normalization logic is reused.

**When to use:** Only when the user is already using `AsyncQdrantClient`. This is additive — sync wrapper ships first; async is a follow-on.

**Trade-offs:**
- (+) Covers async RAG pipelines (common in FastAPI / LangGraph apps)
- (-) Doubles the intercepted-method surface to maintain
- Implementation note: `Memento.log_retrieval()` is synchronous I/O (SQLite); in async context, run it in a thread via `asyncio.to_thread()` or accept that short SQLite writes are acceptable blocking on the event loop for now

## Data Flow

### Query Interception Flow

```
User app
  │
  │  client.query_points(collection, query_vec, limit=10)
  ▼
QdrantMementoClient.query_points()
  │
  ├──► self._client.query_points(...)   [network/local call to Qdrant]
  │         │
  │         ▼
  │    QueryResponse (list of ScoredPoint: id, score, payload, vector)
  │         │
  ├──► _normalize_query_response(response)
  │         │
  │         ▼
  │    list[dict]: [{doc_id, filename, score, embedding}, ...]
  │         │
  ├──► self._memento.log_retrieval(records)
  │         │
  │         ▼
  │    DB.upsert_document() + DB.insert_retrieval()  [SQLite writes]
  │
  └──► return original QueryResponse to caller  [unmodified]
```

### Key Data Flows

1. **Query path (hot path):** Qdrant network call → response → normalization → SQLite write → return to caller. SQLite write is synchronous and append-only; expected latency is sub-millisecond for typical result sets.
2. **Analytics path (cold path):** User calls `memento.report()` or `memento.get_ghosts()` → reads SQLite → returns analysis. This is entirely independent of query interception; can be called any time.
3. **Embedding capture:** If the user requests `with_vectors=True` in `query_points`, `ScoredPoint.vector` is non-None and the normalizer passes it to `log_retrieval`, enabling duplicate detection. If vectors are not requested, duplicate detection falls back to previously stored vectors.

## Scaling Considerations

This is a local observability library, not a distributed service. Scale here means corpus size, not request throughput.

| Scale | Architecture adjustment |
|-------|------------------------|
| < 100k documents | Default SQLite, no changes needed |
| 100k–1M documents | SQLite handles well; duplicate detection (O(n²) cosine sim) becomes the bottleneck — add a `sample` parameter or batch processing to `get_duplicates()` |
| > 1M documents | SQLite still fine for event tables; embedding matrix comparison needs chunking or approximate nearest-neighbor index (future milestone) |

### Scaling Priorities

1. **First bottleneck:** `get_duplicates()` loads all embeddings into RAM for pairwise cosine similarity. At ~50k 1536-dim vectors, this is ~300 MB. Add a `limit` parameter or ANN-based deduplication.
2. **Second bottleneck:** SQLite write contention in multi-threaded RAG servers. The current `_conn()` context manager opens a new connection per write. For high-concurrency scenarios, switch to a connection pool or WAL mode.

## Anti-Patterns

### Anti-Pattern 1: Subclassing QdrantClient

**What people do:** `class QdrantMementoClient(QdrantClient): def query_points(...): super().query_points(...)...`

**Why it's wrong:** `QdrantClient.__init__` has complex transport logic (chooses between REST, gRPC, local). Subclassing couples the wrapper to implementation details that are not part of the public API. If Qdrant reorganizes internals, the wrapper breaks. The `QdrantClient` maintainers do not document it as a base class.

**Do this instead:** Wrap via composition (`self._client = client`). Only expose what you intercept; delegate the rest via `__getattr__`.

### Anti-Pattern 2: Modifying the Return Value

**What people do:** Return the normalized `list[dict]` instead of the original `QueryResponse`, to "simplify" the caller's code.

**Why it's wrong:** The caller wrote their RAG pipeline expecting a `QueryResponse` with `ScoredPoint` objects. Changing the return type is a silent breaking change. The wrapper's job is observability, not transformation.

**Do this instead:** Always return the original upstream response unmodified. The analytics side-effect happens entirely inside the wrapper.

### Anti-Pattern 3: Catching and Suppressing Qdrant Errors

**What people do:** Wrap the Qdrant call in `try/except` to ensure Memento logging always runs even on error.

**Why it's wrong:** If Qdrant raises (network error, bad collection name), the caller needs to see that exception. Silently swallowing it, or logging it and returning empty results, hides real failures.

**Do this instead:** Let Qdrant exceptions propagate naturally. The Memento side-effect write should only happen after a successful response. If the Memento write itself fails (SQLite error), log a warning but do not let it block the return of valid search results.

### Anti-Pattern 4: Hard Dependency on qdrant-client in Core

**What people do:** Import `from qdrant_client import QdrantClient` in `memento.py` or `__init__.py`.

**Why it's wrong:** Forces all rag-memento users to install qdrant-client even if they use a different vector DB or only use the manual API.

**Do this instead:** Keep the Qdrant import isolated inside `rag_memento/integrations/qdrant.py`. Declare `qdrant-client` as an optional dependency (`pip install rag-memento[qdrant]`) in pyproject.toml. Use a lazy import guard inside the integration module.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| `qdrant-client` (sync) | Composition — `QdrantMementoClient` holds `QdrantClient` instance | User constructs `QdrantClient` themselves and passes it in; wrapper does not manage connection lifecycle |
| `qdrant-client` (async) | Same composition pattern with `AsyncQdrantClient` | Phase 2 addition; requires `asyncio.to_thread()` for SQLite writes |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `QdrantMementoClient` → `Memento` | Direct method call (`memento.log_retrieval()`) | The Memento instance is injected at construction time; wrapper owns no analytics logic |
| `QdrantMementoClient` → `QdrantClient` | Direct delegation (`self._client.method()`) + `__getattr__` fallthrough | Wrapper is transparent to non-intercepted operations |
| `Memento` → `DB` | Direct method calls | Unchanged from existing implementation |
| `ResultNormalizer` → `Memento` format | Pure function; input: `QueryResponse`, output: `list[dict]` | Isolated translation layer; testable without Qdrant or Memento |

## Suggested Build Order

Dependencies between components determine this order:

1. **`ResultNormalizer` (`_normalize_query_response`)** — Pure function, no dependencies. Build and test in isolation first. This is the riskiest mapping decision (Qdrant's `point.id` type, payload shape) and needs validation against a real response.

2. **`QdrantMementoClient` (sync, `query_points` only)** — Depends on normalizer and existing `Memento`. Implement delegation wrapper with `__getattr__`, intercept `query_points`, write tests with a mock `QdrantClient`.

3. **Extend to `query_batch_points`** — Same pattern, batch variant. Normalizer already exists; just loop over batch responses.

4. **Optional: `AsyncQdrantClient` mirror** — Only if async support is in scope for this milestone. Keep as a separate class or a flag on construction.

5. **Package restructuring (pyproject.toml, extras)** — Not a blocker for wrapper logic, but should ship in the same milestone to enable `pip install rag-memento[qdrant]`.

## Sources

- Qdrant Python client official docs: [python-client.qdrant.tech](https://python-client.qdrant.tech/qdrant_client.qdrant_client) — `query_points` signature and `QueryResponse` structure (HIGH confidence, official docs)
- Qdrant client GitHub: [github.com/qdrant/qdrant-client](https://github.com/qdrant/qdrant-client/blob/master/qdrant_client/qdrant_client.py) — composition-based internal architecture (HIGH confidence, source code)
- OpenLLMetry Qdrant instrumentation: [github.com/traceloop/openllmetry](https://github.com/traceloop/openllmetry/tree/main/packages/opentelemetry-instrumentation-qdrant) — prior art for wrapping Qdrant calls (MEDIUM confidence, reference implementation)
- Python delegation/proxy patterns: [python-patterns.guide](https://python-patterns.guide/gang-of-four/decorator-pattern/) — `__getattr__` delegation pattern (HIGH confidence, canonical reference)
- Qdrant async API tutorial: [qdrant.tech/documentation/tutorials-develop/async-api](https://qdrant.tech/documentation/database-tutorials/async-api/) — async client structure (HIGH confidence, official docs)
- Existing codebase: `/Users/arkady/src/rag-memento/memento.py`, `db.py`, `__init__.py` — direct inspection of Memento/DB API contracts (HIGH confidence)

---
*Architecture research for: rag-memento Qdrant wrapper*
*Researched: 2026-03-24*
