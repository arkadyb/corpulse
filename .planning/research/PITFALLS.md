# Pitfalls Research

**Domain:** RAG corpus analytics library — vector DB wrapper, observability layer, Python packaging
**Researched:** 2026-03-24
**Confidence:** HIGH (pitfalls derived from direct code inspection + verified community patterns)

---

## Critical Pitfalls

### Pitfall 1: Async/Sync Mismatch in the Qdrant Wrapper

**What goes wrong:**
The Qdrant Python client ships two entirely separate classes: `QdrantClient` (sync) and `AsyncQdrantClient`. If the wrapper only subclasses or wraps `QdrantClient`, any user running an async RAG pipeline (LangChain async, FastAPI, etc.) will hit either a `RuntimeError: This event loop is already running` or a blocking call inside a coroutine. The wrapper silently works in tests (which are typically sync) but breaks in production.

**Why it happens:**
Developers write the wrapper against the sync client because it is simpler, test it in a plain script, ship it, and only discover the async incompatibility when a user opens an issue. The two client classes have identical method names but different return types (`Coroutine[...]` vs the result directly), so a single wrapper cannot transparently serve both.

**How to avoid:**
Design the wrapper to support both clients from the start. Concrete approach: accept `client: QdrantClient | AsyncQdrantClient` in `__init__`; in each intercepted method, detect the return type with `inspect.iscoroutine()` and either await it (inside an async wrapper method) or return it directly. Alternatively, provide two wrapper classes — `QdrantMementoClient` and `AsyncQdrantMementoClient` — that mirror the upstream split. The second approach is more explicit and easier to test.

**Warning signs:**
- Wrapper tests only use `QdrantClient` in a `__main__` block, never `pytest-asyncio`
- `async def` versions of intercepted methods are absent from the wrapper class
- Issue titles mentioning "event loop", "RuntimeError", or "not awaitable"

**Phase to address:**
Qdrant wrapper phase — must be decided before writing the first line of wrapper code.

---

### Pitfall 2: Silent Data Loss When Qdrant Returns No `doc_id`

**What goes wrong:**
Qdrant `ScoredPoint` objects use an integer or UUID `.id` field — not a `doc_id` string key. The existing `log_retrieval` API expects `{"doc_id": ..., "filename": ..., "score": ...}` dicts. If the wrapper maps `point.id` to `doc_id` and the collection stores doc identifiers inside the payload (e.g. `point.payload["document_id"]` or `point.payload["source"]`), the wrapper will silently log Qdrant's internal integer IDs instead of the document identifiers the user actually cares about. All downstream ghost/duplicate/stale detection then runs against meaningless integer IDs, and `filename` columns will all read as the integer ID string.

**Why it happens:**
There is no single convention for payload field names in Qdrant. Users store doc IDs under `"id"`, `"doc_id"`, `"source"`, `"filename"`, `"metadata.source"`, and so on. A hardcoded mapping breaks silently rather than raising an error.

**How to avoid:**
Add a `payload_id_field` parameter to the wrapper (default `"doc_id"`), and a `payload_filename_field` (default `"filename"`). Fall back to the point's integer `.id` only when the payload field is absent, and emit a `warnings.warn()` the first time the fallback fires so users know to configure the field names. Document the convention prominently in the docstring.

**Warning signs:**
- Analytics show every document has a short integer filename like `"12345"`
- All documents are identified as ghosts immediately after wrapper setup
- No duplicates are detected despite obviously similar content

**Phase to address:**
Qdrant wrapper phase — the `payload_id_field` parameter should be part of the wrapper's constructor API from day one.

---

### Pitfall 3: Per-Query SQLite Write Creates a Lock-Per-Search Bottleneck

**What goes wrong:**
The current `DB._conn()` opens a new `sqlite3.connect()` on every call. Under the wrapper, every Qdrant search triggers two or more DB writes (upsert_document + insert_retrieval per result). In a high-throughput async service making dozens of queries per second, concurrent coroutines all try to acquire the write lock simultaneously, producing `sqlite3.OperationalError: database is locked` errors in the user's application.

**Why it happens:**
SQLite's default journal mode serializes all writers. The existing synchronous, single-request-at-a-time usage pattern hides this completely — the demo script never runs two `log_retrieval` calls concurrently.

**How to avoid:**
Enable WAL mode (`PRAGMA journal_mode=WAL`) in `DB._init()` — this is a one-line addition and drops the contention dramatically for the typical read-heavy, occasional-write pattern. Additionally, set `timeout` on the connection (e.g. `sqlite3.connect(..., timeout=10)`) so writes queue rather than fail immediately. For very high throughput, a background write queue (queue + dedicated writer thread) is the correct pattern, but WAL mode is sufficient for v1 given the project's zero-infrastructure constraint.

**Warning signs:**
- `sqlite3.OperationalError: database is locked` in user bug reports
- The DB `_conn()` method has no `timeout` argument
- `PRAGMA journal_mode` is not set anywhere in `DB._init()`

**Phase to address:**
SQLite/DB layer phase (or packaging phase when tests are added) — add a test with `threading.Thread` + concurrent `log_retrieval` calls to surface this before shipping.

---

### Pitfall 4: O(n²) Cosine Similarity Blows Up for Large Corpora

**What goes wrong:**
`get_duplicates()` loads all embeddings into memory and runs `cosine_similarity(vecs)` — a full n×n matrix computation. At 1,000 documents this is fine (1M operations). At 50,000 documents it allocates ~10 GB of RAM and stalls for minutes. If the Qdrant wrapper auto-captures embeddings from every search result, corpora will grow past safe threshold without any user action.

**Why it happens:**
The current v0.1 code was written for small corpora (demo uses 13 docs). The n² scaling is intentional for accuracy but becomes a hidden footgun as users onboard real production collections.

**How to avoid:**
Add a `max_docs_for_exact_duplicate_check` threshold (default 5,000) in `corpus_health()` and `get_duplicates()`. When the doc count exceeds it, either skip the exact check and emit a warning, or use approximate nearest-neighbour sampling (random sample of 5k docs). Document the scaling limitation clearly in the docstring. This is not a rewrite — it is a guard clause and a config parameter.

**Warning signs:**
- Users report `get_duplicates()` hanging or OOM-killing their process
- No `max_docs` parameter exists on `get_duplicates()`
- `corpus_health()` calls `get_duplicates()` twice (it currently does — lines 328–334 in memento.py)

**Phase to address:**
Test suite phase — add a test with 10,000 synthetic embeddings to verify the guard fires. Also fixable as a known-issue note in documentation.

---

### Pitfall 5: Wrapper Swallows the Qdrant Client's Interface

**What goes wrong:**
If the wrapper subclasses `QdrantClient` and overrides only `search()`, users who call `client.query_points()`, `client.scroll()`, or future methods will bypass the wrapper entirely and get no observability. Alternatively, if the wrapper delegates via `__getattr__` to an inner client instance, calls like `type(client)` will return the wrapper class, breaking any code that does `isinstance(client, QdrantClient)` (common in LangChain's vector store internals).

**Why it happens:**
Both common proxy approaches (subclassing vs. composition with `__getattr__`) have this blind spot. Subclassing misses non-overridden methods silently; composition breaks `isinstance` checks.

**How to avoid:**
Use composition (not subclassing) and also register the wrapper against `QdrantClient` via `QdrantClient.register(MementoQdrantClient)` if the upstream ABC supports it, or just document the limitation. For the v1 scope, intercept only `search()` and `query_points()` explicitly — do not attempt transparent full-proxy interception. Document which methods are instrumented and which are pass-through. This is the honest, maintainable choice.

**Warning signs:**
- Wrapper class has a `__getattr__` that delegates everything to `self._client`
- No explicit list of "instrumented methods" in the class docstring
- Tests only call `client.search()`, never `client.query_points()` or `client.scroll()`

**Phase to address:**
Qdrant wrapper phase — architectural decision that must be explicit in the wrapper's docstring/README.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode `"doc_id"` and `"filename"` as payload field names | Simpler first wrapper | Silent wrong data for 80% of real-world Qdrant collections | Never — add `payload_id_field` param from day one |
| Skip WAL mode in SQLite | Zero extra code | `database is locked` errors for any async user | Never — it is a one-line pragma |
| Only wrap `search()`, not `query_points()` | Faster to ship | Users on qdrant-client ≥1.7 (which prefers `query_points`) get no instrumentation | Acceptable for v1 if documented clearly |
| No upper bound on embedding storage | Simpler inserts | DB grows unbounded; duplicate detection OOMs | Acceptable for v1 if the O(n²) guard exists |
| Use `from __future__ import annotations` + `TYPE_CHECKING` for qdrant-client types | Avoids hard import dep | Type checkers silently skip validation if import guard is wrong | Acceptable — but test with and without qdrant-client installed |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Qdrant `ScoredPoint` | Accessing `.id` and assuming it's a doc identifier | Check `point.payload` first; `.id` is Qdrant's internal integer/UUID |
| Qdrant `search()` vs `query_points()` | Only wrapping `search()` — deprecated in qdrant-client ≥1.7.4 | Wrap both; `query_points()` is the current recommended API |
| qdrant-client optional install | Importing `qdrant_client` at module top-level, failing on import even without wrapper | Guard with `TYPE_CHECKING` import + lazy import inside wrapper `__init__` |
| SQLite + Python threads | `sqlite3` connections are not thread-safe by default | Pass `check_same_thread=False` OR create a new connection per thread (current pattern); current code opens per-call which is safe but slow |
| Optional scikit-learn | Raising `RuntimeError` at call-time (current pattern, correct) vs raising at import | Current pattern is correct; preserve it for qdrant-client too |
| pyproject.toml extras | Using underscores in extra names (`qdrant_support`) | Use hyphens: `qdrant-support`; pip normalizes but mixing causes confusion |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| O(n²) duplicate matrix | `get_duplicates()` hangs / OOM | Add doc-count guard, skip or sample above threshold | ~5,000 docs at 1536-dim (OpenAI) embeddings |
| New SQLite connection per write | Latency spikes under concurrent load | WAL mode + connection pool or single writer thread | ~10 concurrent writers |
| Loading all embeddings into RAM | `all_embeddings()` returns 500MB BLOB | Add pagination or explicit limit to `all_embeddings()` | ~100k docs with 1536-dim floats |
| `corpus_health()` calls `get_duplicates()` twice | Report generation takes 2× as long as necessary | Cache result or compute once and reuse | Already a bug at any scale above ~1k docs |
| No embedding stored in wrapper (pass-through only retrieval scores) | Duplicate detection never fires | Ensure wrapper extracts `vectors` from `ScoredPoint` when `with_vectors=True` | From day 1 if wrapper forgets to pass `with_vectors=True` |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Writing the SQLite DB to the current working directory by default (`./memento.db`) | DB may be created inside a web-serving directory and exposed | Default path is acceptable for a library; document that production deployments should configure an explicit `db_path` outside web root |
| Storing raw query hashes (SHA-256 truncated) | Query content is partially reconstructable if hashes are shared | The 16-char truncation is intentional for privacy; document that full queries are never persisted |
| Qdrant API key passed through wrapper | If wrapper logs kwargs for debugging, API key may appear in logs | Never log `**kwargs` passed to the inner client; only log intercepted search metadata |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Wrapper raises `ImportError` at import time if qdrant-client is absent | Users who installed `rag-memento` without the `[qdrant]` extra see a confusing top-level import failure | Lazy-import qdrant-client inside wrapper `__init__`; raise a clear `ImportError("pip install rag-memento[qdrant]")` only when the wrapper is instantiated |
| Wrapper requires users to also call `memento.log_retrieval()` | Users adopted the wrapper precisely to avoid manual instrumentation; double-calling creates duplicate entries | Wrapper must be self-contained; document that `log_retrieval()` should NOT be called alongside the wrapper |
| `cleanup_report()` prints to stdout with emoji | Breaks in CI environments without UTF-8 terminals; not machine-readable | Preserve for interactive use; add a `get_cleanup_report() -> dict` programmatic alternative |
| No indication that observability only starts from wrapper instantiation (no historical data) | Users expect ghost detection to work from day 1 but they have zero retrieval history | Add a warning in `report()` when total retrieval count is below a minimum threshold (e.g. `< 10`) |
| Extra name inconsistency between docs and actual package | Users try `pip install rag-memento[qdrant_support]` vs `rag-memento[qdrant]` | Pick one canonical extra name in `pyproject.toml` (`qdrant`) and use it everywhere |

---

## "Looks Done But Isn't" Checklist

- [ ] **Qdrant wrapper:** `query_points()` instrumented, not just `search()` — verify both method names have interceptors
- [ ] **Qdrant wrapper:** Async client path tested, not just sync — verify `pytest-asyncio` test exists
- [ ] **Qdrant wrapper:** `payload_id_field` is configurable — verify constructor accepts it
- [ ] **SQLite:** WAL mode enabled — verify `PRAGMA journal_mode=WAL` in `DB._init()`
- [ ] **Optional import:** `qdrant_client` is not imported at the top of the wrapper module — verify with `python -c "import rag_memento"` without qdrant-client installed
- [ ] **corpus_health():** `get_duplicates()` called only once — verify by reading lines 328–334 of memento.py (currently called twice)
- [ ] **Packaging:** `qdrant-client` declared under `[project.optional-dependencies]` in pyproject.toml, not `[project.dependencies]` — verify with `pip install rag-memento` (no Qdrant) succeeds
- [ ] **Wrapper docs:** States which methods are instrumented and which are pass-through — verify docstring explicitly lists them
- [ ] **Python 3.10+ types:** `X | Y` union syntax and `match` statements compile on 3.10 — verify `python_requires = ">=3.10"` is in pyproject.toml
- [ ] **Test suite:** Concurrent `log_retrieval()` test exists — verify no `database is locked` under threading

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Async/sync mismatch discovered post-release | HIGH | Add `AsyncQdrantMementoClient`; bump minor version; update docs with migration note |
| Silent wrong doc IDs (no payload field config) | HIGH | Add `payload_id_field`; data in existing DBs is unrecoverable (wrong IDs logged); users must reset DB |
| `database is locked` in production | LOW | Add WAL pragma + timeout in a patch release; existing DBs automatically use WAL on next open |
| O(n²) OOM for large corpus | MEDIUM | Add guard clause in patch release; no data migration needed |
| `corpus_health()` double-calling `get_duplicates()` | LOW | One-line fix: cache result in local variable |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Async/sync mismatch | Qdrant wrapper | `pytest-asyncio` test: wrap `AsyncQdrantClient`, call async search, verify retrieval logged |
| Silent wrong doc IDs | Qdrant wrapper | Unit test: collection with `payload["source"]` field; assert logged `doc_id == payload["source"]` not point integer id |
| SQLite lock under concurrency | Packaging / test suite | Threading test: 10 threads each call `log_retrieval()` 100×; assert zero `OperationalError` |
| O(n²) duplicate OOM | Test suite | Performance test: insert 10k docs; assert `get_duplicates()` returns in <5s or emits warning |
| Wrapper swallows interface | Qdrant wrapper | Test: call `client.scroll()` on the wrapper; assert it does not raise and returns Qdrant results |
| qdrant-client import at top-level | Packaging | `pip install rag-memento` (no qdrant extra) in a fresh venv; `python -c "import rag_memento"` must succeed |
| `corpus_health()` double-duplication call | Test suite | Assert `get_duplicates()` mock called exactly once when `corpus_health()` is invoked |

---

## Sources

- Qdrant Python client source: `QdrantClient` vs `AsyncQdrantClient` split — [qdrant-client GitHub](https://github.com/qdrant/qdrant-client) (HIGH confidence)
- Qdrant `ScoredPoint` structure with `.id`, `.payload`, `.score` — [Qdrant Client docs](https://python-client.qdrant.tech/qdrant_client.qdrant_client) (HIGH confidence)
- `query_points()` as the current recommended search API — [Qdrant API reference](https://api.qdrant.tech/api-reference/search/query-points) (HIGH confidence)
- SQLite WAL mode and single-writer bottleneck — [SQLite WAL docs](https://www.sqlite.org/wal.html), [SkyPilot blog on SQLite concurrency](https://blog.skypilot.co/abusing-sqlite-to-handle-concurrency/) (HIGH confidence)
- pyproject.toml optional dependencies and extra name normalization — [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) (HIGH confidence)
- Optional import UX pattern — [Python.org discussion](https://discuss.python.org/t/optional-imports-for-optional-dependencies/104760) (MEDIUM confidence)
- O(n²) duplicate check, double-call in `corpus_health()` — direct code inspection of `/Users/arkady/src/rag-memento/memento.py` lines 328–334 (HIGH confidence)
- Per-call `sqlite3.connect()` pattern — direct code inspection of `/Users/arkady/src/rag-memento/db.py` (HIGH confidence)

---
*Pitfalls research for: RAG corpus analytics library (rag-memento) — Qdrant wrapper + packaging milestone*
*Researched: 2026-03-24*
