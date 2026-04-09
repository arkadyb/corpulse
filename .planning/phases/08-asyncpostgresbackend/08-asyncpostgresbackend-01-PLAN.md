---
phase: 08-asyncpostgresbackend
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - corpulse/backends/postgres_async.py
  - corpulse/backends/__init__.py
  - pyproject.toml
  - tests/test_async_postgres_backend.py
  - tests/conftest.py
  - tests/test_import.py
  - tests/test_package.py
autonomous: true
requirements: [BACK-05, INT-02]

must_haves:
  truths:
    - "await AsyncPostgresBackend.create(dsn) returns an initialized backend with a connection pool"
    - "All 8 async CRUD methods work correctly against the pool"
    - "asyncpg is NOT imported when running import corpulse or import corpulse.backends"
    - "pip install corpulse[postgres-async] installs asyncpg>=0.29"
    - "StorageBackendError is raised when asyncpg raises PostgresError"
    - "AsyncPostgresBackend supports async with for deterministic cleanup"
    - "Pool size is configurable via min_size and max_size parameters"
    - "The shared parametrized async test fixture passes for AsyncPostgresBackend"
  artifacts:
    - path: "corpulse/backends/postgres_async.py"
      provides: "AsyncPostgresBackend class with all 8 async CRUD methods, create() factory, close(), async context manager"
      min_lines: 120
    - path: "tests/test_async_postgres_backend.py"
      provides: "Fake-driver unit tests and env-gated live parity test"
      min_lines: 100
    - path: "tests/conftest.py"
      provides: "async_backend fixture for shared parametrized async parity"
  key_links:
    - from: "corpulse/backends/postgres_async.py"
      to: "corpulse/backends/postgres.py"
      via: "imports SCHEMA constant"
      pattern: "from .postgres import SCHEMA"
    - from: "corpulse/backends/__init__.py"
      to: "corpulse/backends/postgres_async.py"
      via: "lazy __getattr__ export"
      pattern: "AsyncPostgresBackend"
    - from: "pyproject.toml"
      to: "asyncpg"
      via: "optional dependency extra"
      pattern: 'postgres-async.*asyncpg'
    - from: "tests/conftest.py"
      to: "corpulse/backends/postgres_async.py"
      via: "async_backend fixture creates AsyncPostgresBackend"
      pattern: "AsyncPostgresBackend.create"
---

<objective>
Implement AsyncPostgresBackend with asyncpg, add the [postgres-async] optional extra, write deterministic fake-driver tests (written BEFORE implementation), and add async_backend fixture for shared parity coverage.

Purpose: Allow async services (FastAPI, etc.) to use corpulse with PostgreSQL without blocking the event loop.
Output: Working async backend, package extra, full test coverage, async parity fixture.
</objective>

<execution_context>
@/Users/arkady/.claude/get-shit-done/workflows/execute-plan.md
@/Users/arkady/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/08-asyncpostgresbackend/08-RESEARCH.md
@.planning/phases/07-postgresbackend-sync/07-postgresbackend-sync-01-SUMMARY.md

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From corpulse/backends/base.py:
```python
class DocumentRow(TypedDict):
    doc_id: str
    filename: str
    embedding_vec: bytes | None
    embedded_at: float | None
    source_updated_at: float | None

class RetrievalRow(TypedDict):
    doc_id: str
    cnt: int
    avg_rank: float | None
    avg_score: float | None

class EngagementRow(TypedDict):
    doc_id: str
    cnt: int

class EmbeddingRow(TypedDict):
    doc_id: str
    filename: str
    embedding_vec: bytes

class StorageBackendError(RuntimeError): ...

class StorageBackend(ABC):
    # 8 abstract methods + close() + __enter__/__exit__
    def upsert_document(self, doc_id, filename, embedding=None, embedded_at=None) -> None
    def insert_retrieval(self, doc_id, query_hash, rank, score, retrieved_at) -> None
    def insert_engagement(self, doc_id, event_type, engaged_at) -> None
    def update_source_timestamp(self, doc_id, updated_at) -> None
    def all_documents(self) -> list[DocumentRow]
    def retrieval_counts(self, since) -> list[RetrievalRow]
    def engagement_counts(self, since) -> list[EngagementRow]
    def all_embeddings(self) -> list[EmbeddingRow]
    def close(self) -> None
```

From corpulse/backends/postgres.py:
```python
SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY, filename TEXT,
    embedding_vec BYTEA, embedded_at DOUBLE PRECISION,
    source_updated_at DOUBLE PRECISION DEFAULT NULL
);
CREATE TABLE IF NOT EXISTS retrievals (
    id BIGSERIAL PRIMARY KEY, doc_id TEXT NOT NULL,
    query_hash TEXT NOT NULL, rank INTEGER,
    score DOUBLE PRECISION, retrieved_at DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS engagements (
    id BIGSERIAL PRIMARY KEY, doc_id TEXT NOT NULL,
    event_type TEXT NOT NULL, engaged_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_retrievals_doc ON retrievals(doc_id);
CREATE INDEX IF NOT EXISTS idx_retrievals_time ON retrievals(retrieved_at);
CREATE INDEX IF NOT EXISTS idx_engagements_doc ON engagements(doc_id);
"""

def _load_psycopg() -> tuple[Any, Any, type[BaseException]]: ...
class PostgresBackend(StorageBackend): ...
```

From corpulse/backends/__init__.py:
```python
__all__ = [
    "DocumentRow", "EmbeddingRow", "EngagementRow", "RetrievalRow",
    "StorageBackend", "StorageBackendError",
    "InMemoryBackend", "PostgresBackend", "SQLiteBackend",
]

def __getattr__(name: str):
    if name == "PostgresBackend":
        from .postgres import PostgresBackend
        globals()["PostgresBackend"] = PostgresBackend
        return PostgresBackend
    raise AttributeError(...)
```

From pyproject.toml:
```toml
[project.optional-dependencies]
qdrant = ["qdrant-client>=1.7"]
postgres = ["psycopg>=3.2"]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]
```

From tests/conftest.py:
```python
def _backend_params() -> list[str]:
    params = ["sqlite", "memory"]
    if (
        os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")
        and importlib.util.find_spec("psycopg") is not None
    ):
        params.append("postgres")
    return params

@pytest.fixture(params=_backend_params())
def backend(request, tmp_path):
    # yields sqlite, memory, or postgres backend instances
    ...
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write fake-driver tests and packaging assertions (tests first)</name>
  <files>tests/test_async_postgres_backend.py, tests/test_import.py, tests/test_package.py</files>
  <read_first>
    - tests/test_postgres_backend.py (fake-driver pattern to mirror: FakeConnection, FakePsycopgModule, monkeypatch of _load_psycopg)
    - tests/test_import.py (existing lazy-import smoke tests to extend)
    - tests/test_package.py (existing extra-declaration tests to extend)
    - corpulse/backends/base.py (StorageBackendError for import in tests)
    - corpulse/backends/postgres.py (SCHEMA constant shape — needed to understand how _SCHEMA_STATEMENTS split works)
  </read_first>
  <action>
    **1. Create `tests/test_async_postgres_backend.py`:**

    Build fake asyncpg objects mirroring the FakeConnection/FakePsycopgModule pattern from test_postgres_backend.py:

    ```python
    class FakeAsyncpgError(Exception):
        pass

    class FakeAsyncpgRecord(dict):
        """dict subclass — asyncpg.Record supports dict() natively."""
        pass

    class FakeAsyncpgConnection:
        def __init__(self):
            self.calls = []
            self.rows = {}
            self.error = None

        async def execute(self, sql, *args):
            normalized = _normalize_sql(sql)
            self.calls.append((normalized, args))
            if self.error is not None:
                raise self.error

        async def fetch(self, sql, *args):
            normalized = _normalize_sql(sql)
            self.calls.append((normalized, args))
            if self.error is not None:
                raise self.error
            return self.rows.get(normalized, [])

        def transaction(self):
            return _FakeTransaction()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

    class _FakeTransaction:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            pass

    class _FakeAcquire:
        def __init__(self, conn):
            self._conn = conn
        async def __aenter__(self):
            return self._conn
        async def __aexit__(self, *a):
            pass

    class FakeAsyncpgPool:
        def __init__(self, conn=None):
            self.conn = conn or FakeAsyncpgConnection()
            self.closed = False
            self.create_pool_kwargs = {}

        def acquire(self):
            return _FakeAcquire(self.conn)

        async def close(self):
            self.closed = True

    class FakeAsyncpgModule:
        PostgresError = FakeAsyncpgError

        def __init__(self, pool=None):
            self.pool = pool or FakeAsyncpgPool()
            self.create_pool_calls = []

        async def create_pool(self, dsn, *, min_size, max_size):
            self.create_pool_calls.append({"dsn": dsn, "min_size": min_size, "max_size": max_size})
            self.pool.create_pool_kwargs = {"dsn": dsn, "min_size": min_size, "max_size": max_size}
            return self.pool
    ```

    Use `_normalize_sql(sql)` helper (same as in test_postgres_backend.py): `return " ".join(sql.split())`

    Write tests using monkeypatch to replace `_load_asyncpg`:
    ```python
    monkeypatch.setattr(
        "corpulse.backends.postgres_async._load_asyncpg",
        lambda: (fake_module, FakeAsyncpgError),
    )
    ```

    Then call `await AsyncPostgresBackend.create("postgresql://test")` and assert on fake_module.create_pool_calls, conn.calls, etc.

    Tests to write (all async, no @pytest.mark.asyncio needed due to asyncio_mode=auto):

    - `test_async_postgres_backend_requires_asyncpg`: monkeypatch _load_asyncpg to raise ImportError, verify ImportError with "corpulse[postgres-async]" in message
    - `test_async_postgres_backend_creates_pool`: verify create_pool called with dsn, min_size=2, max_size=10
    - `test_async_postgres_backend_custom_pool_size`: create(dsn, min_size=5, max_size=20), verify forwarded
    - `test_async_postgres_backend_initializes_schema`: verify conn.calls contain CREATE TABLE statements after create()
    - `test_async_postgres_backend_upsert_document`: call upsert_document("d1", "f1.md", b"vec", 1.0), verify conn.calls contains ON CONFLICT SQL with args ("d1", "f1.md", b"vec", 1.0)
    - `test_async_postgres_backend_insert_retrieval`: call insert_retrieval("d1", "h", 1, 0.9, 25.0), verify 5-arg execute
    - `test_async_postgres_backend_insert_engagement`: call insert_engagement("d1", "opened", 30.0), verify 3-arg execute
    - `test_async_postgres_backend_update_source_timestamp`: call update_source_timestamp("d1", 40.0), verify 2-arg execute with (40.0, "d1") order
    - `test_async_postgres_backend_all_documents`: pre-populate conn.rows with fake SELECT * result, verify returns list of dicts
    - `test_async_postgres_backend_retrieval_counts`: pre-populate conn.rows, verify returns aggregated list
    - `test_async_postgres_backend_engagement_counts`: pre-populate conn.rows, verify returns aggregated list
    - `test_async_postgres_backend_all_embeddings`: pre-populate conn.rows, verify returns list
    - `test_async_postgres_backend_translates_driver_errors`: set conn.error = FakeAsyncpgError("boom"), call all_documents(), verify StorageBackendError with __cause__
    - `test_async_postgres_backend_close_idempotent`: call close() twice, verify pool.closed is True, no error on second call
    - `test_async_postgres_backend_async_context_manager`: use `async with backend:`, verify pool.closed after exit
    - `test_async_postgres_backend_uses_pool_acquire`: verify all CRUD methods go through pool.acquire (check conn.calls populated after each method)

    Add env-gated live test:
    ```python
    @pytest.mark.skipif(
        not os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")
        or importlib.util.find_spec("asyncpg") is None,
        reason="requires CORPULSE_POSTGRES_TEST_CONNINFO and asyncpg",
    )
    async def test_live_async_postgres_backend_round_trip():
        from corpulse.backends import AsyncPostgresBackend as LiveBackend

        backend = await LiveBackend.create(os.environ["CORPULSE_POSTGRES_TEST_CONNINFO"])
        try:
            async with backend._pool.acquire() as conn:
                await conn.execute("TRUNCATE engagements, retrievals, documents RESTART IDENTITY")

            await backend.upsert_document("doc-1", "doc-1.md", embedding=b"vec", embedded_at=12.5)
            await backend.insert_retrieval("doc-1", "hash", 1, 0.9, 25.0)
            await backend.insert_engagement("doc-1", "opened", 30.0)
            await backend.update_source_timestamp("doc-1", 40.0)

            assert await backend.all_documents() == ... # same shape as sync test
            # (full assertions for all 4 read methods)
        finally:
            async with backend._pool.acquire() as conn:
                await conn.execute("TRUNCATE engagements, retrievals, documents RESTART IDENTITY")
            await backend.close()
    ```

    **IMPORTANT:** The tests import `AsyncPostgresBackend` from `corpulse.backends.postgres_async`. At the time this task runs, the module does NOT exist yet. All tests that use monkeypatch to replace `_load_asyncpg` should still import the class. Since the module doesn't exist, the tests WILL FAIL (red phase). This is expected — Task 2 makes them green.

    To avoid ImportError at collection time before the module exists, guard the import:
    ```python
    import pytest
    pytestmark = pytest.mark.skipif(
        not hasattr(__import__("corpulse.backends", fromlist=["postgres_async"]), "postgres_async"),
        reason="AsyncPostgresBackend not yet implemented — tests will pass after Task 2"
    )
    ```

    Alternatively, use a try/except at module level that marks all tests as xfail if the import fails. The executor should choose the simplest approach that lets `pytest tests/ -q` not error out before Task 2 is complete. The cleanest pattern: put all async backend tests behind a module-level import guard that skips if the module doesn't exist yet, so the test file can be committed first.

    **2. Extend `tests/test_import.py`:**

    Add two tests:
    ```python
    def test_import_backends_does_not_eagerly_load_asyncpg():
        sys.modules.pop("asyncpg", None)
        import corpulse.backends as backends
        importlib.reload(backends)
        assert hasattr(backends, "SQLiteBackend")
        assert "asyncpg" not in sys.modules

    def test_async_postgres_backend_lazy_export_does_not_import_asyncpg():
        sys.modules.pop("asyncpg", None)
        import corpulse.backends as backends
        importlib.reload(backends)
        async_pg_backend = backends.AsyncPostgresBackend
        assert async_pg_backend.__name__ == "AsyncPostgresBackend"
        assert "asyncpg" not in sys.modules
    ```

    Note: The lazy-export test (`test_async_postgres_backend_lazy_export_does_not_import_asyncpg`) will fail until Task 2 adds `AsyncPostgresBackend` to `__init__.py`. Guard with a skip if the attribute doesn't exist yet.

    **3. Extend `tests/test_package.py`:**

    Add one test:
    ```python
    def test_postgres_async_extra_declared():
        """INT-02: Optional [postgres-async] extra declares asyncpg."""
        pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        assert 'postgres-async' in content and 'asyncpg' in content, "Missing asyncpg postgres-async extra"
    ```

    This test will fail until Task 2 adds the extra to pyproject.toml (red phase).
  </action>
  <verify>
    <automated>python -c "import ast; ast.parse(open('tests/test_async_postgres_backend.py').read()); print('syntax OK')" && grep -c "async def test_" tests/test_async_postgres_backend.py</automated>
  </verify>
  <done>Test file exists with 16+ async test functions and fake driver infrastructure. Packaging tests extended. Tests are expected to fail (red) until Task 2 implements the backend.</done>
</task>

<task type="auto">
  <name>Task 2: Implement AsyncPostgresBackend, lazy export, and [postgres-async] extra</name>
  <files>corpulse/backends/postgres_async.py, corpulse/backends/__init__.py, pyproject.toml</files>
  <read_first>
    - corpulse/backends/postgres.py (source of SCHEMA, _load_psycopg pattern to mirror, all 8 method SQL queries)
    - corpulse/backends/base.py (StorageBackend ABC, TypedDict return types, StorageBackendError)
    - corpulse/backends/__init__.py (lazy __getattr__ export pattern, __all__ list)
    - pyproject.toml (existing optional-dependencies section)
    - tests/test_async_postgres_backend.py (the tests written in Task 1 — understand what the fakes expect)
  </read_first>
  <action>
    **1. Create `corpulse/backends/postgres_async.py`:**

    Add `from __future__ import annotations` at top.

    Import from `.base`: `DocumentRow`, `EmbeddingRow`, `EngagementRow`, `RetrievalRow`, `StorageBackendError`.
    Import from `.postgres`: `SCHEMA` (single source of truth for DDL).

    Define `_load_asyncpg()`:
    ```python
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

    Define `_SCHEMA_STATEMENTS`:
    ```python
    _SCHEMA_STATEMENTS = [s.strip() for s in SCHEMA.split(";") if s.strip()]
    ```

    Define `AsyncPostgresBackend` class (NOT subclassing StorageBackend since ABC has sync methods):
    ```python
    class AsyncPostgresBackend:
        def __init__(self, pool, error_cls):
            self._pool = pool
            self._error_cls = error_cls
            self._closed = False

        @classmethod
        async def create(cls, dsn: str, *, min_size: int = 2, max_size: int = 10) -> AsyncPostgresBackend:
            asyncpg, error_cls = _load_asyncpg()
            pool = await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)
            backend = cls(pool, error_cls)
            await backend._initialize()
            return backend
    ```

    Implement `_initialize()` — execute each statement from `_SCHEMA_STATEMENTS` individually inside a transaction:
    ```python
    async def _initialize(self) -> None:
        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    for stmt in _SCHEMA_STATEMENTS:
                        await conn.execute(stmt)
        except self._error_cls as exc:
            raise StorageBackendError(str(exc)) from exc
    ```

    Implement all 8 CRUD methods. Each method follows this pattern:
    - `async with self._pool.acquire() as conn:` / `async with conn.transaction():` / `await conn.execute(...)`
    - Wrap the body in `try:` / `except self._error_cls as exc:` / `raise StorageBackendError(str(exc)) from exc`
    - Use `$1, $2, ...` positional placeholders (NOT `%s`)
    - Pass parameters as positional args to `execute()`/`fetch()` (NOT as tuple)

    SQL for each method (converted from postgres.py %s to $N):

    `upsert_document(doc_id, filename, embedding=None, embedded_at=None)`:
    ```sql
    INSERT INTO documents (doc_id, filename, embedding_vec, embedded_at)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (doc_id) DO UPDATE SET
        filename = EXCLUDED.filename,
        embedding_vec = COALESCE(EXCLUDED.embedding_vec, documents.embedding_vec),
        embedded_at = COALESCE(EXCLUDED.embedded_at, documents.embedded_at)
    ```
    Call: `await conn.execute(sql, doc_id, filename, embedding, embedded_at)`

    `insert_retrieval(doc_id, query_hash, rank, score, retrieved_at)`:
    ```sql
    INSERT INTO retrievals (doc_id, query_hash, rank, score, retrieved_at)
    VALUES ($1, $2, $3, $4, $5)
    ```
    Call: `await conn.execute(sql, doc_id, query_hash, rank, score, retrieved_at)`

    `insert_engagement(doc_id, event_type, engaged_at)`:
    ```sql
    INSERT INTO engagements (doc_id, event_type, engaged_at)
    VALUES ($1, $2, $3)
    ```
    Call: `await conn.execute(sql, doc_id, event_type, engaged_at)`

    `update_source_timestamp(doc_id, updated_at)`:
    ```sql
    UPDATE documents SET source_updated_at = $1 WHERE doc_id = $2
    ```
    Call: `await conn.execute(sql, updated_at, doc_id)`

    `all_documents()` -> `list[DocumentRow]`:
    ```python
    rows = await conn.fetch("SELECT * FROM documents")
    return [dict(row) for row in rows]
    ```

    `retrieval_counts(since)` -> `list[RetrievalRow]`:
    ```sql
    SELECT doc_id, COUNT(*) AS cnt, AVG(rank) AS avg_rank, AVG(score) AS avg_score
    FROM retrievals WHERE retrieved_at >= $1 GROUP BY doc_id
    ```
    Call: `await conn.fetch(sql, since)`

    `engagement_counts(since)` -> `list[EngagementRow]`:
    ```sql
    SELECT doc_id, COUNT(*) AS cnt FROM engagements WHERE engaged_at >= $1 GROUP BY doc_id
    ```
    Call: `await conn.fetch(sql, since)`

    `all_embeddings()` -> `list[EmbeddingRow]`:
    ```sql
    SELECT doc_id, filename, embedding_vec FROM documents WHERE embedding_vec IS NOT NULL
    ```

    `close()`:
    ```python
    async def close(self) -> None:
        if self._closed:
            return
        await self._pool.close()
        self._closed = True
    ```

    Async context manager:
    ```python
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
    ```

    **2. Update `corpulse/backends/__init__.py`:**

    Add `"AsyncPostgresBackend"` to the `__all__` list.

    Add a second branch in `__getattr__`:
    ```python
    if name == "AsyncPostgresBackend":
        from .postgres_async import AsyncPostgresBackend
        globals()["AsyncPostgresBackend"] = AsyncPostgresBackend
        return AsyncPostgresBackend
    ```

    **3. Update `pyproject.toml`:**

    Add the `postgres-async` extra to `[project.optional-dependencies]`:
    ```toml
    postgres-async = ["asyncpg>=0.29"]
    ```
  </action>
  <verify>
    <automated>pytest tests/test_async_postgres_backend.py tests/test_import.py tests/test_package.py -q</automated>
  </verify>
  <done>All fake-driver tests pass (green). AsyncPostgresBackend class exists with all 8 async CRUD methods, create() factory, close(), async context manager. Lazy export wired. [postgres-async] extra declared. `pytest tests/ -q` exits 0.</done>
</task>

<task type="auto">
  <name>Task 3: Add async_backend fixture to conftest.py for shared parity</name>
  <files>tests/conftest.py</files>
  <read_first>
    - tests/conftest.py (current fixture structure)
    - tests/test_backend_contract.py (shared parity tests that use the backend fixture — understand the pattern)
    - corpulse/backends/postgres_async.py (the implementation from Task 2)
  </read_first>
  <action>
    Add an `async_backend` fixture to `tests/conftest.py` following the Research Pattern 7, gated on `CORPULSE_POSTGRES_TEST_CONNINFO` + asyncpg availability.

    Add to conftest.py:

    ```python
    def _async_backend_params() -> list[str]:
        params = []
        if (
            os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")
            and importlib.util.find_spec("asyncpg") is not None
        ):
            params.append("async_postgres")
        return params or ["skip"]

    @pytest.fixture(params=_async_backend_params())
    async def async_backend(request):
        if request.param == "skip":
            pytest.skip("requires CORPULSE_POSTGRES_TEST_CONNINFO and asyncpg")
        from corpulse.backends import AsyncPostgresBackend

        backend = await AsyncPostgresBackend.create(
            os.environ["CORPULSE_POSTGRES_TEST_CONNINFO"]
        )
        async with backend._pool.acquire() as conn:
            await conn.execute(
                "TRUNCATE engagements, retrievals, documents RESTART IDENTITY"
            )
        try:
            yield backend
        finally:
            async with backend._pool.acquire() as conn:
                await conn.execute(
                    "TRUNCATE engagements, retrievals, documents RESTART IDENTITY"
                )
            await backend.close()
    ```

    This fixture enables writing shared async parity tests that use `async_backend` the same way sync tests use `backend`. Future test files can parametrize against this fixture to verify async backend contract compliance.

    Verify the full test suite still passes after adding the fixture.
  </action>
  <verify>
    <automated>pytest tests/ -q</automated>
  </verify>
  <done>async_backend fixture exists in conftest.py. It is gated on CORPULSE_POSTGRES_TEST_CONNINFO and asyncpg. Full test suite passes. Roadmap success criterion 3 ("shared parametrized test fixture passes for AsyncPostgresBackend") is addressable via this fixture.</done>
</task>

</tasks>

<verification>
1. `pytest tests/ -q` — full suite green (all existing + new tests pass)
2. `python -c "import corpulse.backends"` succeeds without asyncpg installed
3. `grep 'postgres-async' pyproject.toml` shows the extra declaration
4. `grep 'AsyncPostgresBackend' corpulse/backends/__init__.py` shows lazy export
5. `grep -c 'async def' corpulse/backends/postgres_async.py` shows at least 12 async methods
6. `grep 'async_backend' tests/conftest.py` shows the async fixture
</verification>

<success_criteria>
- AsyncPostgresBackend class with all 8 async CRUD methods, async create() factory, async close(), async context manager
- SCHEMA imported from postgres.py (single source of truth)
- asyncpg lazy-loaded only at instantiation time
- [postgres-async] extra declared in pyproject.toml
- Fake-driver tests written BEFORE implementation (tests-first ordering)
- Fake-driver tests cover all methods, error translation, close idempotency, pool usage
- Env-gated live async parity test wired and skips cleanly
- async_backend fixture in conftest.py for shared parametrized async parity
- Full test suite passes
</success_criteria>

<output>
After completion, create `.planning/phases/08-asyncpostgresbackend/08-asyncpostgresbackend-01-SUMMARY.md`
</output>
