# Phase 6: Storage Foundation - Research

**Researched:** 2026-04-08
**Domain:** Storage backend abstraction for corpulse's existing SQLite persistence layer
**Confidence:** HIGH

## User Constraints

No phase-specific `CONTEXT.md` exists for Phase 6.

Locked constraints from the roadmap, requirements, and success criteria:

- Preserve `Corpulse()` behavior exactly when no backend is passed: SQLite remains the default.
- Address only `ABS-01`, `ABS-02`, `ABS-03`, `ABS-04`, `BACK-01`, `BACK-02`, `BACK-03`, `BACK-06`, and `INT-01`.
- `db.py` must remain as a compatibility import surface.
- `InMemoryBackend` is for testability and must do no file I/O.
- Native backend exceptions must surface as `StorageBackendError` at the caller boundary.
- All backends must support `.close()` and `with Corpulse(...) as c:`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ABS-01 | StorageBackend ABC defines 8 abstract methods matching existing DB interface | Existing `DB` surface is exactly 8 methods in `corpulse/db.py`; Phase 6 should freeze those names/signatures as the contract. |
| ABS-02 | TypedDict return types shared across all backends | Current read methods already imply four stable row shapes; normalize all backend returns to plain typed mappings, not `sqlite3.Row`. |
| ABS-03 | StorageBackendError wraps native DB exceptions at the backend boundary | Catch native backend exceptions inside backend public methods and re-raise `StorageBackendError`; do not push sqlite3/other driver exceptions into `core.py`. |
| ABS-04 | Shared parametrized test fixture runs against all backend implementations | Add backend-contract tests parameterized over SQLite and in-memory; keep SQLite-only tests where they assert WAL or private `_conn()` behavior. |
| BACK-01 | SQLiteBackend refactors existing DB class with zero behavioral change | Preserve current SQL, connection lifecycle, row semantics, and compatibility hooks; current baseline is 41 passing tests, not 39. |
| BACK-02 | db.py becomes a one-line compat shim importing SQLiteBackend as DB | Keep `from corpulse.db import DB` working by aliasing `SQLiteBackend` from the new backend module layout. |
| BACK-03 | InMemoryBackend (dict-based, no deps) with full aggregate behavior | Match SQLite semantics for upsert, update-noop-on-missing-doc, aggregate row keys, and no file I/O. |
| BACK-06 | All backends implement close() and context manager protocol | Put `close`, `__enter__`, and `__exit__` on the backend contract; make `Corpulse` delegate cleanly. |
| INT-01 | Corpulse(backend=...) accepts explicit backend; defaults to SQLiteBackend when omitted | Add a `backend` parameter without breaking existing `db_path` usage and constructor defaults. |

</phase_requirements>

## Summary

Phase 6 is a seam-refactor, not a storage redesign. The current repository already has a narrow persistence contract: `corpulse/core.py` only relies on 8 `DB` methods, and those methods already imply stable row shapes. That is the correct abstraction boundary. Planning should avoid changing analytics logic or SQL behavior unless required to make the backend contract explicit.

The main implementation risk is not the ABC itself. The risk is compatibility pressure from tests and public imports. `Corpulse` currently instantiates `DB` directly, `tests/test_analytics.py` imports `DB` from `corpulse.db`, and `tests/test_qdrant_wrapper.py` reaches into the SQLite private `_conn()` helper. That means Phase 6 must separate backend-agnostic contract tests from SQLite-specific verification instead of trying to parameterize every existing test across all backends.

`InMemoryBackend` must mimic SQLite behavior more closely than it first appears. The hard parts are not storage mechanics; they are semantic parity: `upsert_document()` preserves existing embedding bytes when a later write passes `None`, `update_source_timestamp()` is a no-op for unknown documents, aggregate rows expose the same keys the analytics layer already reads, and ordering stays irrelevant. If those behaviors drift, analytics will diverge subtly between backends.

**Primary recommendation:** Create a `corpulse/backends/` package now, freeze the current 8-method DB surface as `StorageBackend`, normalize all read results to `TypedDict`-shaped plain dicts, and add a new backend-contract test module instead of over-parameterizing the current SQLite-focused tests.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `abc` | Python 3.10+ | Define `StorageBackend` abstract contract | Native, dependency-free way to freeze the backend interface |
| Python stdlib `typing.TypedDict` | Python 3.10+ | Share row shapes across backends | Matches current dict-like row access in `core.py` and avoids leaking `sqlite3.Row` |
| Python stdlib `sqlite3` | Python 3.10+ | SQLite default backend | Existing production behavior already depends on it; zero new dependency cost |
| `pytest` | 9.0.2 locally, `>=8.0` in `pyproject.toml` | Shared backend contract tests | Already installed and configured; fixture parameterization is the right tool here |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `numpy` | 2.4.4 locally, `>=1.24` in `pyproject.toml` | Embedding bytes conversion and duplicate tests | Required for existing embedding storage and duplicate detection paths |
| `scikit-learn` | 1.8.0 locally, `>=1.3` in `pyproject.toml` | Duplicate detection analytics | Existing dependency; Phase 6 must not disturb duplicate-analysis behavior |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `TypedDict` row contracts | `Protocol` or dataclasses | `TypedDict` matches current mapping-style access and keeps SQLite/InMemory returns simple |
| Separate backend package | Keep everything in `corpulse/db.py` | Faster short term, but causes immediate churn again in Phases 7-8 when Postgres backends land |
| Parameterize all existing tests | Add a new backend-contract suite | Full suite parameterization would force backend-agnostic rewrites of SQLite-private assertions too early |

**Installation:**

No new runtime dependencies are needed for Phase 6.

Use the existing dev stack:

```bash
pip install -e ".[dev,qdrant]"
```

**Version verification:** Verified from the local environment on 2026-04-08:

- `python 3.14.3`
- `pytest 9.0.2`
- `numpy 2.4.4`
- `scikit-learn 1.8.0`
- `qdrant-client 1.17.1`

## Architecture Patterns

### Recommended Project Structure

```text
corpulse/
├── backends/
│   ├── __init__.py        # exports StorageBackend, StorageBackendError, SQLiteBackend, InMemoryBackend
│   ├── base.py            # ABC, TypedDict row types, shared error wrapper helpers
│   ├── sqlite.py          # refactored current DB implementation
│   └── memory.py          # dict/list-based test backend
├── core.py                # Corpulse facade accepts backend=...
└── db.py                  # compat shim: SQLiteBackend as DB
tests/
├── conftest.py            # backend factory fixture(s)
├── test_backend_contract.py
├── test_analytics.py      # keep SQLite-default behavior and public analytics checks
└── test_qdrant_wrapper.py # keep SQLite-specific storage introspection or refactor helpers
```

### Pattern 1: Freeze the Existing 8-Method Contract

**What:** The StorageBackend ABC should exactly match the current public `DB` method surface used by `core.py`:

1. `upsert_document`
2. `insert_retrieval`
3. `insert_engagement`
4. `update_source_timestamp`
5. `all_documents`
6. `retrieval_counts`
7. `engagement_counts`
8. `all_embeddings`

Add `close()` and context-manager support as backend lifecycle methods, but do not mutate the data API shape.

**When to use:** Immediately in Phase 6. This is the stable seam both SQLite and in-memory must satisfy, and it is the seam future Postgres backends should inherit.

**Example:**

```python
# Source: repo contract inferred from corpulse/db.py and corpulse/core.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypedDict


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


class StorageBackend(ABC):
    @abstractmethod
    def upsert_document(self, doc_id: str, filename: str,
                        embedding: bytes | None = None,
                        embedded_at: float | None = None) -> None: ...

    @abstractmethod
    def insert_retrieval(self, doc_id: str, query_hash: str,
                         rank: int, score: float, retrieved_at: float) -> None: ...

    @abstractmethod
    def insert_engagement(self, doc_id: str, event_type: str,
                          engaged_at: float) -> None: ...

    @abstractmethod
    def update_source_timestamp(self, doc_id: str, updated_at: float) -> None: ...

    @abstractmethod
    def all_documents(self) -> list[DocumentRow]: ...

    @abstractmethod
    def retrieval_counts(self, since: float) -> list[RetrievalRow]: ...

    @abstractmethod
    def engagement_counts(self, since: float) -> list[EngagementRow]: ...

    @abstractmethod
    def all_embeddings(self) -> list[EmbeddingRow]: ...

    @abstractmethod
    def close(self) -> None: ...

    def __enter__(self) -> "StorageBackend":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
```

### Pattern 2: Normalize Read Results to Plain Typed Mappings

**What:** Convert SQLite reads to plain dicts matching the TypedDict contracts instead of returning raw `sqlite3.Row` objects.

**When to use:** For every backend read method in Phase 6.

**Why:** `core.py` already only uses key-based access (`row["doc_id"]`, `row["cnt"]`, `row["embedding_vec"]`). Returning plain dicts makes backend behavior explicit and keeps InMemoryBackend natural.

**Example:**

```python
# Source: https://docs.python.org/3/library/sqlite3.html and current repo usage
def all_documents(self) -> list[DocumentRow]:
    with self._conn() as conn:
        rows = conn.execute("SELECT * FROM documents").fetchall()
    return [dict(row) for row in rows]
```

### Pattern 3: Wrap Native Backend Exceptions Only at Backend Boundaries

**What:** Catch backend-native exceptions inside backend public methods and re-raise `StorageBackendError`, preserving the original exception with `raise ... from exc`.

**When to use:** Around SQLite `connect`, `execute`, `executescript`, and equivalent future backend driver calls.

**Why:** `core.py` should depend on storage behavior, not on sqlite3 exception classes. The requirement is explicit that native DB exceptions surface as `StorageBackendError` at the caller boundary.

**Example:**

```python
# Source: repo requirement ABS-03; exception chaining follows Python standard guidance
class StorageBackendError(RuntimeError):
    """Backend operation failed."""


def _wrap_storage_errors(fn):
    def inner(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except self._native_errors as exc:
            raise StorageBackendError(str(exc)) from exc
    return inner
```

### Pattern 4: Backend-Factory Test Parameterization

**What:** Add a shared fixture that yields backend instances by id (`sqlite`, `memory`) and run backend contract tests plus analytics parity tests through it.

**When to use:** For new Phase 6 backend parity tests.

**Why:** Current tests mix public analytics assertions with SQLite-private assertions. Split them instead of forcing every existing test to become backend-agnostic.

**Example:**

```python
# Source: https://docs.pytest.org/en/stable/how-to/parametrize.html
import pytest

from corpulse.backends import InMemoryBackend, SQLiteBackend


@pytest.fixture(params=["sqlite", "memory"], ids=["sqlite", "memory"])
def backend(request, tmp_path):
    if request.param == "sqlite":
        with SQLiteBackend(str(tmp_path / "test.db")) as db:
            yield db
    else:
        with InMemoryBackend() as db:
            yield db
```

### Anti-Patterns to Avoid

- **Leaking `sqlite3.Row` across the backend boundary:** This ties `core.py` to SQLite and makes InMemoryBackend unnatural.
- **Parameterizing current `_conn()`-based tests across all backends:** `InMemoryBackend` should not implement fake SQL internals just to satisfy private SQLite tests.
- **Changing SQLite connection strategy in Phase 6:** The current backend opens a connection per operation. Keeping that avoids new transaction and thread-safety behavior during a compatibility-focused refactor.
- **Letting `core.py` catch sqlite exceptions directly:** Error translation belongs in the backend layer.
- **Making `close()` destructive for in-memory state:** Phase 6 only requires lifecycle support, not disposal semantics. Keep it idempotent and unsurprising.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Backend interface checks | Custom ad-hoc duck typing | `abc.ABC` with explicit abstract methods | Clearer failures and easier future backend onboarding |
| Row contracts | Untyped dict conventions in comments | `TypedDict` definitions in `backends/base.py` | Captures the existing schema without runtime overhead |
| Backend lifecycle | Per-class bespoke `__enter__`/`__exit__` logic everywhere | One shared base implementation delegating to `close()` | Keeps lifecycle behavior consistent |
| Shared parity verification | Copy-pasted SQLite and memory tests | `pytest` parametrized backend contract fixture | Reduces drift and catches semantic mismatches early |

**Key insight:** The dangerous custom work here is not storage itself. It is inventing a second contract on top of the current one. The repo already has a de facto contract; make it explicit instead of redesigning it.

## Common Pitfalls

### Pitfall 1: Missing SQLite Upsert Semantics in InMemoryBackend

**What goes wrong:** In-memory updates overwrite `embedding_vec` or `embedded_at` with `None`, while SQLite currently preserves the prior value via `COALESCE`.

**Why it happens:** The SQL behavior is encoded in `ON CONFLICT ... COALESCE(...)` and is easy to forget when rewriting the logic imperatively.

**How to avoid:** Mirror the current SQLite rule exactly:

- `filename` always updates
- `embedding_vec` only updates when a non-`None` embedding is passed
- `embedded_at` only updates when a non-`None` timestamp is passed

**Warning signs:** Duplicate-detection or vector-capture tests start failing only on the in-memory backend.

### Pitfall 2: Over-Abstracting Around `_conn()`

**What goes wrong:** The plan tries to remove `_conn()` entirely in Phase 6 and rewrites too many existing tests at once.

**Why it happens:** `_conn()` is private, but current tests use it for SQLite-specific inspection.

**How to avoid:** Keep `_conn()` on `SQLiteBackend` for compatibility, but do not include it in `StorageBackend`.

**Warning signs:** Qdrant wrapper tests need major surgery before backend parity is even implemented.

### Pitfall 3: Silent Divergence in Aggregate Row Shapes

**What goes wrong:** `InMemoryBackend.retrieval_counts()` returns different keys or types than SQLite, such as omitting `avg_rank` / `avg_score` or returning integers where SQLite returns floats.

**Why it happens:** Only `cnt` is heavily used today, so the rest can look optional even though they are part of the implied interface.

**How to avoid:** Freeze the full row shape in `TypedDict`s and assert exact key sets in backend contract tests.

**Warning signs:** Analytics pass, but wrapper or future Postgres tests fail because row shape assumptions drift.

### Pitfall 4: Error Wrapping in the Wrong Layer

**What goes wrong:** `core.py` or tests start knowing about `sqlite3.Error`, or broad `Exception` wrapping hides caller mistakes unrelated to storage.

**Why it happens:** The requirement is easy to interpret too broadly.

**How to avoid:** Translate only backend-native failures inside backend public methods and initialization/close paths. Let caller misuse and analytics exceptions propagate normally.

**Warning signs:** `ValueError` from bad data or `KeyError` from malformed retrieval items gets misreported as `StorageBackendError`.

### Pitfall 5: Constructor Ambiguity Between `db_path` and `backend`

**What goes wrong:** `Corpulse(db_path="x", backend=InMemoryBackend())` silently ignores one input and becomes hard to reason about.

**Why it happens:** Backward compatibility pushes the old `db_path` parameter to stay, while the new backend injection adds a second source of truth.

**How to avoid:** Decide the policy in planning and document it. Recommended: if `backend` is provided, it is the authoritative storage object; reject conflicting non-default `db_path` with `ValueError`.

**Warning signs:** Tests or docs need caveats like "db_path is ignored when backend is set".

## Code Examples

Verified patterns from official sources and current repo behavior:

### SQLite Backend Error Boundary

```python
# Source: https://docs.python.org/3/library/sqlite3.html
import sqlite3
from contextlib import contextmanager


@contextmanager
def _conn(self):
    try:
        conn = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES)
    except sqlite3.Error as exc:
        raise StorageBackendError(str(exc)) from exc

    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except sqlite3.Error as exc:
        raise StorageBackendError(str(exc)) from exc
    finally:
        conn.close()
```

### In-Memory Retrieval Aggregation Matching SQLite Keys

```python
# Source: repo behavior in corpulse/core.py and corpulse/db.py
def retrieval_counts(self, since: float) -> list[RetrievalRow]:
    grouped: dict[str, list[dict]] = {}
    for row in self._retrievals:
        if row["retrieved_at"] >= since:
            grouped.setdefault(row["doc_id"], []).append(row)

    result: list[RetrievalRow] = []
    for doc_id, rows in grouped.items():
        result.append({
            "doc_id": doc_id,
            "cnt": len(rows),
            "avg_rank": sum(r["rank"] for r in rows) / len(rows),
            "avg_score": sum(r["score"] for r in rows) / len(rows),
        })
    return result
```

### Corpulse Constructor Wiring

```python
# Source: repo constructor in corpulse/core.py
class Corpulse:
    def __init__(self, db_path: str = "./corpulse.db", *,
                 backend: StorageBackend | None = None, ...):
        if backend is not None and db_path != "./corpulse.db":
            raise ValueError("Pass either db_path or backend, not both")
        self.db = backend or SQLiteBackend(db_path)

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "Corpulse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `core.py` directly imports `DB` from `corpulse.db` | `core.py` should depend on `StorageBackend` and default to `SQLiteBackend` | Phase 6 | Makes future Postgres backends possible without touching analytics logic again |
| SQLite returns `sqlite3.Row` objects implicitly | Backends should return explicit typed mapping rows | Phase 6 | Removes SQLite leakage and simplifies InMemory/Postgres parity |
| Tests couple analytics and SQLite internals | Split into backend-contract tests plus SQLite-specific tests | Phase 6 | Lowers refactor risk while still meeting shared-fixture requirement |

**Deprecated/outdated:**

- Directly treating `corpulse.db.DB` as the implementation location: keep it only as a compatibility alias.
- Treating the roadmap’s "39 tests" count as authoritative: the current repo passes 41 tests (`15 analytics + 16 qdrant wrapper + 2 docstrings + 4 import + 4 package`).

## Open Questions

1. **Should `Corpulse(db_path=..., backend=...)` raise or silently prefer `backend`?**
   - What we know: both inputs would configure storage; only one can actually be used.
   - What's unclear: user-facing policy is not specified in requirements.
   - Recommendation: raise on conflicting explicit inputs to avoid silent misconfiguration.

2. **How much of `tests/test_qdrant_wrapper.py` should be backend-agnostic in Phase 6?**
   - What we know: helper assertions currently use `corpulse.db._conn()` and direct SQL.
   - What's unclear: whether Phase 6 wants wrapper parity across memory immediately or only backend-contract parity.
   - Recommendation: keep wrapper tests SQLite-backed for now, add a separate shared contract suite for backend behavior.

3. **Should `close()` enforce a closed-state error on later backend use?**
   - What we know: the requirement only asks for `.close()` and context-manager support.
   - What's unclear: whether post-close usage should fail or remain a no-op/reopen.
   - Recommendation: keep `close()` idempotent and non-destructive in Phase 6; closed-state enforcement can be added later if required.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 9.0.2` |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/test_backend_contract.py tests/test_analytics.py -q` |
| Full suite command | `pytest tests -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ABS-01 | 8-method backend contract is enforced | unit | `pytest tests/test_backend_contract.py -q` | ❌ Wave 0 |
| ABS-02 | Shared row shapes match TypedDict contracts | unit | `pytest tests/test_backend_contract.py -q` | ❌ Wave 0 |
| ABS-03 | Native backend exceptions become `StorageBackendError` | unit | `pytest tests/test_backend_contract.py -q` | ❌ Wave 0 |
| ABS-04 | Shared fixture runs the same assertions against SQLite and memory | unit | `pytest tests/test_backend_contract.py -q` | ❌ Wave 0 |
| BACK-01 | SQLite backend preserves current behavior | regression | `pytest tests/test_analytics.py tests/test_qdrant_wrapper.py -q` | ✅ |
| BACK-02 | `corpulse.db.DB` compat import still works | smoke | `pytest tests/test_import.py tests/test_package.py -q` | ✅ |
| BACK-03 | In-memory backend matches analytics behavior without file I/O | regression | `pytest tests/test_backend_contract.py tests/test_analytics.py -q` | ❌ Wave 0 |
| BACK-06 | `.close()` and context manager work for all backends | unit | `pytest tests/test_backend_contract.py -q` | ❌ Wave 0 |
| INT-01 | `Corpulse(backend=...)` works and default constructor stays SQLite | regression | `pytest tests/test_analytics.py tests/test_qdrant_wrapper.py tests/test_backend_contract.py -q` | ❌ Partial |

### Sampling Rate

- **Per task commit:** `pytest tests/test_backend_contract.py -q`
- **Per wave merge:** `pytest tests/test_backend_contract.py tests/test_analytics.py tests/test_qdrant_wrapper.py -q`
- **Phase gate:** `pytest tests -q`

### Wave 0 Gaps

- [ ] `tests/conftest.py` — shared backend factory fixture for SQLite and in-memory
- [ ] `tests/test_backend_contract.py` — backend parity and error-boundary coverage for ABS-01/02/03/04 and BACK-03/06
- [ ] `tests/test_core_backend_integration.py` or equivalent additions — explicit `Corpulse(backend=...)` integration coverage for INT-01
- [ ] Qdrant wrapper helper refactor or explicit SQLite-only marker — current helpers depend on private `_conn()` on the default backend

## Sources

### Primary (HIGH confidence)

- Repository code:
  - `corpulse/db.py`
  - `corpulse/core.py`
  - `tests/test_analytics.py`
  - `tests/test_qdrant_wrapper.py`
  - `pyproject.toml`
- Python typing docs: https://docs.python.org/3/library/typing.html
  - Checked `TypedDict`, required keys, and mapping-shape guidance.
- Python sqlite3 docs: https://docs.python.org/3/library/sqlite3.html
  - Checked `sqlite3.Row`, `row_factory`, connection behavior, and sqlite exception types.
- pytest parametrization docs: https://docs.pytest.org/en/stable/how-to/parametrize.html
  - Checked fixture/test parameterization patterns suitable for shared backend tests.

### Secondary (MEDIUM confidence)

- Project planning docs:
  - `.planning/REQUIREMENTS.md`
  - `.planning/ROADMAP.md`
  - `.planning/PROJECT.md`
  - `.planning/STATE.md`

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - Phase 6 uses stdlib + already-installed pytest; no uncertain ecosystem dependency choice is needed.
- Architecture: HIGH - The repo already exposes the correct seam, and the main recommendations are direct consequences of current code/test coupling.
- Pitfalls: HIGH - All listed pitfalls are grounded in the current implementation, tests, or explicit phase requirements.

**Research date:** 2026-04-08
**Valid until:** 2026-05-08
