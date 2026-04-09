# Pitfalls Research

**Domain:** Pluggable storage backends — adding SQLite/Postgres/InMemory abstraction to an existing Python library
**Researched:** 2026-04-08
**Confidence:** HIGH (derived from direct codebase inspection + verified community patterns)

---

## Critical Pitfalls

### Pitfall 1: SQLite BLOB → PostgreSQL BYTEA Type Mismatch

**What goes wrong:**
`db.py` stores numpy float32 embeddings via `np.array(vec, dtype=np.float32).tobytes()` and reads them back via `np.frombuffer(b, dtype=np.float32)`. In SQLite, a BLOB column is a raw bytes buffer. In PostgreSQL with psycopg, BYTEA columns are returned as `memoryview` objects, not `bytes`. Passing a `memoryview` to `np.frombuffer()` technically works but is brittle — any intermediate step that calls `bytes(row["embedding_vec"])` or `len(row["embedding_vec"])` to check length will silently succeed, while `.tobytes()` without explicit decode will not. More critically, psycopg2 additionally applies hex-escaping to BYTEA values unless you explicitly call `psycopg2.extras.register_default_jsonb()` or use the binary format, making the raw bytes look like `\x3f...` strings on retrieval. psycopg3 (psycopg) improves this but the type returned is still `memoryview`, not `bytes`.

**Why it happens:**
The `_bytes_to_vec()` helper in `core.py` uses `np.frombuffer(b, dtype=np.float32)`, which works with both `bytes` and `memoryview` — so it appears to work. The bug only manifests when the embedding is passed through any code that treats it as `bytes` (e.g., length checks, logging, passing to other libraries). Tests written against SQLiteBackend never see the memoryview type.

**How to avoid:**
The StorageBackend interface should specify that `embedding_vec` is always returned as `bytes`, not `memoryview`. PostgresBackend must convert on read: `bytes(row["embedding_vec"])`. InMemoryBackend should store and return `bytes`. Add a test that calls `isinstance(result["embedding_vec"], bytes)` across all backend implementations.

**Warning signs:**
- Duplicate detection silently returns no pairs after switching backends
- `np.frombuffer()` crashes with `ValueError: buffer is smaller than requested size`
- Postgres backend passes unit tests but fails integration tests that check embedding round-trips

**Phase to address:**
Phase 1 (StorageBackend interface definition) — the return type contract for `embedding_vec` must be `bytes`, not `Any`, in the Protocol definition.

---

### Pitfall 2: Unix Float Timestamps vs PostgreSQL Native Timestamps

**What goes wrong:**
The existing schema stores all timestamps as `REAL` (Unix epoch float, e.g. `1712518400.0`). The queries `retrieval_counts(since: float)` and `engagement_counts(since: float)` use `WHERE retrieved_at >= ?` with a float. PostgreSQL does not have a native float-epoch timestamp type — if you keep the columns as `DOUBLE PRECISION` in Postgres, comparisons work but you lose all native Postgres date/time capabilities (indexing with `BRIN`, `now()`, timezone awareness). If you instead migrate to `TIMESTAMP WITH TIME ZONE`, the existing Python code that produces `time.time()` floats must be converted at the boundary using `datetime.fromtimestamp(ts, tz=timezone.utc)`, otherwise inserts will fail with `DataError: invalid input syntax for type timestamp`.

**Why it happens:**
The SQLite schema was designed for zero-infrastructure simplicity. Unix floats are SQLite-idiomatic. The Postgres backend is tempting to design by copying the same schema, but doing so means either (a) keeping `DOUBLE PRECISION` columns and accepting no native date indexing, or (b) adding a timestamp conversion layer that is invisible to callers but required for correctness.

**How to avoid:**
Use `DOUBLE PRECISION` in the Postgres schema for `retrieved_at`, `engaged_at`, `embedded_at`, and `source_updated_at`. This keeps the interface identical across backends — callers always pass Unix floats, the backend stores Unix floats, the `since` queries filter on `>= ?`. Add an explicit comment in the schema migration stating this is intentional and not a future-proofing oversight. If native timestamp types are later needed, that is a separate migration concern.

**Warning signs:**
- Postgres schema uses `TIMESTAMP` columns without a conversion layer in `insert_retrieval()`
- `DataError: invalid input syntax for type timestamp` in Postgres integration tests
- The `since` parameter is documented as `float` in the interface but the Postgres backend passes it through `datetime.fromtimestamp()` before the query, hiding the conversion from callers

**Phase to address:**
Phase 1 (interface definition) — pin the timestamp convention (`float` = Unix epoch) in the Protocol docstring; Phase 2 (PostgresBackend) — verify schema uses `DOUBLE PRECISION`.

---

### Pitfall 3: `ON CONFLICT` / Upsert Dialect Incompatibility

**What goes wrong:**
`db.py` uses SQLite's `INSERT ... ON CONFLICT(doc_id) DO UPDATE SET ...` upsert syntax (available in SQLite 3.24+). PostgreSQL uses identical syntax (`INSERT ... ON CONFLICT (doc_id) DO UPDATE SET ...`), so this looks portable — but there is a subtle difference: SQLite uses `excluded.column_name` and PostgreSQL also uses `EXCLUDED.column_name` (uppercase by convention). This particular case happens to work across both. However, `COALESCE(excluded.embedding_vec, embedding_vec)` in the upsert is SQLite-style. In PostgreSQL, `EXCLUDED` refers to the proposed-for-insert row, so `COALESCE(EXCLUDED.embedding_vec, documents.embedding_vec)` is the correct Postgres form — note the table-qualified reference to the existing row value. Using the unqualified form is ambiguous in PostgreSQL and may raise `ERROR: column reference "embedding_vec" is ambiguous`.

**Why it happens:**
The SQLite and PostgreSQL upsert syntaxes look nearly identical. Developers copy the SQLite SQL string into the Postgres backend, tests pass with simple inserts, and the ambiguity error only appears when an upsert actually needs to fall back to the existing value (i.e., when `embedding_vec` is `NULL` in the new insert). This only triggers in the `upsert_document()` path when a document is re-inserted without an embedding.

**How to avoid:**
In the PostgresBackend upsert, use fully table-qualified references in the `COALESCE`: `COALESCE(EXCLUDED.embedding_vec, documents.embedding_vec)`. Write a test that inserts a document with an embedding, then re-inserts the same `doc_id` without an embedding (passing `embedding=None`), and asserts the stored embedding is preserved.

**Warning signs:**
- `ProgrammingError: column reference "embedding_vec" is ambiguous` in Postgres tests
- The error only appears after the second insert of the same `doc_id`
- SQLiteBackend tests pass but PostgresBackend upsert test is absent or only tests the initial insert path

**Phase to address:**
Phase 2 (PostgresBackend implementation) — write the upsert test explicitly covering the `embedding=None` re-insert case.

---

### Pitfall 4: asyncio.to_thread for SQLite Inside an Async Qdrant Wrapper Creates Hidden Blocking

**What goes wrong:**
The existing `AsyncQdrantCorpulseClient` calls `await asyncio.to_thread(self._corpulse.log_retrieval, results, query=query)` to avoid blocking the event loop on SQLite writes. This pattern is correct as stated. The hidden danger comes when PostgresBackend is added: if a caller instantiates `AsyncQdrantCorpulseClient` with a `Corpulse(backend=PostgresBackend(...))`, the `asyncio.to_thread` wrapping sends a **synchronous** psycopg call into a thread — which is safe but defeats the purpose of using asyncpg. Conversely, if they use `AsyncPostgresBackend` (which returns coroutines), calling it via `asyncio.to_thread()` will pass a coroutine object to a thread that cannot `await` it, silently returning the unawaited coroutine instead of executing it.

**Why it happens:**
The Qdrant wrapper's async path was designed for SQLite (which has no native async API). When pluggable backends arrive, the wrapper's async dispatch logic becomes backend-type-aware — but nothing in the current design enforces this awareness. The backend interface says nothing about whether methods return values or coroutines.

**How to avoid:**
Define two Protocol variants: `StorageBackend` (sync, all methods return values) and `AsyncStorageBackend` (async, all methods are coroutines). The `AsyncQdrantCorpulseClient` should accept only `AsyncStorageBackend` when async execution is needed. Keep `asyncio.to_thread()` for sync backends (SQLite). Do not mix. The `Corpulse` facade should have a parallel `AsyncCorpulse` variant, or clearly document that `Corpulse` is sync-only and `AsyncQdrantCorpulseClient` requires an async backend. Pick one; document it explicitly.

**Warning signs:**
- `AsyncQdrantCorpulseClient` accepts any `backend=` without type checking
- The async wrapper path uses `asyncio.to_thread()` regardless of backend type
- No test verifies that `AsyncPostgresBackend` methods are actually awaited (not sent to a thread)

**Phase to address:**
Phase 1 (interface definition) — the sync vs. async backend split must be explicit in the Protocol. Phase 3 (AsyncPostgresBackend) — write a test that verifies the async backend's methods are awaited, not thread-dispatched.

---

### Pitfall 5: InMemoryBackend Behavioral Divergence from SQLite

**What goes wrong:**
The `InMemoryBackend` is the primary tool for unit testing. If it is implemented as a simple dict store, it will diverge from SQLite behavior in subtle ways:

1. `retrieval_counts(since)` requires aggregation by `doc_id` with `COUNT`, `AVG(rank)`, `AVG(score)`. A dict implementation that counts per-doc visits will produce the right `cnt` but return `None` for `avg_rank` and `avg_score` if not explicitly computed — callers in `core.py` access `r["avg_rank"]` and `r["avg_score"]` by key, which will raise `KeyError` or silently return `None`.
2. `all_documents()` in SQLite returns `sqlite3.Row` objects (subscriptable by column name). `InMemoryBackend` will return plain dicts or dataclasses — callers that use `row["doc_id"]` work with both, but callers that call `dict(row)` explicitly (e.g., logging, pandas export) may get different structures.
3. Ordering: SQLite returns documents in insertion order; a dict backend in Python 3.7+ preserves insertion order, so this is consistent — but relying on it is fragile.

**Why it happens:**
The InMemoryBackend is written to be "just enough to pass tests" without cross-checking behavior against SQLiteBackend. Divergence only surfaces when a test that passes with InMemoryBackend fails in production with a real backend.

**How to avoid:**
Write a shared test suite (parametrized fixture over all backend implementations) that tests every backend method against identical inputs and asserts identical outputs. This is the most effective guard against InMemoryBackend drift. The InMemoryBackend must implement `retrieval_counts()` with full aggregation (cnt, avg_rank, avg_score), not just a count.

**Warning signs:**
- `InMemoryBackend` tests pass but `get_suspects()` raises `KeyError: 'avg_rank'` with a real backend
- Backend tests are not parametrized — each backend has its own separate test file with duplicated assertions
- `retrieval_counts()` in InMemoryBackend returns `[{"doc_id": ..., "cnt": ...}]` without `avg_rank` and `avg_score`

**Phase to address:**
Phase 1 (InMemoryBackend) — implement full aggregate behavior, not just counts. Write the shared parametrized test fixture immediately and run it against InMemoryBackend and SQLiteBackend before PostgresBackend work begins.

---

### Pitfall 6: Abstraction Leaks Through the `Corpulse` Facade

**What goes wrong:**
`core.py` currently calls `self.db.all_documents()`, `self.db.retrieval_counts(since)`, etc. directly. If any backend-specific error (e.g., `psycopg.OperationalError: connection refused`, `asyncpg.TooManyConnectionsError`) propagates through the facade, the caller receives a backend-specific exception type. A caller catching `sqlite3.OperationalError` for error handling will not catch `psycopg.OperationalError` — they are unrelated exception hierarchies. The abstraction appears clean at the interface level but leaks backend identity through its error types.

**Why it happens:**
The StorageBackend Protocol defines method signatures but not exception behavior. Backends raise their native DB errors; the facade does not translate them.

**How to avoid:**
Define a `StorageBackendError` base exception in the corpulse package. Each backend wraps its native DB exceptions in `StorageBackendError` before raising. The facade catches only `StorageBackendError`. This is a deliberate design choice that must be made in Phase 1 and enforced in every backend's error handling.

**Warning signs:**
- `Corpulse.get_ghosts()` callers must import `psycopg` to handle database errors
- Backend implementations have bare `raise` with no wrapping
- The Protocol definition has no mention of what exceptions methods may raise

**Phase to address:**
Phase 1 (interface definition) — define `StorageBackendError` alongside the Protocol. All backends wrap native exceptions in it.

---

### Pitfall 7: Connection Pool Exhaustion in AsyncPostgresBackend Under Concurrent Load

**What goes wrong:**
asyncpg uses a connection pool with a default `max_size=10`. The `AsyncQdrantCorpulseClient` logs every search result as a separate write. In a production service handling 50 concurrent searches, each search triggering `n` result writes (typically 5-10 per query), the pool is exhausted immediately. asyncpg's default behavior when the pool is exhausted is to block until a connection becomes available or raise `asyncpg.TooManyConnectionsError` if a timeout is configured. Without explicit pool sizing and timeout configuration, the service hangs silently under load — requests queue in the pool's internal queue with no visibility.

**Why it happens:**
Development and tests use a single connection (not a pool) or a pool with default settings. The write pattern of "one DB call per search result" is fine for SQLite (which serializes writes anyway) but creates amplified pool pressure for Postgres under concurrency.

**How to avoid:**
`AsyncPostgresBackend` must accept `min_size` and `max_size` pool parameters and expose a `connect()` / `close()` lifecycle for pool initialization and teardown. Use `asyncpg.create_pool()` rather than single connections. Set a sensible `timeout` on `pool.acquire()` (e.g., 5 seconds) so requests fail fast with a clear error rather than queuing indefinitely. Document the pool sizing recommendation: `max_size >= (expected_concurrent_searches * avg_results_per_search)`.

**Warning signs:**
- `AsyncPostgresBackend` uses `asyncpg.connect()` (single connection) rather than `asyncpg.create_pool()`
- No `min_size` / `max_size` exposed in the backend constructor
- Load tests pass at 1 concurrent request but hang at 10

**Phase to address:**
Phase 3 (AsyncPostgresBackend) — pool design must be explicit from the start; do not add it as an afterthought.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store timestamps as `DOUBLE PRECISION` in Postgres instead of `TIMESTAMP WITH TIME ZONE` | No conversion layer needed; interface stays identical | No native Postgres date indexing; `now()` comparisons awkward | Acceptable for v1 — document intentionally |
| Copy SQLite SQL strings verbatim into PostgresBackend | Fast to write | Subtle dialect differences (COALESCE ambiguity, AUTOINCREMENT vs SERIAL) will surface only in edge-case tests | Never — always validate each SQL against Postgres separately |
| Use `asyncio.to_thread()` for PostgresBackend's sync variant | Reuse existing async dispatch in the Qdrant wrapper | Defeats async I/O; creates unnecessary thread overhead | Acceptable for PostgresBackend (sync) only — async backend must use asyncpg natively |
| Skip `StorageBackendError` wrapping in backends | Less boilerplate | Callers handle backend-specific exceptions; abstraction leaks | Never — define the wrapper exception in Phase 1 |
| InMemoryBackend returns partial rows (no `avg_rank`/`avg_score`) | Faster to implement | Diverges from real backends; tests pass but production fails | Never — implement full aggregation from the start |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| psycopg (psycopg3) BYTEA | Assuming returned value is `bytes` | Always call `bytes(row["embedding_vec"])` — psycopg3 returns `memoryview` for BYTEA |
| asyncpg BYTEA | asyncpg returns `bytes` natively for BYTEA columns | No conversion needed; but verify with `isinstance(val, bytes)` in tests |
| psycopg upsert | Using `COALESCE(excluded.col, col)` (unqualified) | Use `COALESCE(EXCLUDED.col, table_name.col)` to avoid column ambiguity error |
| asyncpg pool | Calling `asyncpg.connect()` for the async backend | Use `asyncpg.create_pool()` with explicit min/max size |
| psycopg sync pool | Not calling `pool.open()` before use | psycopg3's `ConnectionPool` requires explicit `.open()` or use as async context manager |
| SQLiteBackend WAL | WAL mode set via `PRAGMA` in `executescript()` | WAL pragma must run in a separate `conn.execute()` call — `executescript()` issues an implicit `COMMIT` before running, which may interfere with WAL activation on first open |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| One DB call per search result in async backend | Pool exhaustion at moderate concurrency | Batch `insert_retrieval()` calls; add a `insert_retrievals_bulk()` method to the interface | ~10 concurrent searches with 10 results each |
| psycopg3 pipeline mode not used | 3-5× slower than necessary for bulk inserts | Use `conn.pipeline()` context manager for multi-row inserts | Any bulk insert above ~100 rows |
| InMemoryBackend holds all data in a Python list | Slow `retrieval_counts()` scan at large test data volumes | Acceptable for tests — document expected scale ceiling (~10k rows) | Not a production concern; only matters if tests use huge synthetic datasets |
| SQLiteBackend creates new connection per call | Fine under low concurrency; serialization under high concurrency | WAL mode already in schema; existing pattern is acceptable for v1 | ~10 concurrent writes |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Postgres connection string stored in `Corpulse(backend=PostgresBackend("postgres://user:pass@host/db"))` | Connection string (with password) appears in tracebacks, logs, repr() | Accept `dsn` parameter but do not include it in `__repr__`; document that env-var-based config (e.g., `PGPASSWORD`) is preferred |
| Passing user-controlled strings as table/column names | SQL injection via backend configuration | Never use f-strings to build SQL; all column/table names are hardcoded in backend implementations |
| asyncpg `max_inactive_connection_lifetime` not set | Idle connections accumulate and are not recycled on network failures | Set `max_inactive_connection_lifetime=300` in `create_pool()` |

---

## "Looks Done But Isn't" Checklist

- [ ] **embedding_vec round-trip:** `bytes(backend.all_embeddings()[0]["embedding_vec"])` returns identical bytes across all backends — verify with a shared parametrized test
- [ ] **upsert preserves existing embedding:** Insert doc with embedding; re-insert same `doc_id` with `embedding=None`; assert embedding is preserved — verify for both SQLiteBackend and PostgresBackend
- [ ] **retrieval_counts returns avg_rank and avg_score:** Assert `"avg_rank"` and `"avg_score"` keys present in every backend's `retrieval_counts()` return rows
- [ ] **StorageBackendError raised on connection failure:** Mock a connection failure; assert `StorageBackendError` is raised (not `psycopg.OperationalError` or `sqlite3.OperationalError`)
- [ ] **Corpulse() with no args still works:** `Corpulse()` instantiates with SQLiteBackend default, creates `./corpulse.db` — verify backwards compat after refactor
- [ ] **asyncio.to_thread not used for AsyncPostgresBackend:** Verify the async wrapper path calls `await backend.insert_retrieval()` directly, not `await asyncio.to_thread(backend.insert_retrieval, ...)`
- [ ] **Postgres connection pool closed on teardown:** `AsyncPostgresBackend` exposes a `close()` / `aclose()` method and it is documented; verify pool is not leaked in tests
- [ ] **psycopg extras installed:** `pip install corpulse` (without extras) must succeed; `PostgresBackend` raises `ImportError("pip install corpulse[postgres]")` on instantiation if psycopg is absent

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| BYTEA returned as memoryview breaks embedding round-trips | MEDIUM | Add `bytes()` cast in backend's `all_embeddings()` and `all_documents()` reads; no data migration needed |
| Upsert ambiguity silently corrupts embeddings in Postgres | HIGH | Fix SQL to use table-qualified COALESCE; existing rows with lost embeddings must be re-registered |
| asyncio.to_thread + async backend produces unawaited coroutines | HIGH | Requires redesign of the async dispatch layer; existing logs have no data (writes silently failed) |
| InMemoryBackend divergence causes false-passing tests | MEDIUM | Add shared parametrized test suite; no production data loss but investigation cost is high |
| Connection pool exhaustion in production | LOW | Increase `max_size`; restart service; no data loss |
| StorageBackendError not defined — callers catch wrong exceptions | LOW | Add wrapper exception class; patch release; no data loss |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| BYTEA memoryview type mismatch | Phase 1 (interface) + Phase 2 (PostgresBackend) | Shared test: `isinstance(backend.all_embeddings()[0]["embedding_vec"], bytes)` |
| Unix float vs Postgres timestamp | Phase 1 (interface definition, doc the convention) + Phase 2 | Integration test: insert float timestamp, retrieve with `since` filter, assert correct count |
| Upsert COALESCE ambiguity | Phase 2 (PostgresBackend) | Test: re-insert doc with `embedding=None`, assert embedding preserved |
| asyncio.to_thread + async backend mismatch | Phase 1 (Protocol split sync/async) + Phase 3 (AsyncPostgresBackend) | Test: verify async backend method is awaited, not thread-dispatched |
| InMemoryBackend behavioral drift | Phase 1 (InMemoryBackend) | Shared parametrized fixture run against all 3 backends with identical inputs |
| Abstraction leak via exception types | Phase 1 (define StorageBackendError) | Test: mock DB failure; assert `StorageBackendError` at Corpulse call site |
| Async pool exhaustion | Phase 3 (AsyncPostgresBackend) | Load test: 20 concurrent async searches; assert zero `TooManyConnectionsError` |
| Backwards compat broken | Phase 2 (SQLiteBackend refactor) | `Corpulse()` no-args test must remain green throughout refactor |

---

## Sources

- psycopg3 BYTEA return type (memoryview): [psycopg3 type adaptation docs](https://www.psycopg.org/psycopg3/docs/basic/adapt.html) (HIGH confidence)
- asyncpg pool design and exhaustion behavior: [asyncpg GitHub](https://github.com/MagicStack/asyncpg), [asyncpg connection pool docs](https://magicstack.github.io/asyncpg/current/api/pool.html) (HIGH confidence)
- psycopg3 pool design and blocking behavior: [psycopg3 pool docs](https://www.psycopg.org/psycopg3/docs/advanced/pool.html) (HIGH confidence)
- Upsert COALESCE column ambiguity in PostgreSQL: direct SQL dialect analysis (HIGH confidence)
- asyncio.to_thread pitfalls with mixed sync/async code: [Python asyncio-dev docs](https://docs.python.org/3/library/asyncio-dev.html), [aiosqlite design notes](https://github.com/omnilib/aiosqlite) (HIGH confidence)
- SQLite WAL mode and PRAGMA in executescript: [SQLite WAL docs](https://www.sqlite.org/wal.html), [Python bug tracker issue 29228](https://bugs.python.org/issue29228) (HIGH confidence)
- NumPy BYTEA storage and shape loss: [psycopg issue #336](https://github.com/psycopg/psycopg/issues/336), [community analysis](https://copyprogramming.com/howto/best-way-to-insert-python-numpy-array-into-postgresql-database) (MEDIUM confidence — verified against psycopg3 docs)
- Repository pattern and exception abstraction: [Architecture Patterns with Python](https://www.cosmicpython.com/book/chapter_02_repository.html) (MEDIUM confidence)
- Direct code inspection: `/Users/arkady/src/corpulse/corpulse/db.py`, `core.py`, `integrations/qdrant.py` (HIGH confidence)

---
*Pitfalls research for: corpulse v1.1 — Pluggable Storage Backends milestone*
*Researched: 2026-04-08*
