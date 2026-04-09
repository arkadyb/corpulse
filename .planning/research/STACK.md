# Stack Research

**Domain:** Python library — Pluggable storage backends (PostgreSQL sync/async, InMemory, refactored SQLite)
**Researched:** 2026-04-08
**Confidence:** HIGH (versions verified against PyPI; interface patterns verified against Python official docs)

## Context

This research covers only the new additions for the v1.1 pluggable storage backends milestone. The existing stack (SQLite via `db.py`, numpy, scikit-learn, pandas, tabulate, qdrant-client, hatchling, pytest) is not re-researched.

The question is: what specific libraries, versions, and interface patterns are needed to introduce a `StorageBackend` ABC, refactor `DB` into `SQLiteBackend`, add `PostgresBackend` (sync), `AsyncPostgresBackend`, and `InMemoryBackend`?

---

## Recommended Stack

### Core Technologies (new additions only)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| psycopg | >=3.2 | Sync PostgreSQL driver (`PostgresBackend`) | psycopg 3 is the actively developed successor to psycopg2; new features go here only; ships both sync `Connection` and async `AsyncConnection` in the same package; pure-Python install works without system libpq if users install `psycopg[binary]`; library consumers should pin `psycopg` without extras and let users choose their install variant |
| asyncpg | >=0.29 | Async PostgreSQL driver (`AsyncPostgresBackend`) | Fastest async PostgreSQL driver available (5x faster than psycopg3 async in benchmarks); production-stable (0.31.0 released Nov 2025); uses binary protocol exclusively; Python 3.9+; separate package means users pay zero overhead if they only need sync |
| Python `abc` stdlib | built-in | `StorageBackend` abstract base class | stdlib, no dependency; `ABC` + `@abstractmethod` enforces interface at instantiation time, not call time — catches missing implementations early; right tool when you control the class hierarchy (all backends are defined in-library) |
| Python `typing.Protocol` | built-in (3.8+) | Optional: type-checker-friendly interface annotation | Use alongside ABC for static analysis; `@runtime_checkable` Protocol gives isinstance()-checks but only verifies attribute existence, not signatures — ABC is the enforcement mechanism, Protocol is the annotation mechanism |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| psycopg[binary] | >=3.2 | Binary wheel variant of psycopg for end-user installs | In application pyproject.toml or Docker images where build tools are absent; NOT in corpulse's own dependency declaration |
| psycopg[c] | >=3.2 | C-extension variant of psycopg for performance | In production deployments where libpq and a C compiler are available; faster than binary variant; NOT in corpulse's own dependency declaration |
| pytest-asyncio | >=0.23 | Already present — needed for AsyncPostgresBackend tests | Already in dev extras; use `asyncio_mode = "auto"` which is already configured in pyproject.toml |

### Development Tools (no changes needed)

Existing tooling (hatchling, pytest, pytest-asyncio) is sufficient. No additions required.

---

## Interface Design: ABC vs Protocol

**Use `ABC` with `@abstractmethod` as the enforcement mechanism.** Use `typing.Protocol` as an optional annotation for users who want to implement a custom backend without subclassing.

Rationale: corpulse owns all backends (`SQLiteBackend`, `PostgresBackend`, `AsyncPostgresBackend`, `InMemoryBackend`). All ship in the library. This is the exact use case ABCs are designed for — a closed class hierarchy where the library enforces the contract. Protocol adds nothing for enforcement here but adds value as a type annotation for external implementors.

Concrete pattern:

```python
# corpulse/backends/base.py
from abc import ABC, abstractmethod

class StorageBackend(ABC):
    @abstractmethod
    def upsert_document(self, doc_id: str, filename: str,
                        embedding: bytes | None, embedded_at: float | None) -> None: ...

    @abstractmethod
    def insert_retrieval(self, doc_id: str, query_hash: str,
                         rank: int, score: float, retrieved_at: float) -> None: ...

    @abstractmethod
    def insert_engagement(self, doc_id: str, event_type: str, engaged_at: float) -> None: ...

    @abstractmethod
    def update_source_timestamp(self, doc_id: str, updated_at: float) -> None: ...

    @abstractmethod
    def all_documents(self) -> list: ...

    @abstractmethod
    def retrieval_counts(self, since: float) -> list: ...

    @abstractmethod
    def engagement_counts(self, since: float) -> list: ...

    @abstractmethod
    def all_embeddings(self) -> list: ...
```

The `AsyncStorageBackend` is a parallel ABC where every method is `async def`. Do not make sync and async share a base class — they are different call protocols and mixing them leads to confusing errors.

---

## psycopg vs asyncpg for Async

Both are viable; the project uses **both** because they serve different user needs:

- `PostgresBackend` (sync): uses `psycopg` (psycopg3). Sync PostgreSQL in the same library that provides async via `AsyncConnection`. Single dependency for sync users.
- `AsyncPostgresBackend`: uses `asyncpg`. Faster binary protocol driver; preferred when users are already in an async service (the primary production use case for this backend). asyncpg is a separate package, separate optional extra.

This is not redundancy — it is intentional. Sync users install `[postgres]`, async users install `[postgres-async]`. Users running both would need both, but that's an unusual combination.

---

## pyproject.toml Changes

Add two new optional extras. Keep existing `qdrant` and `dev` extras unchanged:

```toml
[project.optional-dependencies]
qdrant        = ["qdrant-client>=1.7.1"]
postgres      = ["psycopg>=3.2"]
postgres-async = ["asyncpg>=0.29"]
dev           = ["pytest>=8.0", "pytest-asyncio>=0.23"]
```

Do NOT add `psycopg[binary]` or `psycopg[c]` in the library's own dependency — only declare `psycopg>=3.2`. Let end-users choose the install variant appropriate to their environment. This follows the psycopg3 official documentation guidance for libraries.

---

## InMemoryBackend

No new dependencies. Pure Python dicts and lists. The only constraint is thread safety if users call into corpulse from multiple threads — use `threading.Lock` internally. This is a stdlib-only concern, no new packages.

---

## Installation

```bash
# Users who want sync Postgres
pip install "corpulse[postgres]"

# Users who want async Postgres
pip install "corpulse[postgres-async]"

# Users who want both
pip install "corpulse[postgres,postgres-async]"

# Development (run all tests including Postgres)
pip install -e ".[postgres,postgres-async,dev]"
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `abc.ABC` + `@abstractmethod` | `typing.Protocol` alone | If corpulse exposed a public interface for third-party backends and wanted to allow structural (duck-typed) implementations without subclassing; not the case now, all backends are first-party |
| psycopg3 for sync Postgres | psycopg2 | Only if targeting Python <3.8 or needing a long-established ecosystem with many ORMs; psycopg2 is in maintenance mode — no new features planned; for new code, psycopg3 is the right choice |
| asyncpg for async Postgres | psycopg3 async (`AsyncConnection`) | If you want a single dependency for both sync and async Postgres, use psycopg3 for both. asyncpg is faster but is async-only. The decision to use asyncpg here is about giving async users the fastest possible driver, not minimizing dependencies. |
| Separate `postgres` and `postgres-async` extras | Single `postgres` extra with both psycopg and asyncpg | Only if you want simpler install UX at the cost of always pulling in both drivers; most production users are either sync or async, not both |
| `threading.Lock` in InMemoryBackend | No lock | Only if corpulse explicitly documents single-threaded-only guarantee; adding a lock costs nothing |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| psycopg2 | Maintenance mode; no new features; psycopg3 has superior async support and better type annotations | `psycopg>=3.2` |
| SQLAlchemy as abstraction layer | Adds a large ORM dependency; corpulse uses raw SQL by design to stay lightweight and infrastructure-free by default; would complicate the SQLiteBackend which needs BLOB storage for numpy arrays | Raw SQL in each backend |
| databases (encode/databases) | Thin async wrapper over SQLAlchemy core; adds indirection without eliminating SQLAlchemy; no active development as of 2025 | asyncpg directly |
| aiopg | psycopg2-based async driver; psycopg2 maintenance mode means aiopg has no future | asyncpg |
| `@runtime_checkable` Protocol as sole interface | `isinstance()` on a `@runtime_checkable` Protocol only checks attribute existence, not method signatures — a backend can have `upsert_document = None` and still pass the check | ABC with `@abstractmethod` as the primary enforcement mechanism |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| psycopg>=3.2 | Python 3.8+ | 3.3.3 released 2026-02-18; verified on PyPI. Library pins `>=3.2` (when async-to-sync auto-conversion landed, making the codebase more stable). |
| asyncpg>=0.29 | Python 3.9+ | 0.31.0 released 2025-11-24; verified on PyPI. Python 3.9+ aligns with project's 3.10+ constraint. |
| abc (stdlib) | Python 3.4+ | Built-in; no version concern for a 3.10+ project. |
| pytest-asyncio>=0.23 | Python 3.10+ | Already in dev extras; `asyncio_mode = "auto"` already configured in pyproject.toml — no changes needed. |

---

## Sources

- [psycopg PyPI](https://pypi.org/project/psycopg/) — version 3.3.3 confirmed, released 2026-02-18. **HIGH confidence.**
- [psycopg installation docs](https://www.psycopg.org/psycopg3/docs/basic/install.html) — binary/c/pure-python variants; library vs application dependency guidance. **HIGH confidence.**
- [asyncpg PyPI](https://pypi.org/project/asyncpg/) — version 0.31.0 confirmed, released 2025-11-24; Python 3.9+. **HIGH confidence.**
- [psycopg3 vs asyncpg benchmark](https://fernandoarteaga.dev/blog/psycopg-vs-asyncpg/) — asyncpg ~5x faster than psycopg3 async in request throughput benchmarks. **MEDIUM confidence** (third-party benchmark; methodology not fully disclosed).
- [Python abc stdlib docs](https://docs.python.org/3/library/abc.html) — `ABC`, `@abstractmethod` semantics; catches missing implementations at instantiation. **HIGH confidence.**
- [ABC vs Protocol analysis](https://jellis18.github.io/post/2022-01-11-abc-vs-protocol/) — ABC for nominal subtyping with controlled class hierarchy; Protocol for structural subtyping / third-party implementors. **MEDIUM confidence** (community article, aligned with official PEP 544 guidance).
- [PEP 544 — Protocols](https://peps.python.org/pep-0544/) — `@runtime_checkable` only checks attribute existence, not signatures. **HIGH confidence.**
- [Python Packaging — writing pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — `[project.optional-dependencies]` syntax for extras. **HIGH confidence.**
- psycopg2 maintenance status: [psycopg features page](https://www.psycopg.org/features/) and [GeeksForGeeks comparison](https://www.geeksforgeeks.org/python/comparing-psycopg2-vs-psycopg-in-python/) confirm psycopg2 receives no new features. **HIGH confidence.**

---
*Stack research for: corpulse v1.1 pluggable storage backends*
*Researched: 2026-04-08*
