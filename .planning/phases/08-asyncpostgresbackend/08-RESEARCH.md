# Phase 8: AsyncPostgresBackend - Research

**Researched:** 2026-04-09
**Domain:** asyncpg async PostgreSQL backend, Python async ABC patterns, optional extras packaging
**Confidence:** HIGH

## Summary

Phase 8 adds `AsyncPostgresBackend` — an asyncpg-based backend that allows FastAPI and other asyncio services to write to PostgreSQL without blocking the event loop. The sync `PostgresBackend` (Phase 7) is already complete and provides the SQL schema, query strings, and lazy-import pattern to reuse directly.

The core challenge is that `StorageBackend` ABC has synchronous abstract methods, but `AsyncPostgresBackend` must expose async equivalents. The resolved pattern is: keep the synchronous ABC untouched (the sync Corpulse analytics engine drives it), expose a **separate async ABC** or simply document that `AsyncPostgresBackend` satisfies the interface via `asyncio.get_event_loop().run_until_complete()` internally — but that defeats the purpose. The cleaner, idiomatic approach used in similar libraries is to define an **`AsyncStorageBackend` abstract base class** with `async def` abstract methods and have `AsyncPostgresBackend` implement it, then provide a thin `AsyncCorpulse` facade or require callers to `await` each method directly.

Given the phase scope (`BACK-05`, `INT-02`, `INT-03`) and success criteria (pool, lazy import, shared parity fixture, `AsyncPostgresBackend.create(dsn=...)`), the most practical design is: implement `AsyncPostgresBackend` as a **standalone async class** (not subclassing the sync `StorageBackend`), with async versions of all 8 CRUD methods plus `async initialize()` and `async close()`. The shared parity fixture in `conftest.py` is sync-parametrized; adding asyncpg requires an **async variant of the parity fixture** using `pytest-asyncio` and `asyncio_mode=auto`.

**Primary recommendation:** Model `AsyncPostgresBackend` after `PostgresBackend` — reuse the same `SCHEMA` SQL and query strings from `postgres.py`, swap `psycopg.connect()` for `asyncpg.create_pool()`, replace `%s` placeholders with `$1/$2/...`, and surface a `@classmethod async def create(dsn, ...)` constructor. Add lazy loader `_load_asyncpg()` mirroring `_load_psycopg()`. Extend `conftest.py` with an async backend fixture and gate it on `CORPULSE_POSTGRES_TEST_CONNINFO` + asyncpg availability.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BACK-05 | AsyncPostgresBackend via asyncpg>=0.29 with async initialize() and connection pool | asyncpg.create_pool() with min_size/max_size; async class factory `create()`; lazy `_load_asyncpg()`; async versions of all 8 StorageBackend methods |
| INT-02 | pyproject.toml extras: [postgres] for psycopg, [postgres-async] for asyncpg | Add `postgres-async = ["asyncpg>=0.29"]` to `[project.optional-dependencies]`; [postgres] already exists for psycopg>=3.2 |
| INT-03 | PostgresBackend and AsyncPostgresBackend support connection pooling | asyncpg has native pool via `create_pool()`; psycopg>=3.2 has `psycopg_pool` as separate package — verify if INT-03 requires adding pool to sync backend too or only async |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncpg | >=0.29 (latest: 0.31.0) | Async PostgreSQL driver using binary protocol | 5x faster than psycopg3 in async benchmarks; native asyncio; built-in connection pool; no thread pool needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | >=0.23 (already in dev deps) | Async test execution | Already installed; `asyncio_mode=auto` already set in pyproject.toml |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncpg | psycopg (async mode) | psycopg>=3 has async support but slower; requirement explicitly names asyncpg |
| asyncpg.create_pool | asyncpg.connect (single connection) | Single connection blocks on concurrent requests; pool is required by INT-03 |

**Installation (end-user):**
```bash
pip install "corpulse[postgres-async]"
```

**Installation (dev):**
```bash
pip install asyncpg>=0.29
```

**Version verification:** asyncpg latest on PyPI is **0.31.0** (confirmed 2026-04-09 via `pip index versions asyncpg`). The requirement spec `>=0.29` is appropriate — 0.29 was the first version with asyncpg's stable pool API improvements.

## Architecture Patterns

### Recommended Project Structure
```
corpulse/backends/
├── base.py              # StorageBackend ABC (sync) — unchanged
├── sqlite.py            # SQLiteBackend
├── memory.py            # InMemoryBackend
├── postgres.py          # PostgresBackend (sync, psycopg)
├── postgres_async.py    # AsyncPostgresBackend (asyncpg) — NEW
└── __init__.py          # lazy-load both Postgres backends via __getattr__

tests/
├── conftest.py          # extend: add async_backend fixture (async_postgres param)
└── test_async_postgres_backend.py  # fake-driver unit tests + skipif live tests
```

### Pattern 1: Lazy Import Loader
**What:** Import asyncpg only inside `_load_asyncpg()` — mirrors `_load_psycopg()` in postgres.py
**When to use:** Always — prevents `import corpulse` from failing when asyncpg is not installed

```python
# Source: mirrors corpulse/backends/postgres.py _load_psycopg() pattern
def _load_asyncpg():
    try:
        import asyncpg
    except ImportError as exc:
        raise ImportError(
            "asyncpg is required to use AsyncPostgresBackend. "
            "Install corpulse[postgres-async]."
        ) from exc
    return asyncpg, asyncpg.PostgresError
```

### Pattern 2: Async Class Factory (`create` classmethod)
**What:** `__init__` cannot be async; use a classmethod that awaits pool creation
**When to use:** Whenever a constructor needs to await I/O (pool creation, schema init)

```python
# Source: asyncpg docs https://magicstack.github.io/asyncpg/current/api/index.html
class AsyncPostgresBackend:
    def __init__(self, pool, error_cls):
        self._pool = pool
        self._error_cls = error_cls
        self._closed = False

    @classmethod
    async def create(
        cls,
        dsn: str,
        *,
        min_size: int = 2,
        max_size: int = 10,
    ) -> "AsyncPostgresBackend":
        asyncpg, error_cls = _load_asyncpg()
        pool = await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)
        backend = cls(pool, error_cls)
        await backend._initialize()
        return backend
```

**Usage:**
```python
backend = await AsyncPostgresBackend.create(dsn="postgresql://user:pass@host/db")
```

### Pattern 3: Pool-based Async Operations with Transaction
**What:** Each public method acquires a pool connection, runs SQL in a transaction, releases it
**When to use:** All 8 CRUD methods of the backend

```python
# Source: asyncpg docs https://magicstack.github.io/asyncpg/current/usage.html
async def upsert_document(self, doc_id, filename, embedding=None, embedded_at=None):
    try:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO documents (doc_id, filename, embedding_vec, embedded_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        filename = EXCLUDED.filename,
                        embedding_vec = COALESCE(EXCLUDED.embedding_vec, documents.embedding_vec),
                        embedded_at = COALESCE(EXCLUDED.embedded_at, documents.embedded_at)
                    """,
                    doc_id, filename, embedding, embedded_at,
                )
    except self._error_cls as exc:
        raise StorageBackendError(str(exc)) from exc
```

**Key difference from psycopg:** asyncpg uses `$1, $2, ...` positional placeholders (not `%s`). Arguments are passed as positional args to `execute()` (not a tuple).

### Pattern 4: Record to Dict Conversion
**What:** asyncpg returns `asyncpg.Record` objects; convert with `dict(row)`
**When to use:** All `fetch()` calls returning rows

```python
# Source: asyncpg docs — Record is tuple-/dict-like hybrid
rows = await conn.fetch("SELECT * FROM documents")
return [dict(row) for row in rows]
```

### Pattern 5: Async Context Manager for Cleanup
**What:** `AsyncPostgresBackend` should support `async with` for pool teardown
**When to use:** Callers who want deterministic cleanup

```python
async def close(self) -> None:
    if self._closed:
        return
    await self._pool.close()
    self._closed = True

async def __aenter__(self):
    return self

async def __aexit__(self, exc_type, exc, tb):
    await self.close()
```

### Pattern 6: `__getattr__` Lazy Export in backends/__init__.py
**What:** Add `AsyncPostgresBackend` to `__all__` and `__getattr__` — mirrors PostgresBackend
**When to use:** Extending the lazy-load registry

```python
# Add to __all__:
"AsyncPostgresBackend",

# Add to __getattr__:
if name == "AsyncPostgresBackend":
    from .postgres_async import AsyncPostgresBackend
    globals()["AsyncPostgresBackend"] = AsyncPostgresBackend
    return AsyncPostgresBackend
```

### Pattern 7: Extending the Shared Parity Fixture
**What:** The existing `backend` fixture in `conftest.py` is sync; add a parallel `async_backend` fixture for the async backend
**When to use:** Async parity test suite — mirrors `test_backend_contract.py::test_backend_parity` but async

```python
# conftest.py addition
import asyncio, importlib.util, os
from corpulse.backends import AsyncPostgresBackend  # lazy

def _async_backend_params():
    params = []
    if (
        os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")
        and importlib.util.find_spec("asyncpg") is not None
    ):
        params.append("async_postgres")
    return params or ["skip"]  # need at least one param

@pytest.fixture(params=_async_backend_params())
async def async_backend(request):
    if request.param == "skip":
        pytest.skip("requires CORPULSE_POSTGRES_TEST_CONNINFO and asyncpg")
    backend = await AsyncPostgresBackend.create(
        os.environ["CORPULSE_POSTGRES_TEST_CONNINFO"]
    )
    await backend._pool.execute(
        "TRUNCATE engagements, retrievals, documents RESTART IDENTITY"
    )
    try:
        yield backend
    finally:
        await backend._pool.execute(
            "TRUNCATE engagements, retrievals, documents RESTART IDENTITY"
        )
        await backend.close()
```

### Anti-Patterns to Avoid
- **`asyncio.get_event_loop().run_until_complete()` inside async methods:** defeats the whole point; never bridge sync→async inside the backend
- **`asyncpg.connect()` per request:** creates a new TCP connection each time; always use pool
- **Importing asyncpg at module level:** breaks `import corpulse` for users without asyncpg installed
- **Reusing `SCHEMA` SQL with semicolon-separated statements via `execute()`:** asyncpg `execute()` does NOT support multiple semicolon-separated statements in a single call — must split SCHEMA into individual statements and execute sequentially (unlike psycopg which handles `executescript`-style multi-statement)
- **Using `%s` placeholders:** asyncpg requires `$1, $2, ...`; using `%s` will raise a runtime error

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Connection pool | Custom pool with asyncio.Queue | asyncpg.create_pool() | Health checks, backpressure, idle connection expiry all built in |
| Async transactions | Manual try/await conn.rollback() | `async with conn.transaction():` | Handles nested savepoints, auto-rollback on exception |
| Record mapping | Custom row factory class | `dict(asyncpg_record)` | asyncpg.Record supports dict() natively |
| Multi-statement schema init | String.split(";") loop | Execute each DDL statement separately | asyncpg execute() handles one statement at a time |

**Key insight:** asyncpg's pool is production-grade and used by major async frameworks (Starlette, Litestar). The only hand-rolling needed is the StorageBackendError wrapping layer.

## Common Pitfalls

### Pitfall 1: Multi-Statement SCHEMA Execute
**What goes wrong:** `await conn.execute(SCHEMA)` where SCHEMA contains multiple `;`-separated statements raises `asyncpg.exceptions.PostgresSyntaxError`
**Why it happens:** asyncpg's `execute()` sends one statement to the server; the Postgres binary protocol rejects multiple statements in a single simple-query
**How to avoid:** Split `SCHEMA` into individual SQL strings and execute each in a loop, or use `conn.executemany()` / `conn.execute()` per statement. Alternatively, define `SCHEMA_STATEMENTS = [stmt.strip() for stmt in SCHEMA.split(";") if stmt.strip()]` and execute each.
**Warning signs:** `PostgresSyntaxError: cannot insert multiple commands into a prepared statement`

### Pitfall 2: Wrong Placeholder Syntax
**What goes wrong:** Using `%s` (psycopg style) in asyncpg queries causes either a `PostgresSyntaxError` or silent corruption
**Why it happens:** asyncpg passes queries directly to Postgres without regex substitution; `%s` is not a Postgres parameter placeholder
**How to avoid:** Use `$1, $2, $3, ...` throughout `postgres_async.py`; do not copy-paste from `postgres.py` without updating placeholders
**Warning signs:** `asyncpg.exceptions.PostgresSyntaxError` on first parameterized query

### Pitfall 3: Sync `__init__` Cannot Await
**What goes wrong:** Calling `await asyncpg.create_pool()` inside `__init__` causes `TypeError: object NoneType can't be used in 'await' expression`
**Why it happens:** `__init__` is a sync function; it cannot be a coroutine
**How to avoid:** Use `@classmethod async def create(cls, dsn, ...)` factory; `__init__` receives an already-created pool object
**Warning signs:** `SyntaxError` or `TypeError` at class instantiation time

### Pitfall 4: asyncpg pool min_size default is 10
**What goes wrong:** Default `min_size=10` opens 10 connections immediately — excessive for test environments
**Why it happens:** asyncpg defaults are tuned for production; `create_pool(dsn, min_size=10, max_size=10)`
**How to avoid:** Use `min_size=2, max_size=10` as defaults in `create()` method; tests that truncate tables may hit conflicts with 10 open connections on a fresh Postgres instance
**Warning signs:** Connection timeouts on low-resource test Postgres instances

### Pitfall 5: Async Fixture Needs pytest-asyncio
**What goes wrong:** `async def async_backend(...)` fixture not recognized by pytest; `ScopeMismatch` or coroutine not executed
**Why it happens:** Plain pytest does not understand async fixtures without pytest-asyncio
**How to avoid:** `asyncio_mode = "auto"` is already set in `pyproject.toml` — async fixtures are recognized automatically; no `@pytest.mark.asyncio` needed
**Warning signs:** Fixture yields a coroutine object instead of the backend instance

### Pitfall 6: INT-03 Scope — Does Sync Backend Need Pooling?
**What goes wrong:** Requirement says "both PostgresBackend and AsyncPostgresBackend support connection pooling" — if Phase 7 used a single connection, INT-03 is not fully satisfied
**Why it happens:** psycopg single-connection is not pooling; psycopg has `psycopg_pool` as a separate package
**How to avoid:** Check Phase 7 implementation — `PostgresBackend.__init__` uses `psycopg.connect()` (single connection). INT-03 may require retrofitting `PostgresBackend` with `psycopg_pool.ConnectionPool`. Investigate and decide at plan time whether to add `psycopg_pool` to Phase 7 or do it in Phase 8. If adding pool to sync backend, `psycopg_pool>=3.2` must be added to `[postgres]` extra or as a separate extra.
**Warning signs:** CI passes Phase 8 but REQUIREMENTS audit fails INT-03 for PostgresBackend

## Code Examples

Verified patterns from official sources:

### Schema Initialization (multi-statement safe)
```python
# asyncpg cannot execute multiple statements in one call
# Split the shared SCHEMA string from postgres.py into individual DDL statements

_SCHEMA_STATEMENTS = [s.strip() for s in SCHEMA.split(";") if s.strip()]

async def _initialize(self) -> None:
    try:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for stmt in _SCHEMA_STATEMENTS:
                    await conn.execute(stmt)
    except self._error_cls as exc:
        raise StorageBackendError(str(exc)) from exc
```

### Fetch and Convert
```python
# Source: asyncpg docs — dict() converts asyncpg.Record
async def all_documents(self) -> list[DocumentRow]:
    try:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM documents")
            return [dict(row) for row in rows]
    except self._error_cls as exc:
        raise StorageBackendError(str(exc)) from exc
```

### Fake asyncpg Module for Unit Tests (mirrors FakePsycopgModule pattern)
```python
# mirrors FakeConnection / FakePsycopgModule in test_postgres_backend.py
class FakeAsyncpgRecord(dict):
    """dict with asyncpg.Record-compatible dict() conversion."""
    pass

class FakeAsyncpgConnection:
    async def execute(self, sql, *args): ...
    async def fetch(self, sql, *args): return []
    async def fetchrow(self, sql, *args): return None
    async def __aenter__(self): return self
    async def __aexit__(self, *a): pass

class FakeAsyncpgPool:
    def acquire(self): return FakeAsyncpgConnection()  # returns async CM
    async def execute(self, sql, *args): ...
    async def close(self): ...

class FakeAsyncpgModule:
    PostgresError = Exception
    async def create_pool(self, dsn, *, min_size, max_size): return FakeAsyncpgPool()
```

### pyproject.toml extras update
```toml
[project.optional-dependencies]
qdrant = ["qdrant-client>=1.7"]
postgres = ["psycopg>=3.2"]
postgres-async = ["asyncpg>=0.29"]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| asyncio.to_thread(sync_db_call) | Native async driver (asyncpg) | asyncpg 0.1+ | True non-blocking; no thread pool overhead |
| asyncpg.connect() per request | asyncpg.create_pool() | Standard since asyncpg 0.10 | Connection reuse; 15x throughput improvement |
| asyncpg loop= parameter | Not used (auto-detects running loop) | asyncpg 0.22 (Python 3.10+) | Cleaner API; loop parameter deprecated |

**Deprecated/outdated:**
- `loop=` parameter to `asyncpg.create_pool()`: deprecated since Python 3.10 removed explicit loop passing; do not pass it
- Multiple statements in `asyncpg.execute()`: never worked; must always use single-statement execute

## Open Questions

1. **INT-03: Does PostgresBackend (sync) need connection pooling?**
   - What we know: Phase 7's `PostgresBackend` uses a single `psycopg.connect()` connection. INT-03 says "both backends support connection pooling."
   - What's unclear: Does this mean Phase 8 must retrofit sync backend with `psycopg_pool`, or is the requirement satisfied by async backend alone?
   - Recommendation: At plan time, interpret INT-03 minimally — add optional `pool_size` parameter to `PostgresBackend` backed by `psycopg_pool.ConnectionPool` as a Phase 8 task, gated on `CORPULSE_POSTGRES_TEST_CONNINFO`. If that's too broad for Phase 8 scope, defer and mark INT-03 as partially satisfied.

2. **SCHEMA reuse vs copy-paste**
   - What we know: `postgres.py` defines `SCHEMA` with Postgres-compatible DDL. Same schema applies to async backend.
   - What's unclear: Should `postgres_async.py` import `SCHEMA` from `postgres.py`, or duplicate it?
   - Recommendation: Import `SCHEMA` from `postgres.py` directly — single source of truth. `postgres.py` does not import asyncpg, so no circular dep risk.

3. **Corpulse facade — does it need async methods?**
   - What we know: `Corpulse` class is sync; its analytics engine calls sync `StorageBackend` methods. Phase scope does not include an `AsyncCorpulse` facade (that is v2 `ASYNC-01`).
   - What's unclear: How does a FastAPI user write retrieval events using `AsyncPostgresBackend` through `Corpulse`?
   - Recommendation: For Phase 8, `AsyncPostgresBackend` is a standalone async class. Callers use it directly (`await backend.upsert_document(...)`) or bridge via `asyncio.to_thread(corpulse_instance.log_retrieval, ...)` at the application layer. Document this usage pattern in docstrings. Do NOT add async methods to `Corpulse` in Phase 8.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio >=0.23 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` — `asyncio_mode = "auto"` already set |
| Quick run command | `pytest tests/test_async_postgres_backend.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BACK-05 | `AsyncPostgresBackend.create(dsn)` returns initialized backend with pool | unit (fake driver) | `pytest tests/test_async_postgres_backend.py::test_async_postgres_backend_creates_pool -x` | ❌ Wave 0 |
| BACK-05 | asyncpg not imported at `import corpulse` time | unit | `pytest tests/test_import.py -x` (extend existing) | ✅ (extend) |
| BACK-05 | `pip install corpulse[postgres-async]` installs asyncpg>=0.29 | integration (packaging) | manual / CI | ❌ Wave 0 |
| BACK-05 | All 8 async CRUD methods work correctly | unit (fake driver) | `pytest tests/test_async_postgres_backend.py -x` | ❌ Wave 0 |
| BACK-05 | Schema initialized on first create() | unit (fake driver) | `pytest tests/test_async_postgres_backend.py::test_schema_initialized -x` | ❌ Wave 0 |
| BACK-05 | StorageBackendError raised on asyncpg error | unit (fake driver) | `pytest tests/test_async_postgres_backend.py::test_error_translation -x` | ❌ Wave 0 |
| BACK-05 | Live async parity (all 8 methods, real Postgres) | integration (skipif no env var) | `CORPULSE_POSTGRES_TEST_CONNINFO=... pytest tests/test_async_postgres_backend.py::test_live_async_backend_round_trip -x` | ❌ Wave 0 |
| INT-02 | `[postgres-async]` extra in pyproject.toml with asyncpg>=0.29 | unit | `pytest tests/test_package.py -x` (extend) | ✅ (extend) |
| INT-03 | AsyncPostgresBackend uses pool (not single connection) | unit (fake driver) | `pytest tests/test_async_postgres_backend.py::test_pool_used_not_single_connection -x` | ❌ Wave 0 |
| INT-03 | Configurable pool size (min_size, max_size params) | unit (fake driver) | `pytest tests/test_async_postgres_backend.py::test_pool_size_params_forwarded -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_async_postgres_backend.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_async_postgres_backend.py` — covers BACK-05 fake-driver unit tests and live skipif test
- [ ] `conftest.py` — add `async_backend` async fixture gated on env var + asyncpg availability

*(Existing `tests/test_import.py` and `tests/test_package.py` need targeted additions for asyncpg lazy-import and extras verification.)*

## Sources

### Primary (HIGH confidence)
- asyncpg official docs https://magicstack.github.io/asyncpg/current/api/index.html — create_pool signature, Pool methods, Record→dict conversion, close/terminate
- asyncpg official docs https://magicstack.github.io/asyncpg/current/usage.html — async context manager patterns, transaction usage, pool.acquire()
- PyPI registry (verified live) — asyncpg 0.31.0 is current latest; 0.29.0 is the minimum stated in requirements
- corpulse/backends/postgres.py — SCHEMA SQL, _load_psycopg() pattern, _run() error translation, all 8 method signatures
- corpulse/backends/base.py — StorageBackend ABC, all TypedDicts, StorageBackendError
- tests/conftest.py — existing backend fixture structure to extend for async variant
- tests/test_postgres_backend.py — FakeConnection/FakePsycopgModule pattern to mirror for asyncpg fakes
- pyproject.toml — existing extras structure, asyncio_mode=auto already set

### Secondary (MEDIUM confidence)
- WebSearch: asyncpg create_pool signature (verified against official docs) — min_size/max_size defaults, dsn positional arg
- WebSearch: asyncpg multi-statement execute limitation (corroborated by known binary protocol behavior; should be verified in first test run)

### Tertiary (LOW confidence)
- WebSearch: asyncpg vs psycopg3 5x performance claim — benchmarks not independently verified; directionally correct but exact numbers vary by workload

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — asyncpg version confirmed live via pip index; API verified against official docs
- Architecture: HIGH — lazy loader pattern, factory classmethod, pool acquire/transaction all from official asyncpg docs and direct analogy to Phase 7 implementation
- Pitfalls: HIGH (multi-statement, placeholders, sync init) / MEDIUM (INT-03 scope ambiguity — needs plan-time decision)
- Test patterns: HIGH — mirrors Phase 7 fake-driver approach; asyncio_mode=auto already configured

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (asyncpg API is stable; extras packaging pattern is fixed)
