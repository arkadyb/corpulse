# Feature Research

**Domain:** Pluggable storage backends for Python analytics library
**Researched:** 2026-04-08
**Confidence:** HIGH (for ABC/interface patterns) / MEDIUM (for async/sync dual support tradeoffs)

---

## Context

corpulse v1.0 ships a working analytics engine backed by a single SQLite `DB` class (8 public
methods). This milestone extracts a `StorageBackend` ABC, refactors `DB` into `SQLiteBackend`,
and adds `PostgresBackend`, `AsyncPostgresBackend`, and `InMemoryBackend`. The existing
`Corpulse(db_path=...)` constructor must remain backward-compatible; `Corpulse()` with no args
defaults to `SQLiteBackend`.

Feature classification below is scoped exclusively to what is needed for this milestone. Features
already shipped are noted but not prioritized — they are assumed complete.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features whose absence makes the pluggable backend system feel broken or incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **`StorageBackend` ABC with all 8 existing methods as abstractmethods** | Without a formal interface, "pluggable" is just a naming convention — no enforcement at instantiation; any library offering pluggability must enforce the contract at the class system level | LOW | Use `ABC` + `@abstractmethod`. Python raises `TypeError` on instantiation if any abstract method is unimplemented. The 8 methods are: `upsert_document`, `insert_retrieval`, `insert_engagement`, `update_source_timestamp`, `all_documents`, `retrieval_counts`, `engagement_counts`, `all_embeddings` |
| **`SQLiteBackend` as a drop-in refactor of existing `DB`** | Existing users must not be broken; `Corpulse()` must continue to work exactly as before with SQLite as the default | LOW | Rename `DB` → `SQLiteBackend`, make it inherit from `StorageBackend`. Constructor signature stays the same (`db_path`). `Corpulse(db_path=...)` must still work. |
| **`InMemoryBackend` for testing** | Every plugin-architecture library provides an in-memory backend for unit tests; without it, tests require real DB infrastructure | LOW | Dict-of-lists implementation. No persistence. Should clear state per-test via standard `setUp`/`teardown` or fixture. No external dependencies. |
| **`PostgresBackend` (sync) via psycopg** | Service repos that adopt corpulse will run PostgreSQL, not SQLite; sync backend is the first step before async | MEDIUM | Requires `psycopg` (v3, package name `psycopg`). Connection string or connection object as constructor arg. Schema init via `CREATE TABLE IF NOT EXISTS`. |
| **`AsyncPostgresBackend` via asyncpg** | FastAPI and other async service repos cannot block the event loop on DB writes; an async backend is required for production async usage | HIGH | Requires `asyncpg`. All 8 methods become `async def`. The `Corpulse` class or its callers must `await` these. Requires careful handling of `Corpulse` facade — currently synchronous throughout. |
| **`Corpulse(backend=...)` explicit config with SQLite default** | Users must be able to pass a configured backend instance at construction time; implicit path-based detection would be a footgun | LOW | Change `Corpulse.__init__` signature: add `backend: StorageBackend | None = None`. When `None`, construct `SQLiteBackend(db_path)`. When provided, use it and ignore `db_path`. |
| **Optional extras in `pyproject.toml` for Postgres drivers** | `psycopg` and `asyncpg` must not be hard dependencies; SQLite users should not be forced to install Postgres drivers | LOW | Add `[postgres]` extra for `psycopg`, `[asyncpg]` extra for `asyncpg` (or combined `[postgres]` covering both). Lazy import with clear `ImportError` message in each backend. |
| **Schema initialization in each backend** | Each backend must create its own tables on first use without requiring users to run migrations manually | LOW-MEDIUM | SQLite: `executescript(SCHEMA)` already done. Postgres: `CREATE TABLE IF NOT EXISTS` on `__init__` or `connect()`. InMemory: no-op. Alembic is overkill for this milestone — programmatic DDL is sufficient. |

### Differentiators (Competitive Advantage)

Features that make the pluggable system more useful than the minimum viable interface.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **`InMemoryBackend` that matches Postgres semantics** | Most in-memory backends are simplistic and mask bugs that only appear on real DBs; an in-memory backend that mimics Postgres filtering, grouping, and timestamp semantics catches more bugs in tests | MEDIUM | Implement `retrieval_counts(since)` and `engagement_counts(since)` with proper timestamp filtering in Python, not just a dict count. This is what makes it trustworthy as a test double. |
| **Connection pool support in `PostgresBackend`** | Production Postgres usage requires connection pooling; a backend that opens a new connection per call will exhaust Postgres' connection limit under any real load | MEDIUM | `psycopg_pool.ConnectionPool` (sync) or `psycopg_pool.AsyncConnectionPool` (async). Pool is created in `__init__`, closed in `close()`. Expose `min_size`/`max_size` as constructor args with sensible defaults. |
| **`close()` / context manager support on all backends** | Resource cleanup is expected behavior in any backend that holds connections; without it, long-running processes leak connections | LOW | Add `close()` to the ABC. Implement `__enter__`/`__exit__` (sync) and `__aenter__`/`__aexit__` (async) on `PostgresBackend` and `AsyncPostgresBackend`. `SQLiteBackend` and `InMemoryBackend` can no-op `close()`. |
| **Type-annotated return types across all backends** | Static analysis and IDE support degrade badly when backends return `sqlite3.Row` (which is not a plain dict); a typed `TypedDict` or `dataclass` return makes downstream code type-safe | MEDIUM | Define `DocumentRow`, `RetrievalCountRow`, `EngagementCountRow`, `EmbeddingRow` as `TypedDict`. All backends return these types. Existing `core.py` dict-key access (`d["doc_id"]`) continues to work. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Alembic / migration framework** | "How do I evolve the schema across versions?" | Alembic requires SQLAlchemy ORM or raw engine config, adds a CLI migration step to the user workflow, and is excessive for a library with 3 stable tables and zero user-visible schema changes in v1.1 | Programmatic `CREATE TABLE IF NOT EXISTS` DDL in each backend's `__init__` is sufficient; document the upgrade path (drop-recreate) for the rare schema change |
| **SQLAlchemy Core as the backend abstraction layer** | "Use SQLAlchemy so you get all backends for free" | SQLAlchemy Core adds 500ms+ import time, opinionated query API that fights the existing raw-SQL style, and is a hard dependency for all users including those who only use SQLite | Keep raw SQL per backend; the ABC interface is the abstraction, not an ORM |
| **Generic connection-string factory** | "Accept a DSN string and auto-detect the backend" | Magic string parsing is a source of misconfiguration bugs; users paste wrong DSNs and get cryptic errors | Require explicit backend instantiation: `Corpulse(backend=PostgresBackend("postgresql://..."))` — clear intent, clear error on misconfiguration |
| **Async-from-sync bridge inside `Corpulse`** | "Make `Corpulse` itself async-transparent so it works with both backends" | Bridging async→sync with `asyncio.run()` inside sync methods blocks the event loop if called from an async context; bridging sync→async with `run_in_executor` adds thread overhead and deadlock risk; both approaches make the codebase significantly harder to maintain | Two separate usage paths: sync `Corpulse` + `SQLiteBackend`/`PostgresBackend` for sync code; `AsyncCorpulse` (or user-side `await`) + `AsyncPostgresBackend` for async code. Document clearly which to use. |
| **Connection string validation / health-check on init** | "Verify the DB is reachable when the backend is constructed" | Eager connection on init makes the library fail at import time in test environments, CI with no DB, and cold starts; it also complicates mocking | Connect lazily on first use; surface `OperationalError` on the first actual DB call, which is the right time to fail |
| **ORM-style model layer** | "Add a `Document` model class with `.save()`, `.delete()`" | Model classes add a mapping layer over a schema that is already minimal; no user of corpulse needs to manipulate individual document records outside of corpulse's own analytics | Keep the interface method-oriented, not model-oriented; the 8 methods are sufficient |
| **Multi-backend write fan-out** | "Write to both SQLite and Postgres simultaneously for migration" | Dual-write logic belongs in the application layer, not the library; adding it here doubles complexity and introduces partial-write failure modes | Users who want dual-write should wrap two `Corpulse` instances in their own service layer |

---

## Feature Dependencies

```
[StorageBackend ABC]
    └──required by──> [SQLiteBackend]
    └──required by──> [PostgresBackend]
    └──required by──> [AsyncPostgresBackend]
    └──required by──> [InMemoryBackend]

[SQLiteBackend]
    └──refactored from──> [existing DB class] (already complete, LOW risk)

[PostgresBackend]
    └──requires──> [psycopg optional extra]
    └──uses──> [psycopg_pool.ConnectionPool for production use]

[AsyncPostgresBackend]
    └──requires──> [asyncpg optional extra]
    └──requires──> [Corpulse facade or caller to await methods]

[Corpulse(backend=...)]
    └──requires──> [StorageBackend ABC defined first]
    └──backward-compat──> [Corpulse() no-args must still work via SQLiteBackend default]

[InMemoryBackend]
    └──no external deps──> [dict + list only]
    └──enables──> [unit tests without DB infrastructure]

[close() / context manager on backends]
    └──required by──> [PostgresBackend connection pool cleanup]
    └──required by──> [AsyncPostgresBackend async pool cleanup]
    └──nice-to-have on──> [SQLiteBackend, InMemoryBackend (no-op)]

[TypedDict return types]
    └──depends on──> [StorageBackend ABC defining return annotations]
    └──enables──> [mypy / pyright type checking in downstream code]
```

### Dependency Notes

- **`StorageBackend` ABC must be defined before any backends.** It is the foundational building block; all four implementations depend on it.
- **`SQLiteBackend` is a rename+refactor of existing `DB`.** The behavioral change is minimal; risk is low but existing tests must be updated to import the new name.
- **`AsyncPostgresBackend` requires the caller to be async.** `Corpulse`'s sync facade methods (`log_retrieval`, `get_ghosts`, etc.) cannot call `await backend.upsert_document(...)` without being `async def` themselves. Either `Corpulse` grows an async variant, or callers of `AsyncPostgresBackend` must use it directly. This is the highest-complexity decision in the milestone.
- **Connection pooling is a differentiator, not a blocker.** `PostgresBackend` v1 can open a new connection per call (acceptable for low-volume service repos) and add pooling in v1.1. Document this clearly so users know when to opt in.
- **InMemoryBackend has no external dependencies.** It is purely stdlib. It should be the first backend implemented (after the ABC) because it enables writing tests before the Postgres backends exist.

---

## MVP Definition

### Launch With (v1.1 — this milestone)

- [ ] **`StorageBackend` ABC** with all 8 methods as `@abstractmethod` — foundational, everything else depends on this
- [ ] **`SQLiteBackend`** — refactor of existing `DB`; same behavior, new name, inherits ABC
- [ ] **`InMemoryBackend`** — dict-based, no deps; needed for test suite
- [ ] **`PostgresBackend` (sync)** — via `psycopg`; programmatic schema init; basic connection per call (pooling deferred)
- [ ] **`AsyncPostgresBackend`** — via `asyncpg`; all 8 methods are `async def`; programmatic schema init
- [ ] **`Corpulse(backend=...)` explicit config** with `SQLiteBackend(db_path)` as default when `backend=None`
- [ ] **`pyproject.toml` extras** for `[postgres]` (psycopg) and `[asyncpg]` (asyncpg)
- [ ] **Updated test suite** — existing 39 tests must pass; add tests for each backend using `InMemoryBackend` as the primary test double

### Add After Validation (v1.1.x)

- [ ] **Connection pool support in `PostgresBackend`** — `psycopg_pool.ConnectionPool`; expose `min_size`/`max_size`; needed when service repo starts seeing concurrent load
- [ ] **`close()` and context manager on all backends** — required for proper resource cleanup in long-running services
- [ ] **TypedDict return types** — improves downstream type safety; add once the interface is stable

### Future Consideration (v2+)

- [ ] **`AsyncCorpulse` facade** — if async usage becomes the primary use case; current milestone keeps `Corpulse` sync and makes `AsyncPostgresBackend` a lower-level escape hatch
- [ ] **MySQL/MariaDB backend** — deferred; psycopg/asyncpg are the priority
- [ ] **Schema versioning** — track schema version in a metadata table; only needed if the 3-table schema ever changes

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `StorageBackend` ABC | HIGH | LOW | P1 |
| `SQLiteBackend` refactor | HIGH | LOW | P1 |
| `InMemoryBackend` | HIGH (enables tests) | LOW | P1 |
| `Corpulse(backend=...)` config | HIGH | LOW | P1 |
| `PostgresBackend` (sync) | HIGH | MEDIUM | P1 |
| `AsyncPostgresBackend` | HIGH | HIGH | P1 |
| `pyproject.toml` extras | HIGH | LOW | P1 |
| Updated test suite | HIGH | MEDIUM | P1 |
| Connection pooling | MEDIUM | MEDIUM | P2 |
| `close()` / context manager | MEDIUM | LOW | P2 |
| TypedDict return types | MEDIUM | MEDIUM | P2 |
| `AsyncCorpulse` facade | LOW (deferred) | HIGH | P3 |

**Priority key:**
- P1: Must have for v1.1 launch
- P2: Add when core is validated and production usage begins
- P3: Future milestone

---

## Implementation Notes

These are research findings that directly constrain feature behavior:

**ABC vs Protocol trade-off:** For this codebase, `ABC` + `@abstractmethod` is preferred over `typing.Protocol`. Reasons: (1) `Protocol` provides static checking only — no runtime enforcement at instantiation; (2) `ABC` raises `TypeError` immediately if a backend is missing a method, which is the right behavior for a plugin system users will implement themselves; (3) `ABC` is more familiar to library users implementing their own backends. Use `Protocol` only for optional type-hint-only interfaces; use `ABC` where runtime contract enforcement matters.

**Async/sync boundary decision:** The research confirms the two approaches for dual sync/async support in Python libraries are: (a) separate sync and async ABCs + implementations, and (b) auto-generated sync code from async (httpcore/encode pattern using `unasync`). For this codebase, separate ABCs is the right choice — the codebase is small, the methods are simple, and auto-generation adds CI complexity without proportional benefit. The async backend is essentially the same methods with `async def` + `await pool.acquire()`.

**psycopg vs asyncpg:** psycopg3 offers a unified sync/async API (same `psycopg` package, `AsyncConnection` vs `Connection`). asyncpg is async-only but faster for raw throughput. For this library's write-heavy-but-low-volume workload (a few rows per query event), psycopg3 is sufficient for both `PostgresBackend` and `AsyncPostgresBackend`. Using psycopg3 for both simplifies the optional-dependency story (`pip install corpulse[postgres]` for both sync and async). asyncpg remains an option if raw async throughput becomes a concern.

**Schema migration for Postgres:** `CREATE TABLE IF NOT EXISTS` in `__init__` (or a `_init_schema()` method called on first connection) is the correct approach for this milestone. Alembic is excessive. Document that dropping and recreating tables is the upgrade path for schema changes. This is a library constraint, not a production DB constraint — the service repo owns its migration tooling.

**InMemoryBackend correctness:** `retrieval_counts(since: float)` and `engagement_counts(since: float)` must filter by timestamp in Python (not just count all rows), otherwise tests that rely on time-windowed ghost/suspect detection will pass incorrectly against `InMemoryBackend` and fail on real backends.

---

## Sources

- [Python `abc` module — official docs](https://docs.python.org/3/library/abc.html) — HIGH confidence
- [pyncette — pluggable storage backend pattern in Python scheduler](https://github.com/tibordp/pyncette) — MEDIUM confidence (real-world reference implementation)
- [steerage — pluggable async storage backends library](https://github.com/eykd/steerage/) — MEDIUM confidence (pattern reference)
- [psycopg3 connection pool docs](https://www.psycopg.org/psycopg3/docs/advanced/pool.html) — HIGH confidence (official)
- [psycopg3 async docs](https://www.psycopg.org/psycopg3/docs/advanced/async.html) — HIGH confidence (official)
- [Combining sync and async Python code — DRY package pattern (2025)](https://spwoodcock.dev/blog/2025-02-python-dry-async/) — MEDIUM confidence
- [ABC vs Protocol in Python — Justin A. Ellis](https://jellis18.github.io/post/2022-01-11-abc-vs-protocol/) — MEDIUM confidence
- [Python Protocols for structural subtyping — Real Python](https://realpython.com/python-protocol/) — MEDIUM confidence
- [Repository Pattern in Python — Cosmic Python](https://www.cosmicpython.com/book/chapter_02_repository.html) — MEDIUM confidence
- [10 asyncpg & psycopg3 patterns — Medium 2026](https://medium.com/@sparknp1/10-asyncpg-psycopg3-patterns-for-sub-100ms-queries-eddb26e3c161) — LOW confidence (unverified, used for pattern context only)

---
*Feature research for: pluggable storage backends (corpulse v1.1)*
*Researched: 2026-04-08*
