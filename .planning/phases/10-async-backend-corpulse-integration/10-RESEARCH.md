# Phase 10: Make Async Backend Usable From Corpulse - Research

**Researched:** 2026-04-09
**Domain:** Async facade integration for corpulse storage backends
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BACK-05 | AsyncPostgresBackend via asyncpg>=0.29 with async initialize() and connection pool | Keep `AsyncPostgresBackend` as the pooled async storage primitive, then add a supported async corpulse facade that actually awaits it end to end. |
| INT-03 | PostgresBackend and AsyncPostgresBackend support connection pooling | Sync pooling is already closed in Phase 9; Phase 10 must close the async half with deterministic pool-use tests plus a live async flow and matching verification artifacts. |
</phase_requirements>

## Summary

Phase 8 delivered a real `AsyncPostgresBackend`: lazy `asyncpg` loading, `create_pool()`, async CRUD methods, env-gated live round-trip coverage, and an `async_backend` fixture. Phase 9 then closed the sync pooling half of `INT-03`. The remaining gap is not storage capability. The gap is integration: [`Corpulse`](/Users/arkady/src/corpulse/corpulse/core.py) is still purely synchronous, so injecting [`AsyncPostgresBackend`](/Users/arkady/src/corpulse/corpulse/backends/postgres_async.py) into it creates unawaited coroutines instead of writes.

The smallest safe path is to add a parallel `AsyncCorpulse` facade and keep the existing sync `Corpulse` untouched. Do not retrofit coroutine detection into the sync facade, and do not call `asyncio.run()` or `run_until_complete()` inside `Corpulse`; official asyncio guidance forbids that inside an already-running event loop, which is exactly the async-service case this phase targets. A thin async facade can mirror the existing ingestion API, optionally mirror read/analysis methods where needed, and reuse the same helper logic and result shapes without destabilizing the sync codepath.

This phase is also partly evidence repair. Phase 8 has summary/UAT artifacts but still lacks `08-VERIFICATION.md`, and `08-VALIDATION.md` is still draft. Phase 10 needs to produce milestone-grade proof that the async backend is usable through a supported corpulse-facing API, then update traceability so `BACK-05` and the async half of `INT-03` close on verified behavior rather than code-only claims.

**Primary recommendation:** Add `AsyncCorpulse` as a thin, parallel async facade over `AsyncPostgresBackend`, verify it with deterministic and live async integration tests, and refresh Phase 8/10 planning artifacts so the milestone closes on evidence instead of reinterpretation.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncpg | 0.31.0 | Async PostgreSQL driver and native connection pool | Already implemented locally; official pool API matches the current backend design and satisfies the async half of `INT-03`. |
| asyncio | stdlib (Python >=3.10) | Event loop and async facade runtime | The integration problem is fundamentally an async boundary issue, not a new dependency problem. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | 1.3.0 | Async tests and async fixtures | Use for all async facade, async backend parity, and live async integration coverage. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `AsyncCorpulse` parallel facade | Make `Corpulse` auto-detect coroutine-returning backends | Brittle, silently changes sync semantics, and encourages forbidden nested loop patterns. |
| `AsyncCorpulse` parallel facade | `asyncio.run()` / `run_until_complete()` inside sync methods | Invalid inside a running event loop per official asyncio docs; wrong for FastAPI-style usage. |
| corpulse-facing async facade | Document direct `AsyncPostgresBackend` usage only | Does not satisfy the roadmap contract that the backend be usable through a corpulse integration path. |

**Installation:**
```bash
pip install "corpulse[postgres-async]"
```

**Version verification:**
```bash
python -m pip index versions asyncpg
python -m pip index versions pytest-asyncio
```

Verified on 2026-04-09 in this workspace:
- `asyncpg`: `0.31.0`
- `pytest-asyncio`: `1.3.0`

PyPI release pages show:
- `asyncpg 0.31.0` published 2025-11-24
- `pytest-asyncio 1.3.0` published 2025-11-10

## Architecture Patterns

### Recommended Project Structure
```text
corpulse/
├── core.py                    # existing sync Corpulse, unchanged API
├── async_core.py              # new AsyncCorpulse facade
└── backends/
    ├── postgres.py            # sync pooled backend (already verified)
    └── postgres_async.py      # async pooled backend (reuse as-is)

tests/
├── test_async_postgres_backend.py      # existing backend tests
├── test_async_core_integration.py      # new async facade end-to-end tests
├── test_async_backend_contract.py      # optional async parity/shape suite
└── test_import.py                      # export/lazy-import smoke tests
```

### Pattern 1: Parallel Async Facade, Not a Hybrid Sync Facade
**What:** Introduce `AsyncCorpulse` rather than mutating `Corpulse` to handle both sync and async backends.
**When to use:** Always for async-service integration in this milestone.
**Why:** The current sync facade directly calls backend methods without `await` ([`corpulse/core.py`](/Users/arkady/src/corpulse/corpulse/core.py#L122)). A local runtime check in this workspace confirms that injecting a coroutine-based backend produces `RuntimeWarning: coroutine ... was never awaited` and performs no writes.

**Example:**
```python
# Source: local code shape from corpulse/core.py plus asyncpg backend methods
class AsyncCorpulse:
    def __init__(
        self,
        backend,
        *,
        ghost_threshold_days: int = 30,
        duplicate_threshold: float = 0.92,
        stale_threshold_days: int = 14,
        obsolete_pattern: str = r"v\d+",
        top_k_report: int = 20,
    ):
        self.db = backend
        self.ghost_threshold_days = ghost_threshold_days
        self.duplicate_threshold = duplicate_threshold
        self.stale_threshold_days = stale_threshold_days
        self.obsolete_pattern = obsolete_pattern
        self.top_k_report = top_k_report

    async def log_retrieval(self, results: list[dict[str, Any]], query: str = "") -> None:
        qhash = _hash_query(query)
        ts = _now()
        for rank, item in enumerate(results, start=1):
            vec = item.get("embedding")
            await self.db.upsert_document(
                doc_id=item["doc_id"],
                filename=item.get("filename", item["doc_id"]),
                embedding=_vec_to_bytes(vec) if vec is not None else None,
                embedded_at=ts if vec is not None else None,
            )
            await self.db.insert_retrieval(item["doc_id"], qhash, rank, float(item.get("score", 0.0)), ts)
```

### Pattern 2: Share Pure Helpers, Duplicate Only the Await Boundary
**What:** Reuse `_hash_query`, `_days_ago`, `_vec_to_bytes`, `_bytes_to_vec`, and the existing analysis math where practical. Only duplicate method shells where `await` is required.
**When to use:** For `log_retrieval`, `log_engagement`, `log_source_update`, `register_document`, and any analysis methods brought into async scope.
**Why:** The logic is already stable; the real risk is the async boundary, not the analytics formulas.

### Pattern 3: Narrow the Phase 10 Surface to What the Roadmap Actually Needs
**What:** Implement the smallest async facade surface that proves end-to-end usage without reopening the full deferred `ASYNC-01/02` milestone.
**When to use:** Planning scope.
**Recommendation:** Minimum safe Phase 10 surface:
- `AsyncCorpulse.__init__(backend=...)`
- `async log_retrieval`
- `async log_engagement`
- `async log_source_update`
- `async register_document`
- `async close`, `__aenter__`, `__aexit__`
- At least one async read/analysis path used in verification, preferably `async get_ghosts`

Anything beyond that should be added only if the planner needs it to make the verified async flow credible.

### Pattern 4: Mirror Phase 9’s Deterministic-plus-Live Verification Split
**What:** Keep fake-driver deterministic tests for pool semantics and add a live async round-trip gated on `CORPULSE_POSTGRES_TEST_CONNINFO`.
**When to use:** All verification planning.
**Why:** This is already how sync Postgres was closed successfully. Reuse the evidence shape rather than inventing a new standard.

### Anti-Patterns to Avoid
- **Do not inject `AsyncPostgresBackend` into the existing sync `Corpulse`:** it returns unawaited coroutines and silently drops writes.
- **Do not call `asyncio.run()` or `loop.run_until_complete()` inside sync facade methods:** official docs say `asyncio.run()` cannot be called when another event loop is already running.
- **Do not change `Corpulse` constructor semantics for sync users:** the existing SQLite and sync Postgres paths are already verified.
- **Do not close `BACK-05` on backend-only tests:** Phase 10 must prove a corpulse-facing async flow, not just direct backend CRUD.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sync/async auto-bridge in one facade | Coroutine detection, nested event-loop helpers, thread-executor shims inside `Corpulse` | Separate `AsyncCorpulse` facade | Cleaner API boundary and no invalid loop nesting. |
| Async pooling | Custom queue/pool wrapper | `asyncpg.create_pool()` already in [`postgres_async.py`](/Users/arkady/src/corpulse/corpulse/backends/postgres_async.py) | The pooled backend is already implemented and tested. |
| Async fixture orchestration | Bespoke harness outside pytest | `pytest-asyncio` async fixtures plus env gating | Already present in [`tests/conftest.py`](/Users/arkady/src/corpulse/tests/conftest.py#L65). |
| Milestone evidence repair | Ad hoc notes in summaries only | Proper `08-VERIFICATION.md`, `10-VERIFICATION.md`, and traceability updates | The audit gap is explicitly about missing verification artifacts. |

**Key insight:** The missing capability is not async PostgreSQL access. The missing capability is a supported, awaited corpulse-facing API boundary.

## Common Pitfalls

### Pitfall 1: Treating `AsyncPostgresBackend` as Drop-In for `Corpulse`
**What goes wrong:** [`Corpulse.log_retrieval`](/Users/arkady/src/corpulse/corpulse/core.py#L122) calls `self.db.upsert_document(...)` and `self.db.insert_retrieval(...)` directly. With an async backend, those return coroutines that are never awaited.
**Why it happens:** The method names match, so the object looks injectable even though the call contract differs.
**How to avoid:** Introduce `AsyncCorpulse` and type/document it as the supported path for `AsyncPostgresBackend`.
**Warning signs:** Runtime warnings about unawaited coroutines; no rows written after an apparent success path.

### Pitfall 2: Over-Correcting by Making Sync `Corpulse` Magic
**What goes wrong:** Plans to detect coroutines inside sync methods usually end in `asyncio.run()` or loop juggling.
**Why it happens:** It looks like the smallest patch, but it violates asyncio usage rules in async apps.
**How to avoid:** Keep sync and async facades explicit.
**Warning signs:** Any proposal mentioning `asyncio.run()`, `run_until_complete()`, or hidden executor bridges inside `Corpulse`.

### Pitfall 3: Closing `BACK-05` Without a Corpulse-Facing Async Test
**What goes wrong:** The backend suite passes, but the roadmap contract remains unproven.
**Why it happens:** Phase 8 already has good backend coverage, so it is easy to mistake that for integration coverage.
**How to avoid:** Add at least one async corpulse end-to-end test file that exercises facade writes and a facade read/assertion.
**Warning signs:** Verification commands mention only `tests/test_async_postgres_backend.py`.

### Pitfall 4: Forgetting the Artifact Repair Work
**What goes wrong:** Code and tests land, but milestone audit still fails because Phase 8 is missing `08-VERIFICATION.md` and still has draft validation metadata.
**Why it happens:** The code fix feels like the hard part, but the audit gap is partly documentation-state drift.
**How to avoid:** Plan explicit tasks for verification artifact creation and traceability updates.
**Warning signs:** `BACK-05` still marked pending after green tests.

## Code Examples

Verified patterns from local code and official docs:

### Async Pool Creation
```python
# Source: asyncpg API docs + corpulse/backends/postgres_async.py
pool = await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)
async with pool.acquire() as conn:
    async with conn.transaction():
        await conn.execute("INSERT ...", arg1, arg2)
```

### Async Facade Context Manager
```python
# Source: mirror current Corpulse lifecycle plus async backend close
class AsyncCorpulse:
    async def close(self) -> None:
        await self.db.close()

    async def __aenter__(self) -> "AsyncCorpulse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
```

### Minimal Verified Flow to Close the Audit Gap
```python
# Source: recommended new integration test shape
backend = await AsyncPostgresBackend.create(os.environ["CORPULSE_POSTGRES_TEST_CONNINFO"])
async with AsyncCorpulse(backend=backend) as corpulse:
    await corpulse.log_retrieval(
        [{"doc_id": "ghost", "filename": "ghost.md", "score": 0.2}],
        query="status",
    )
    assert await corpulse.get_ghosts() == []
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Treat async backend as if matching sync interface by name alone | Use explicit sync and async facades | Already reflected in current Python async ecosystem and this repo’s own async backend design | Prevents silent coroutine loss and keeps APIs honest. |
| Single sync Postgres connection | `psycopg_pool.ConnectionPool` in sync backend | Phase 9, verified 2026-04-09 | Sync half of `INT-03` is already closed. |
| Backend-only async proof | Backend proof plus async corpulse-facing integration proof | Required by Phase 10 roadmap and milestone audit | Closes `BACK-05` with evidence instead of code-only claims. |

**Deprecated/outdated:**
- `Corpulse(backend=await AsyncPostgresBackend.create(...))` using the current sync `Corpulse`: outdated and demonstrably broken against the present codebase.

## Open Questions

1. **How much async analytics surface should Phase 10 include?**
   - What we know: Ingestion methods must be async. The roadmap only says the backend must be usable through a corpulse integration path and proven end to end.
   - What's unclear: Whether full async parity for all analysis/report methods is required now or can stay for v2.
   - Recommendation: Keep Phase 10 narrow. Implement the ingestion methods plus the smallest async read path needed for credible verification, and defer full async analytics unless planning reveals a hard dependency.

2. **Should `AsyncCorpulse` be exported from `corpulse.__init__` now?**
   - What we know: `Corpulse` is exported from the package root; discoverability matters.
   - What's unclear: Whether root export is required for contract consistency or whether `corpulse.async_core.AsyncCorpulse` is enough.
   - Recommendation: Export it from the package root if the import remains dependency-free. That keeps the public story simple without changing sync behavior.

3. **Does Phase 10 need a separate async backend contract suite, or is a focused integration suite enough?**
   - What we know: [`tests/conftest.py`](/Users/arkady/src/corpulse/tests/conftest.py#L65) already exposes `async_backend`, and [`tests/test_async_postgres_backend.py`](/Users/arkady/src/corpulse/tests/test_async_postgres_backend.py#L321) already covers direct live CRUD.
   - What's unclear: Whether another async parity file adds enough signal beyond the corpulse-facing integration tests.
   - Recommendation: Prefer one focused `test_async_core_integration.py` file unless the planner needs extra parity coverage to keep assertions reusable and clean.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest 8.x` + `pytest-asyncio 1.3.0` |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/test_async_postgres_backend.py tests/test_async_core_integration.py tests/test_import.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BACK-05 | Async backend is usable through a supported corpulse-facing async path | integration | `pytest tests/test_async_core_integration.py -q` | ❌ Wave 0 |
| BACK-05 | Live async corpulse flow works against real Postgres | integration | `CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://... pytest tests/test_async_core_integration.py -q` | ❌ Wave 0 |
| INT-03 | Async backend actually uses pooled acquire/close behavior | unit | `pytest tests/test_async_postgres_backend.py::test_async_postgres_backend_uses_pool_acquire -q` | ✅ |
| INT-03 | Async pooled path remains wired through shared async fixture or equivalent | integration | `pytest tests/test_async_postgres_backend.py::test_live_async_postgres_backend_round_trip -q` | ✅ |
| BACK-05 | Package/import path exposes async facade without eager optional-driver import | unit | `pytest tests/test_import.py -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_async_postgres_backend.py tests/test_async_core_integration.py tests/test_import.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green plus live async command green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_async_core_integration.py` — corpulse-facing async flow and facade lifecycle
- [ ] `corpulse/async_core.py` — new async facade implementation
- [ ] `corpulse/__init__.py` update — optional root export for `AsyncCorpulse`
- [ ] `.planning/phases/08-asyncpostgresbackend/08-VERIFICATION.md` — missing verification artifact
- [ ] `.planning/phases/08-asyncpostgresbackend/08-VALIDATION.md` — update from draft / `nyquist_compliant: false`
- [ ] `.planning/phases/10-async-backend-corpulse-integration/10-VERIFICATION.md` — phase-level async integration evidence

## Sources

### Primary (HIGH confidence)
- Local code inspection:
  - `/Users/arkady/src/corpulse/corpulse/core.py` - sync facade directly calls backend methods
  - `/Users/arkady/src/corpulse/corpulse/backends/postgres_async.py` - current async pool-backed backend implementation
  - `/Users/arkady/src/corpulse/tests/conftest.py` - env-gated async fixture
  - `/Users/arkady/src/corpulse/tests/test_async_postgres_backend.py` - deterministic and live async backend coverage
  - `/Users/arkady/src/corpulse/tests/test_postgres_backend.py` - sync deterministic/live verification pattern to mirror
  - `/Users/arkady/src/corpulse/.planning/ROADMAP.md` - current Phase 10 contract
  - `/Users/arkady/src/corpulse/.planning/v1.1-v1.1-MILESTONE-AUDIT.md` - exact gap statements
- asyncpg official docs: https://magicstack.github.io/asyncpg/current/api/ - pool acquire/release semantics and `create_pool()`
- Python asyncio docs: https://docs.python.org/3.11/library/asyncio-runner.html - `asyncio.run()` cannot be called when another event loop is running

### Secondary (MEDIUM confidence)
- PyPI asyncpg release page: https://pypi.org/project/asyncpg/ - current release series and publication date
- PyPI pytest-asyncio release page: https://pypi.org/project/pytest-asyncio/ - current release series and publication date

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - almost all claims come from current local code, official docs, and verified package indexes.
- Architecture: HIGH - driven directly by the current sync/async boundary in the repo plus a local runtime reproduction of the unawaited-coroutine failure.
- Pitfalls: HIGH - each pitfall is grounded in current code behavior or the milestone audit.

**Research date:** 2026-04-09
**Valid until:** 2026-05-09
