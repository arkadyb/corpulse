# Architecture Research

**Domain:** Pluggable storage backends for a Python analytics library
**Researched:** 2026-04-08
**Confidence:** HIGH (derived from direct codebase inspection)

## Standard Architecture

### System Overview — Current State

```
┌──────────────────────────────────────────────────────────────┐
│                        Public API Layer                       │
│  QdrantCorpulseClient   AsyncQdrantCorpulseClient            │
│         │                        │  (asyncio.to_thread)      │
│         └──────────┬─────────────┘                           │
│               Corpulse facade                                 │
│  log_retrieval / log_engagement / log_source_update          │
│  get_ghosts / get_duplicates / get_stale_embeddings ...      │
├──────────────────────────────────────────────────────────────┤
│                        Persistence Layer                      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  DB (db.py)   -- SQLite-specific, 8 public methods     │  │
│  │  _conn() contextmanager, WAL mode, sqlite3.Row         │  │
│  └────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────┤
│                        Storage                               │
│  ┌────────────────┐                                          │
│  │  SQLite file   │                                          │
│  └────────────────┘                                          │
└──────────────────────────────────────────────────────────────┘
```

### System Overview — Target State

```
┌──────────────────────────────────────────────────────────────┐
│                        Public API Layer                       │
│  QdrantCorpulseClient   AsyncQdrantCorpulseClient            │
│         │                        │  (asyncio.to_thread for   │
│         └──────────┬─────────────┘   sync backends)          │
│               Corpulse facade        -- UNCHANGED             │
│  Corpulse(backend=...)  -- only constructor changes          │
├──────────────────────────────────────────────────────────────┤
│                    StorageBackend ABC                         │
│  8 abstract methods matching current DB interface exactly     │
├──────────────────────────────────────────────────────────────┤
│         Concrete Backend Implementations                      │
│  ┌──────────────┐ ┌──────────────┐ ┌───────────────────────┐│
│  │ SQLiteBackend│ │PostgresBackend│ │   InMemoryBackend     ││
│  │ (refactored) │ │  (psycopg 3) │ │   (dict-based)        ││
│  └──────────────┘ └──────────────┘ └───────────────────────┘│
│                    ┌──────────────┐                           │
│                    │AsyncPostgres │                           │
│                    │  (asyncpg)   │                           │
│                    └──────────────┘                           │
├──────────────────────────────────────────────────────────────┤
│                        Storage                               │
│  ┌───────────┐  ┌────────────────────────┐                   │
│  │SQLite file│  │  PostgreSQL database   │                   │
│  └───────────┘  └────────────────────────┘                   │
└──────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `Corpulse` (core.py) | Public facade, analytics logic, calls only backend methods | Modify constructor only |
| `DB` (db.py) | SQLite persistence, 8 public methods | Becomes thin shim for backwards compat |
| `StorageBackend` (backends/base.py) | ABC defining the 8-method contract | New file |
| `SQLiteBackend` (backends/sqlite.py) | Refactored DB class, implements ABC | New file |
| `PostgresBackend` (backends/postgres.py) | Sync Postgres via psycopg 3 | New file |
| `AsyncPostgresBackend` (backends/postgres.py) | Async Postgres via asyncpg | New file |
| `InMemoryBackend` (backends/memory.py) | Dict-based, no persistence, for tests | New file |
| `QdrantCorpulseClient` (integrations/qdrant.py) | Unchanged -- calls corpulse.log_retrieval() | No change needed |

## Recommended Project Structure

```
corpulse/
├── __init__.py              # expose Corpulse + backend classes
├── core.py                  # Corpulse facade -- constructor change only
├── backends/
│   ├── __init__.py          # re-export all backends + ABC
│   ├── base.py              # StorageBackend ABC + TypedDicts
│   ├── sqlite.py            # SQLiteBackend (DB class body moved here)
│   ├── postgres.py          # PostgresBackend + AsyncPostgresBackend
│   └── memory.py            # InMemoryBackend
├── db.py                    # KEEP as compat shim, imports SQLiteBackend
└── integrations/
    ├── __init__.py
    └── qdrant.py            # unchanged
```

### Structure Rationale

- **backends/ subdirectory:** Groups all implementations under one importable namespace. Mirrors the pattern used by SQLAlchemy dialects and the `databases` library.
- **base.py separate from impls:** ABC can be imported by users writing custom backends without pulling in sqlite3 or psycopg.
- **db.py kept as shim:** Zero-change backwards compatibility path. Can be deprecated and removed in a future milestone cleanup.

## Architectural Patterns

### Pattern 1: Minimal ABC -- Mirror the 8 Existing DB Methods Exactly

**What:** Define `StorageBackend` as an ABC with exactly the 8 methods `DB` already exposes. Do not redesign the interface. Signature-for-signature match. The 8 methods from current db.py are:

```
upsert_document(doc_id, filename, embedding, embedded_at) -> None
insert_retrieval(doc_id, query_hash, rank, score, retrieved_at) -> None
insert_engagement(doc_id, event_type, engaged_at) -> None
update_source_timestamp(doc_id, updated_at) -> None
all_documents() -> list[DocumentRow]
retrieval_counts(since: float) -> list[dict]
engagement_counts(since: float) -> list[dict]
all_embeddings() -> list[dict]
```

**When to use:** Always for this milestone. The ABC is the contract between Corpulse and any backend. The 8 methods are fully sufficient for all analytics in core.py.

**Return type note:** `DB` currently returns `sqlite3.Row` objects accessed via `d["field"]`. All backends must return dicts or objects supporting `["key"]` subscript access. Use TypedDicts for clarity in the ABC.

**Trade-offs:** No redesign risk, Corpulse logic is untouched, any future method additions are additive.

```python
from abc import ABC, abstractmethod
from typing import TypedDict

class DocumentRow(TypedDict):
    doc_id: str
    filename: str
    embedding_vec: bytes | None
    embedded_at: float | None
    source_updated_at: float | None

class StorageBackend(ABC):
    @abstractmethod
    def upsert_document(self, doc_id: str, filename: str,
                        embedding: bytes | None = None,
                        embedded_at: float | None = None) -> None: ...

    @abstractmethod
    def insert_retrieval(self, doc_id: str, query_hash: str,
                         rank: int, score: float,
                         retrieved_at: float) -> None: ...

    @abstractmethod
    def insert_engagement(self, doc_id: str, event_type: str,
                          engaged_at: float) -> None: ...

    @abstractmethod
    def update_source_timestamp(self, doc_id: str,
                                updated_at: float) -> None: ...

    @abstractmethod
    def all_documents(self) -> list[DocumentRow]: ...

    @abstractmethod
    def retrieval_counts(self, since: float) -> list[dict]: ...

    @abstractmethod
    def engagement_counts(self, since: float) -> list[dict]: ...

    @abstractmethod
    def all_embeddings(self) -> list[dict]: ...
```

### Pattern 2: Sync-Only ABC, Async Backend Handled at Call Site

**What:** The `StorageBackend` ABC is synchronous throughout. `AsyncPostgresBackend` exposes the same sync method signatures but its internals use asyncpg. It is NOT a subclass of `StorageBackend` -- it is a parallel class with matching method names but `async def` signatures. Corpulse stays sync. The async path is only invoked from async callers who use `asyncio.to_thread()` at the call site -- exactly as `AsyncQdrantCorpulseClient` already does.

**When to use:** This is the correct model for this codebase because:
1. Corpulse analytics (get_ghosts, get_duplicates, etc.) are synchronous aggregation operations.
2. `AsyncQdrantCorpulseClient` already handles the sync/async bridge via `asyncio.to_thread()`.
3. Adding async to the ABC would force SQLiteBackend and InMemoryBackend to fake async methods with `async def`.

**Concrete type hierarchy:**

```
StorageBackend (ABC, sync)
    SQLiteBackend       -- sync, inherits ABC
    PostgresBackend     -- sync, inherits ABC, psycopg 3 has sync API
    InMemoryBackend     -- sync, inherits ABC, dict-based

AsyncPostgresBackend    -- NOT in ABC hierarchy
                           mirrors same 8 method names, async def signatures
                           asyncpg internally
                           Corpulse constructor accepts it via duck typing
```

**Trade-offs:** Clean ABC with no fake async. Slight inconsistency that AsyncPostgresBackend is outside the type hierarchy, but this is consistent with the existing async pattern in the codebase and avoids async bleeding into the analytics layer.

### Pattern 3: Backend-Owned Connection Lifecycle with Internal Schema Init

**What:** Each backend owns its connection lifecycle. `__init__()` receives only what it needs (file path for SQLite, DSN or pool for Postgres). Schema initialization happens inside the backend -- Corpulse is not involved.

**When to use:** Always. Matches how existing `DB` class works and keeps Corpulse clean.

**Per-backend connection design:**

- **SQLiteBackend:** One connection per operation using the existing `_conn()` contextmanager pattern. No pooling needed. WAL mode set once at init via `executescript`.

- **PostgresBackend (psycopg 3):** psycopg 3 provides both a sync `Connection` and `ConnectionPool` (`psycopg_pool`). Accept either a DSN string (create an internal pool) or a pre-constructed pool. Schema init on first connection via `cursor.execute(SCHEMA_SQL)`.

- **AsyncPostgresBackend (asyncpg):** asyncpg provides `asyncpg.create_pool()`. Accept a pre-created pool or DSN. Schema cannot be initialized in `__init__` because `__init__` cannot be async -- expose `async def initialize()` that callers must await before first use.

- **InMemoryBackend:** No schema needed. Initialize Python dicts in `__init__`: `self._documents: dict[str, dict] = {}`, `self._retrievals: list[dict] = []`, `self._engagements: list[dict] = []`.

**Schema portability:** Each backend owns its own DDL string. SQLite and Postgres are close enough that minor dialect differences (AUTOINCREMENT vs SERIAL/IDENTITY, BLOB vs BYTEA, REAL vs DOUBLE PRECISION) are manageable per-backend without a shared abstraction.

```python
class PostgresBackend(StorageBackend):
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS documents (
        doc_id            TEXT PRIMARY KEY,
        filename          TEXT,
        embedding_vec     BYTEA,
        embedded_at       DOUBLE PRECISION,
        source_updated_at DOUBLE PRECISION DEFAULT NULL
    );
    CREATE TABLE IF NOT EXISTS retrievals (
        id           BIGSERIAL PRIMARY KEY,
        doc_id       TEXT NOT NULL,
        query_hash   TEXT NOT NULL,
        rank         INTEGER,
        score        DOUBLE PRECISION,
        retrieved_at DOUBLE PRECISION NOT NULL
    );
    CREATE TABLE IF NOT EXISTS engagements (
        id          BIGSERIAL PRIMARY KEY,
        doc_id      TEXT NOT NULL,
        event_type  TEXT NOT NULL,
        engaged_at  DOUBLE PRECISION NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_retrievals_doc  ON retrievals(doc_id);
    CREATE INDEX IF NOT EXISTS idx_retrievals_time ON retrievals(retrieved_at);
    CREATE INDEX IF NOT EXISTS idx_engagements_doc ON engagements(doc_id);
    """
```

## Data Flow

### Write Path (log_retrieval example)

```
async caller
    |
    AsyncQdrantCorpulseClient.query_points()
        |
        asyncio.to_thread(corpulse.log_retrieval, records, "")
            |
            Corpulse.log_retrieval(results, query)
                |
                backend.upsert_document(...)   [for each result]
                backend.insert_retrieval(...)  [for each result]
                    |
                    [backend writes to SQLite / Postgres]

sync caller
    |
    Corpulse.log_retrieval(results, query)
        |
        backend.upsert_document(...)
        backend.insert_retrieval(...)
```

### Read Path (corpus_health example)

```
corpulse.corpus_health()
    |
    backend.all_documents()         -> list[DocumentRow]
    |
    corpulse.get_ghosts()
        |-- backend.retrieval_counts(since=cutoff)  -> list[dict]
        |-- backend.all_documents()                 -> list[DocumentRow]
    |
    corpulse.get_duplicates()
        |-- backend.all_embeddings()                -> list[dict]
    |
    ... (other analytics, all via backend methods, all unchanged)
```

### Corpulse Constructor Change (only change to core.py)

```python
# BEFORE
def __init__(self, db_path: str = "./corpulse.db", ...):
    self.db = DB(db_path)

# AFTER
def __init__(
    self,
    db_path: str = "./corpulse.db",        # kept for backwards compat
    backend: StorageBackend | None = None,  # explicit override
    ...
):
    if backend is not None:
        self.db = backend
    else:
        from .backends.sqlite import SQLiteBackend
        self.db = SQLiteBackend(db_path)
```

All analytics methods in core.py remain untouched. `self.db` is still how Corpulse accesses the backend -- the attribute name does not change.

## Integration Points

### New Components vs Modified Components

| Component | Change Type | What Changes |
|-----------|-------------|--------------|
| `corpulse/core.py` | Modified | Constructor only: `backend=None` added, `self.db = DB(...)` becomes conditional |
| `corpulse/db.py` | Modified | Becomes a one-line compat shim: `from .backends.sqlite import SQLiteBackend as DB` |
| `corpulse/backends/__init__.py` | New | Re-exports ABC + all backends |
| `corpulse/backends/base.py` | New | `StorageBackend` ABC + `DocumentRow` TypedDict |
| `corpulse/backends/sqlite.py` | New | `SQLiteBackend` -- DB class body moved verbatim |
| `corpulse/backends/postgres.py` | New | `PostgresBackend` (psycopg 3) + `AsyncPostgresBackend` (asyncpg) |
| `corpulse/backends/memory.py` | New | `InMemoryBackend` -- dict-based |
| `corpulse/__init__.py` | Modified | Expose `SQLiteBackend`, `PostgresBackend`, `AsyncPostgresBackend`, `InMemoryBackend` |
| `pyproject.toml` | Modified | Add `postgres` extra (psycopg + psycopg-pool); `postgres-async` extra (asyncpg) |
| `corpulse/integrations/qdrant.py` | No change | Calls corpulse.log_retrieval() -- completely unaffected |
| `tests/` | Extended | New test files for each backend; existing 39 tests must stay green without modification |

### Internal Boundary: Corpulse ↔ StorageBackend

| Boundary | Communication | Constraint |
|----------|---------------|------------|
| Corpulse -> backend | Direct sync method calls | All ABC methods must be sync |
| Corpulse constructor | `backend=` kwarg, defaults to SQLiteBackend | `db_path` still accepted for SQLite default path |
| AsyncQdrantCorpulseClient -> Corpulse | asyncio.to_thread() (unchanged) | No change to qdrant.py required |
| AsyncPostgresBackend -> caller | Caller must await `initialize()` before first use | Cannot do async init in `__init__` |

### External Dependencies per Backend

| Backend | Dependency | pyproject.toml extra |
|---------|-----------|----------------------|
| SQLiteBackend | stdlib `sqlite3` | none (zero new deps) |
| InMemoryBackend | none | none |
| PostgresBackend | `psycopg[binary]>=3.1`, `psycopg-pool>=3.1` | `corpulse[postgres]` |
| AsyncPostgresBackend | `asyncpg>=0.29` | `corpulse[postgres-async]` |

## Build Order

Dependencies between components determine this order:

**Step 1: StorageBackend ABC + TypedDicts** (`backends/base.py`)
The contract everything else implements. Build first. Includes `DocumentRow`, `RetrievalRow`, `EngagementRow` TypedDicts that replace `sqlite3.Row` throughout.

**Step 2: SQLiteBackend** (`backends/sqlite.py`)
Move DB class body verbatim into this file. No logic changes. Verify all 39 existing tests pass unchanged after `db.py` becomes a shim. This is the regression gate for the entire refactor.

**Step 3: Update core.py constructor + db.py shim**
One-line change to constructor. Two-line shim in db.py. After this step, `Corpulse()` with no args must still work exactly as before.

**Step 4: InMemoryBackend** (`backends/memory.py`)
Dict-based, no external dependencies. Enables writing tests for PostgresBackend without needing a real database. Build before Postgres.

**Step 5: PostgresBackend** (sync, psycopg 3)
Requires Postgres for integration tests (Docker Compose fixture is the standard approach). Implement all 8 methods. Share schema DDL as a class constant.

**Step 6: AsyncPostgresBackend** (asyncpg)
Implement after sync backend is tested. Share the Postgres schema DDL. The `async def initialize()` pattern must be documented clearly for callers.

**Step 7: Package exports + pyproject.toml extras**
Wire backends into `__init__.py`. Add `[postgres]` and `[postgres-async]` optional dependency groups. Ensure lazy imports so that `import corpulse` without psycopg installed does not raise.

## Anti-Patterns

### Anti-Pattern 1: Making the ABC Async

**What people do:** Define `StorageBackend` with `async def all_documents()`, `async def upsert_document()` etc. to "support async backends natively."

**Why it's wrong:** Corpulse analytics (get_ghosts, get_duplicates, corpus_health) are synchronous aggregation loops. If the ABC is async, every analytics method must become async, which cascades through all tests, the Qdrant wrapper, and user code. The existing codebase explicitly bridges sync/async with `asyncio.to_thread()` -- that pattern must be preserved.

**Do this instead:** Keep the ABC sync. `AsyncPostgresBackend` exists outside the ABC hierarchy with async method signatures, used only from async callers who handle the thread bridging themselves.

### Anti-Pattern 2: Connection String as the Only Backend Config

**What people do:** `Corpulse(dsn="postgresql://...")` as the only Postgres config path.

**Why it's wrong:** Doesn't support pre-configured connection pools, which is how production services use Postgres. A service repo managing its own pool cannot hand it to Corpulse.

**Do this instead:** Accept either a DSN string or a pre-constructed backend instance. `Corpulse(backend=PostgresBackend(pool=my_pool))` gives full control. DSN string convenience lives on the backend constructor: `PostgresBackend(dsn="...")` creates an internal pool.

### Anti-Pattern 3: Schema Migration Logic in the ABC

**What people do:** `StorageBackend.migrate()` as an abstract method, trying to unify schema management.

**Why it's wrong:** Each backend has different schema syntax and migration tools. SQLite has no migrations tooling. Postgres teams use Alembic or raw SQL. Abstracting this creates a leaky abstraction with no gain.

**Do this instead:** Each backend handles its own schema initialization internally. For production Postgres, document that schema init is idempotent (`CREATE TABLE IF NOT EXISTS`) and safe to run on startup. Structural migrations (ALTER TABLE) are out of scope for this milestone.

### Anti-Pattern 4: Modifying Analytics Logic During the Refactor

**What people do:** "While we're at it, let's improve get_ghosts() to make fewer DB calls."

**Why it's wrong:** The existing 39 tests cover analytics behavior. Any change to analytics during a backend refactor makes it impossible to attribute test failures to the backend layer vs the analytics layer.

**Do this instead:** The refactor must be behavior-neutral. Move DB body to SQLiteBackend, change only the constructor in core.py. Verify green tests before writing any new backend code.

### Anti-Pattern 5: Changing self.db Attribute Name

**What people do:** Rename `self.db` to `self._backend` or `self.storage` in Corpulse to "better reflect" the new architecture.

**Why it's wrong:** `self.db` is used in 8+ call sites throughout core.py. Renaming is a mechanical change that adds diff noise and failure surface with no benefit. The attribute is private by convention.

**Do this instead:** Keep `self.db` as the attribute name. The backend object assigned to it simply changes from a `DB` instance to a `StorageBackend` instance.

## Sources

- Direct codebase inspection: `corpulse/db.py`, `corpulse/core.py`, `corpulse/integrations/qdrant.py`, `corpulse/__init__.py`, `pyproject.toml` (2026-04-08)
- Python `abc` module documentation: `abc.ABC`, `@abstractmethod` (stdlib)
- psycopg 3 connection pool: `psycopg_pool.ConnectionPool` -- sync pool for service use
- asyncpg pool design: `asyncpg.create_pool()` -- requires explicit `async def initialize()` since `__init__` cannot be async
- Existing async bridge pattern: `asyncio.to_thread()` already in use in `AsyncQdrantCorpulseClient` for sync DB writes from async context

---
*Architecture research for: corpulse v1.1 pluggable storage backends*
*Researched: 2026-04-08*
