# Phase 14: Docs and Examples - Research

**Researched:** 2026-04-12
**Domain:** Python docstrings, README authoring, runnable async demo script
**Confidence:** HIGH

## Summary

Phase 14 is a pure documentation and example phase with no new library functionality. All three requirements map directly to file edits: README insertion, docstring additions to `corpulse/async_core.py`, and a new `examples/` script. The codebase is already complete — `AsyncCorpulse.to_dataframe()`, `report()`, and `cleanup_report()` exist and return structured payloads that are ready to demonstrate.

The only non-obvious engineering decision is the example script's backend choice. The success criteria mandate `InMemoryBackend` as the default, but `InMemoryBackend` is a synchronous backend — all its methods are sync, and `AsyncCorpulse` awaits every backend call. Passing `InMemoryBackend` directly to `AsyncCorpulse` raises `TypeError: 'NoneType' can't be awaited` at runtime. [VERIFIED: manual test in session] The example script therefore needs a thin async wrapper (`AsyncInMemoryBackend`) that delegates to `InMemoryBackend` using `async def` methods. This wrapper can live inline in the example script (no changes to the installed library needed).

The README already has solid structure and two quickstart sections (Manual API, Qdrant Wrapper). The async section slots naturally after those, following the same pattern: a short motivating code snippet for ingestion, analysis, and the two report methods.

**Primary recommendation:** Write `examples/async-demo/demo.py` with an inline `AsyncInMemoryBackend` adapter, follow the manual-api demo's structure for README snippets, and add Google-style docstrings to the three `AsyncCorpulse` methods matching the existing sync `Corpulse` docstring style.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ASYNC-DOC-01 | README gains a first-class "Async usage" section showing `AsyncCorpulse` over `AsyncPostgresBackend`, including ingestion, analysis, and the new structured report methods | README structure understood; async section slots after existing quickstarts; code snippets for `log_retrieval`, `log_engagement`, `to_dataframe`, `report`, `cleanup_report` are straightforward from `async_core.py` |
| ASYNC-DOC-02 | Docstrings on all new `AsyncCorpulse` methods meet API-reference quality (args, returns, raises, parity notes vs sync) | Three methods (`to_dataframe`, `report`, `cleanup_report`) currently have no docstrings; sync equivalents in `core.py` lines 647–780 provide the parity reference text; existing test in `test_docstrings.py` covers sync only — no new test required by this requirement |
| ASYNC-DOC-03 | `examples/` contains a runnable async script demonstrating ingest → analysis → report end-to-end against `InMemoryBackend` (or async Postgres if DSN is set) | `InMemoryBackend` is sync-only; `AsyncCorpulse` awaits every backend call; an inline `AsyncInMemoryBackend` wrapper resolves this without touching the library; optional Postgres branch via `CORPULSE_POSTGRES_TEST_CONNINFO` is feasible |
</phase_requirements>

## Standard Stack

### Core (no new dependencies)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| Python stdlib `asyncio` | 3.10+ | `asyncio.run()` entry point for example script | Already required by project |
| `corpulse.AsyncCorpulse` | in-repo | Subject of documentation and demo | Already implemented |
| `corpulse.backends.InMemoryBackend` | in-repo | Sync backend to wrap for the demo | Sync-only; needs async wrapper in script |
| `corpulse.backends.AsyncPostgresBackend` | in-repo | Optional live Postgres path in demo | Env-gated via `CORPULSE_POSTGRES_TEST_CONNINFO` |

[VERIFIED: codebase inspection]

**No new `pip install` dependencies for this phase.** `numpy` is already a core dependency and is used by the existing demos for vector generation.

## Architecture Patterns

### Recommended Project Structure
```
examples/
├── manual-api/      # existing sync demo
├── qdrant-wrapper/  # existing Qdrant demo
└── async-demo/      # new — Phase 14
    ├── demo.py      # runnable async script
    └── README.md    # brief prerequisites note (optional)
```

### Pattern 1: Inline AsyncInMemoryBackend adapter
**What:** A local class inside `examples/async-demo/demo.py` that wraps `InMemoryBackend` and exposes every method as `async def`. This requires no changes to the library and keeps the example self-contained.

**When to use:** Any time the example script runs without an external database. This is the default code path.

**Example:**
```python
# Source: manual validation in session — this pattern works on Python 3.14 / asyncio
from corpulse.backends.memory import InMemoryBackend

class AsyncInMemoryBackend:
    """Thin async wrapper around InMemoryBackend for use in examples."""

    def __init__(self):
        self._backend = InMemoryBackend()

    async def upsert_document(self, doc_id, filename, embedding=None, embedded_at=None):
        return self._backend.upsert_document(doc_id, filename, embedding, embedded_at)

    async def insert_retrieval(self, doc_id, query_hash, rank, score, retrieved_at):
        return self._backend.insert_retrieval(doc_id, query_hash, rank, score, retrieved_at)

    async def insert_engagement(self, doc_id, event_type, engaged_at):
        return self._backend.insert_engagement(doc_id, event_type, engaged_at)

    async def update_source_timestamp(self, doc_id, updated_at):
        return self._backend.update_source_timestamp(doc_id, updated_at)

    async def all_documents(self):
        return self._backend.all_documents()

    async def retrieval_counts(self, since):
        return self._backend.retrieval_counts(since)

    async def engagement_counts(self, since):
        return self._backend.engagement_counts(since)

    async def all_embeddings(self):
        return self._backend.all_embeddings()

    async def close(self):
        return self._backend.close()
```

### Pattern 2: Optional Postgres path in the demo
**What:** If `CORPULSE_POSTGRES_TEST_CONNINFO` is set, use `AsyncPostgresBackend.create(dsn)` instead. The requirement says "or an async Postgres instance if `CORPULSE_POSTGRES_TEST_CONNINFO` is set."

**Example:**
```python
import os, asyncio
from corpulse import AsyncCorpulse
from corpulse.backends import AsyncPostgresBackend

async def main():
    dsn = os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")
    if dsn:
        backend = await AsyncPostgresBackend.create(dsn)
    else:
        backend = AsyncInMemoryBackend()  # defined inline

    async with AsyncCorpulse(backend=backend, ghost_threshold_days=30) as corp:
        # ingest → analysis → report
        ...
```

### Pattern 3: Docstring style — match existing sync docstrings
**What:** The sync `Corpulse` methods in `core.py` use Google-style docstrings with `Args:`, `Returns:`, and `Raises:` sections. [VERIFIED: read core.py lines 647–780]

**Parity notes** are required by ASYNC-DOC-02 to call out the structural difference: async methods return `dict` instead of printing.

**Example template for `to_dataframe`:**
```python
async def to_dataframe(self, window_days: int | None = None):
    """Return corpus stats as a pandas DataFrame.

    Async equivalent of :meth:`Corpulse.to_dataframe`. Retrieval and
    engagement counts are fetched from the async backend before building
    the DataFrame.

    Args:
        window_days: Lookback window in days for retrieval/engagement
            counts. Defaults to ``ghost_threshold_days`` if ``None``.

    Returns:
        pandas.DataFrame with columns: ``doc_id``, ``filename``,
        ``retrievals``, ``engagements``, ``engagement_rate``, ``status``.
        Sorted by retrievals descending.

    Raises:
        RuntimeError: If pandas is not installed
            (``pip install pandas`` to resolve).
    """
```

**Example template for `report`:**
```python
async def report(self, window_days: int | None = None) -> dict[str, Any]:
    """Return a structured corpus health payload.

    Unlike sync :meth:`Corpulse.report` which prints to stdout, this method
    returns the payload as a dict so callers can format, log, or forward it.

    Args:
        window_days: Lookback window in days for retrieval and engagement
            counts. Defaults to ``ghost_threshold_days`` if ``None``.

    Returns:
        dict with keys:

        - ``"summary"`` (:class:`dict`) — corpus-level health metrics
          (total docs, noise estimate, bloat warning, recommendation).
        - ``"rows"`` (:class:`list[dict]`) — top-K document rows with
          ``doc_id``, ``filename``, ``retrievals``, ``engagements``,
          ``engagement_rate``, and ``status`` fields.
    """
```

**Example template for `cleanup_report`:**
```python
async def cleanup_report(self) -> dict[str, Any]:
    """Return a structured cleanup action payload.

    Unlike sync :meth:`Corpulse.cleanup_report` which prints to stdout, this
    method returns the payload as a dict.

    Returns:
        dict with keys:

        - ``"total_docs"`` (:class:`int`)
        - ``"noise_pct"`` (:class:`float`) — estimated noisy document fraction.
        - ``"bloat_warning"`` (:class:`bool`)
        - ``"recommendation"`` (:class:`str`)
        - ``"ghost_threshold_days"`` (:class:`int`)
        - ``"ghosts"`` (:class:`dict`) — ``count``, ``top5``, ``overflow``.
        - ``"obsolete"`` (:class:`dict`) — ``count``, ``top5``, ``overflow``.
        - ``"stale"`` (:class:`dict`) — ``count``, ``top5``, ``overflow``.
        - ``"suspects"`` (:class:`dict`) — ``count``, ``top5``, ``overflow``.
    """
```

### Pattern 4: README "Async usage" section placement and content
**What:** The README currently has: Problem → What it is → Installation → Quickstart: Manual API → Quickstart: Qdrant Wrapper → What It Measures → Configuration → Analysis Methods → License.

The async section logically follows the two quickstarts and precedes "What It Measures." It should show `AsyncCorpulse` over `AsyncPostgresBackend` (as the requirement specifies for the README — the example script uses `InMemoryBackend`) with concrete snippets for ingestion, analysis, and the structured report methods.

**Snippet coverage required by ASYNC-DOC-01:**
1. Ingestion: `register_document` or `log_retrieval` + `log_engagement`
2. Analysis (at least one method, e.g., `get_ghosts()`)
3. Structured report: `report()` dict access and `cleanup_report()` dict access

**Anti-Patterns to Avoid**
- Passing sync `InMemoryBackend` directly to `AsyncCorpulse` — raises `TypeError` at runtime [VERIFIED: session test]
- Hard-coding `pandas` import at top-level in the example script — pandas is optional; must be guarded or the script must only call `to_dataframe()` inside a try/except
- Printing `to_dataframe()` result in the demo without a pandas install — the success criteria says "visible proof of the report payload"; `report()` and `cleanup_report()` both return dicts and don't require pandas
- Placing the async README section after "License" — breaks reading flow

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Docstring completeness testing | Custom AST checker | Extend existing `test_docstrings.py` if needed | Project already has the pattern |
| Async wrapper with thread executor | `asyncio.run_in_executor` | Simple `async def` delegating sync method | No blocking I/O; in-memory ops are instantaneous |
| Payload description in docs | Prose description | Point to `_build_report_rows` / `_build_cleanup_payload` return shapes from `core.py` | Ground truth is the payload builders |

## Common Pitfalls

### Pitfall 1: InMemoryBackend is synchronous
**What goes wrong:** `AsyncCorpulse` awaits every backend call. `InMemoryBackend.upsert_document()` returns `None` (sync), so `await backend.upsert_document(...)` raises `TypeError: object NoneType can't be used in 'await' expression`.
**Why it happens:** `InMemoryBackend` extends `StorageBackend` (sync ABC). `AsyncPostgresBackend` is a separate class with `async def` methods — it does not extend the same ABC.
**How to avoid:** Define `AsyncInMemoryBackend` (inline wrapper) in the example script. All eight backend interface methods must be declared `async def`.
**Warning signs:** Script raises `TypeError` on first `await` call at `log_retrieval` or `register_document`.

### Pitfall 2: pandas optional dependency in demo
**What goes wrong:** `to_dataframe()` raises `RuntimeError` if pandas is not installed. If the demo calls it unconditionally it will fail for users who haven't installed pandas.
**Why it happens:** pandas is intentionally kept as an optional extra (locked project decision).
**How to avoid:** Either (a) skip `to_dataframe()` in the default demo path and rely on `report()` + `cleanup_report()` for visible output (both always available), or (b) wrap the call in try/except and print a clear message. Option (a) is cleaner since the success criteria phrase "visible proof of the report payload" is satisfied by printing the `report()` dict.

### Pitfall 3: `AsyncCorpulse` constructor parameter name
**What goes wrong:** README or example uses `Corpulse(db_path=...)` pattern but `AsyncCorpulse(backend=...)` requires an explicit backend object.
**Why it happens:** `Corpulse` defaults to SQLite at `./corpulse.db`; `AsyncCorpulse` has no default backend — it always requires one.
**How to avoid:** README async snippet must show backend construction explicitly before passing it to `AsyncCorpulse`.

### Pitfall 4: `async with` context manager scope
**What goes wrong:** Calling `await corp.close()` after the context manager exits (double-close), or forgetting `close()` outside `async with`.
**Why it happens:** `AsyncCorpulse.__aenter__`/`__aexit__` delegates to `self.db.close()`.
**How to avoid:** Example script uses `async with AsyncCorpulse(backend=backend) as corp:` — the idiomatic pattern shown by the test suite.

### Pitfall 5: `AsyncPostgresBackend` must be created via classmethod
**What goes wrong:** `AsyncPostgresBackend(dsn)` raises `TypeError` — the constructor takes `(pool, error_cls)`.
**Why it happens:** `AsyncPostgresBackend` uses an async factory classmethod `create(dsn)` to set up the connection pool.
**How to avoid:** README and demo must use `backend = await AsyncPostgresBackend.create(dsn)` — not the bare constructor.

## Code Examples

Verified patterns from codebase:

### Full async ingest → analysis → report round trip
```python
# Source: verified against async_core.py + manual execution in session
import asyncio, os, pprint
from corpulse import AsyncCorpulse
from corpulse.backends import AsyncPostgresBackend
from corpulse.backends.memory import InMemoryBackend


class AsyncInMemoryBackend:
    """Thin async shim so InMemoryBackend works with AsyncCorpulse."""
    def __init__(self):
        self._b = InMemoryBackend()
    async def upsert_document(self, *a, **kw): return self._b.upsert_document(*a, **kw)
    async def insert_retrieval(self, *a, **kw): return self._b.insert_retrieval(*a, **kw)
    async def insert_engagement(self, *a, **kw): return self._b.insert_engagement(*a, **kw)
    async def update_source_timestamp(self, *a, **kw): return self._b.update_source_timestamp(*a, **kw)
    async def all_documents(self): return self._b.all_documents()
    async def retrieval_counts(self, since): return self._b.retrieval_counts(since)
    async def engagement_counts(self, since): return self._b.engagement_counts(since)
    async def all_embeddings(self): return self._b.all_embeddings()
    async def close(self): return self._b.close()


async def main():
    dsn = os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")
    backend = await AsyncPostgresBackend.create(dsn) if dsn else AsyncInMemoryBackend()

    async with AsyncCorpulse(backend=backend, ghost_threshold_days=30) as corp:
        # Ingest
        await corp.register_document("doc-1", "guide.md")
        await corp.log_retrieval(
            [{"doc_id": "doc-1", "filename": "guide.md", "score": 0.91}],
            query="how to install?",
        )
        await corp.log_engagement("doc-1", event="opened")

        # Analysis
        ghosts = await corp.get_ghosts()
        print(f"Ghosts: {ghosts}")

        # Structured reports
        report = await corp.report(window_days=30)
        pprint.pprint(report)

        cleanup = await corp.cleanup_report()
        pprint.pprint(cleanup)


asyncio.run(main())
```

### README async section snippet (AsyncPostgresBackend path)
```python
# Source: async_core.py constructor + AsyncPostgresBackend.create() classmethod
import asyncio
from corpulse import AsyncCorpulse
from corpulse.backends import AsyncPostgresBackend

async def main():
    backend = await AsyncPostgresBackend.create(
        "postgresql://user:pass@localhost/mydb"
    )
    async with AsyncCorpulse(backend=backend) as corp:
        # Ingest: called after every vector DB query in your RAG pipeline
        await corp.log_retrieval(
            [{"doc_id": "abc123", "filename": "guide.md", "score": 0.91}],
            query="how to install?",
        )
        await corp.log_engagement("abc123", event="opened")

        # Analysis
        ghosts = await corp.get_ghosts()

        # Structured reports (returns dict, does not print)
        report = await corp.report(window_days=30)
        print(report["summary"])
        print(report["rows"][:3])

        cleanup = await corp.cleanup_report()
        print(cleanup["ghosts"])

asyncio.run(main())
```

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|-----------------|-------|
| Sync `report()` prints to stdout | `AsyncCorpulse.report()` returns `dict` | Structural difference; parity note required in docstring |
| `Corpulse(db_path=...)` auto-creates SQLite | `AsyncCorpulse(backend=...)` always explicit | Must be shown clearly in README snippet |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | An inline `AsyncInMemoryBackend` in the example script (not a library change) satisfies "runs against InMemoryBackend" in the success criteria | Architecture Patterns (Pattern 1) | Low — the success criteria says "no external dependencies required"; an inline wrapper fulfills this. If the planner interprets it as "use InMemoryBackend directly", the task is impossible without a library change. |
| A2 | The example script lives at `examples/async-demo/demo.py` (a new subdirectory matching the existing pattern) | Recommended Project Structure | Low — existing examples each use a subdirectory; if the planner chooses a flat file instead, the plan simply changes the path |
| A3 | No new test file is required for ASYNC-DOC-02 (docstring completeness) — the existing `test_docstrings.py` only covers sync `Corpulse`, and the requirement does not mention adding coverage | Common Pitfalls | Medium — the planner may choose to extend `test_docstrings.py` to cover `AsyncCorpulse` methods; this would be a good defensive addition but is not explicitly required |

## Open Questions

1. **Should `test_docstrings.py` be extended to cover `AsyncCorpulse`?**
   - What we know: `test_docstrings.py` currently only checks `Corpulse` in `core.py`. ASYNC-DOC-02 requires docstring quality but does not specify automated coverage.
   - What's unclear: Whether the planner should add a complementary `test_async_docstrings.py` or extend the existing file.
   - Recommendation: Add coverage in a Wave 0 task to prevent future regressions. Extending `test_docstrings.py` is one clean option.

2. **Should `AsyncInMemoryBackend` live in the library or only in the example?**
   - What we know: No `AsyncInMemoryBackend` exists in `corpulse/backends/`. Putting it in the library would make it easier to test `AsyncCorpulse` without asyncpg. However, the phase scope is docs and examples only.
   - What's unclear: Whether the planner wants to avoid a library change entirely.
   - Recommendation: Keep it inline in the example script for this phase. A library-level `AsyncInMemoryBackend` is a future-phase concern.

## Environment Availability

Step 2.6: External dependencies for this phase are all in-repo. No new tools, services, or CLIs are required. The example script runs `python examples/async-demo/demo.py` using the installed package and stdlib only.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | asyncio, async/await | ✓ | 3.14.3 | — |
| numpy | Vector generation in demo | ✓ | installed (core dep) | — |
| pandas | `to_dataframe()` call in demo | optional | unknown | Skip `to_dataframe()` call, use `report()` dict instead |
| asyncpg | Optional Postgres path in demo | optional | unknown | Default InMemoryBackend path |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:**
- pandas: demo can avoid calling `to_dataframe()` in the default path
- asyncpg: demo defaults to `AsyncInMemoryBackend` when DSN absent

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | pyproject.toml (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/ -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ASYNC-DOC-01 | README contains async usage section | manual/smoke | `python -c "import pathlib; txt=pathlib.Path('README.md').read_text(); assert 'Async usage' in txt"` | ❌ Wave 0 (inline check) |
| ASYNC-DOC-02 | `AsyncCorpulse` methods have docstrings | unit | `pytest tests/test_docstrings.py -q` or extended version | ✅ exists (sync only) — extension needed |
| ASYNC-DOC-03 | Example script runs to completion | smoke | `python examples/async-demo/demo.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -q`
- **Per wave merge:** `pytest tests/ -q && python examples/async-demo/demo.py`
- **Phase gate:** Full suite green plus example script exits 0 before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `examples/async-demo/demo.py` — covers ASYNC-DOC-03
- [ ] Extension of `tests/test_docstrings.py` (or new `tests/test_async_docstrings.py`) — covers ASYNC-DOC-02

## Security Domain

This phase makes no changes to authentication, session management, access control, cryptography, or data storage logic. It adds docstrings and a demo script that uses already-existing public API calls.

The demo script uses `os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")` to optionally read a DSN — the same env-gate already established in phases 12–13. No credentials are hard-coded. [VERIFIED: existing conftest.py pattern]

Security enforcement: no ASVS categories apply to documentation and example additions.

## Sources

### Primary (HIGH confidence)
- `corpulse/async_core.py` — full `AsyncCorpulse` implementation, all three target methods
- `corpulse/core.py` lines 647–780 — sync docstring style and parity reference
- `corpulse/backends/memory.py` — confirmed sync-only (no `async def`)
- `corpulse/backends/__init__.py` — `AsyncPostgresBackend` lazy import pattern
- `tests/test_docstrings.py` — existing docstring coverage scope (sync `Corpulse` only)
- `examples/manual-api/demo.py` — demo script structure and style reference
- Manual asyncio test (session) — confirmed `InMemoryBackend` fails with `TypeError` when awaited; confirmed `AsyncInMemoryBackend` wrapper resolves this

### Secondary (MEDIUM confidence)
- `pyproject.toml` — pandas is not listed as a core or dev dependency; confirms optional nature

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components are in-repo and verified
- Architecture: HIGH — `InMemoryBackend` sync limitation is verified by direct execution
- Pitfalls: HIGH — most found by direct code inspection or execution
- Docstring style: HIGH — synced from existing `core.py` docstrings

**Research date:** 2026-04-12
**Valid until:** Stable — no external ecosystem dependencies; valid until codebase changes
