# Phase 7: PostgresBackend (Sync) - Research

**Researched:** 2026-04-09
**Domain:** Sync PostgreSQL storage backend for corpulse via psycopg 3
**Confidence:** MEDIUM-HIGH

## User Constraints

No phase-specific `CONTEXT.md` exists for Phase 7.

Locked constraints from the roadmap, requirements, and current codebase:

- Address only `BACK-04` and the Phase 7 portion of `INT-02`.
- Keep `Corpulse()` defaulting to SQLite exactly as it does now.
- Do not require `psycopg` at `import corpulse` time.
- Match the existing `StorageBackend` 8-method contract from `corpulse/backends/base.py`.
- Preserve the analytics-facing row shapes already used by `corpulse/core.py`.
- Use schema auto-initialization only; schema migrations remain out of scope.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BACK-04 | PostgresBackend (sync) via psycopg>=3.2 with schema auto-init | Implement a concrete backend with the same public methods as SQLite/InMemory, using PostgreSQL `CREATE TABLE IF NOT EXISTS`, `BYTEA`, and `ON CONFLICT` upserts. |
| INT-02 | `pyproject.toml` extras include `[postgres]` | Add a `[postgres]` extra using `psycopg>=3.2`; as a library dependency, prefer `psycopg` itself instead of forcing `psycopg[binary]`. |

</phase_requirements>

## Summary

Phase 7 should be a narrow backend addition, not another storage abstraction rewrite. Phase 6 already established the only stable seam that matters: `StorageBackend` plus the shared row shapes. The correct approach now is to implement `PostgresBackend` against that seam, keep the backend API identical, and avoid touching analytics logic in `corpulse/core.py`.

The most important packaging constraint comes from Psycopg's own installation guidance: library authors should depend on `psycopg`, not on a specific implementation such as `psycopg[binary]`. That means the project extra should be `psycopg>=3.2`, while service consumers remain free to choose `psycopg[binary]` or `psycopg[c]` in their own deployment environment. This also aligns with the roadmap wording, which only promises psycopg as an optional dependency.

The main implementation risk is import behavior. `corpulse/backends/__init__.py` currently eagerly imports concrete backends. If Phase 7 adds `from .postgres import PostgresBackend` and that module imports `psycopg` at top level, then `import corpulse.backends` will fail on machines without psycopg installed. The plan should therefore make Postgres loading lazy, either by moving psycopg imports into backend initialization or by using module-level `__getattr__` for `PostgresBackend` exports.

The second risk is testing. This workspace currently has no `psql`, `postgres`, or `docker`, so the phase cannot assume a local PostgreSQL server exists. Planning should explicitly separate:

- deterministic unit coverage that always runs, using monkeypatched/fake psycopg objects for lazy import, SQL shape, and error translation;
- live parity coverage that activates only when a real connection string is provided, e.g. `CORPULSE_POSTGRES_TEST_CONNINFO`.

That keeps the repo testable everywhere while still providing a path to satisfy the parity success criterion in environments that actually have PostgreSQL available.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `psycopg` | `>=3.2` | Sync PostgreSQL driver | Official Psycopg 3 package; roadmap already names psycopg |
| `pytest` | `9.0.2` locally, `>=8.0` in `pyproject.toml` | Unit and live parity testing | Existing project test framework |
| PostgreSQL SQL primitives | server-side | Schema and upsert behavior | Existing backend design uses raw SQL, not an ORM |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `psycopg.rows.dict_row` | Psycopg 3 | Dict-shaped read rows | Use on the connection or cursor so read methods return mapping rows like SQLite/InMemory |
| Python `types.ModuleType` / monkeypatching | stdlib | Driver stubs in tests | Use to verify lazy import and translated error behavior without a live server |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `psycopg` library extra | `psycopg[binary]` in `pyproject.toml` | Psycopg docs recommend libraries depend on `psycopg`, leaving implementation choice to the consuming app |
| Persistent connection per backend instance | Open a new connection for every method call | Simpler symmetry with SQLite, but worse fit for a service-targeted Postgres backend |
| Always-on live Postgres tests | Env-gated live integration tests | The current workspace has no local PostgreSQL tooling, so always-on live tests would make the suite non-runnable here |

## Current Codebase Findings

### Stable Interface Already Exists

Phase 6 reduced the storage contract to these methods:

1. `upsert_document`
2. `insert_retrieval`
3. `insert_engagement`
4. `update_source_timestamp`
5. `all_documents`
6. `retrieval_counts`
7. `engagement_counts`
8. `all_embeddings`
9. `close`

`corpulse/core.py` only depends on these methods plus mapping-style row access, so Phase 7 should not change any core analytics code.

### Schema Translation Needed

Current SQLite schema uses:

- `TEXT PRIMARY KEY` for `documents.doc_id`
- `BLOB` for `embedding_vec`
- `REAL` for timestamps and scores
- `INTEGER PRIMARY KEY AUTOINCREMENT` for event ids

The PostgreSQL translation should be straightforward:

- `TEXT PRIMARY KEY`
- `BYTEA` for `embedding_vec`
- `DOUBLE PRECISION` for floating-point timestamps and scores
- `BIGSERIAL PRIMARY KEY` for event ids
- `CREATE INDEX IF NOT EXISTS ...`

`bytes` maps naturally to `BYTEA` in Psycopg 3, which keeps embedding storage compatible with the existing `numpy.ndarray.tobytes()` path in `corpulse/core.py`.

### Import Surface Risk

Current imports:

- `corpulse/core.py` imports `SQLiteBackend` and `StorageBackend`
- `corpulse/backends/__init__.py` eagerly imports `SQLiteBackend` and `InMemoryBackend`
- `tests/test_import.py` only protects `import corpulse`, not `import corpulse.backends`

Phase 7 should add explicit tests proving:

- `import corpulse` still succeeds without psycopg installed
- importing `corpulse.backends` still succeeds without psycopg installed
- attempting to instantiate `PostgresBackend` without psycopg raises a clear import error

## Recommended Architecture

### Pattern 1: Lazy-load psycopg

Do not import `psycopg` at module import time in any path hit by `import corpulse` or `import corpulse.backends`.

Recommended structure:

- `corpulse/backends/postgres.py` defines `PostgresBackend`
- a private helper such as `_load_psycopg()` performs the import inside backend initialization
- `corpulse/backends/__init__.py` exposes `PostgresBackend` through `__getattr__`, mirroring the lazy Qdrant export pattern already used in `corpulse/__init__.py`

### Pattern 2: Use dict rows for reads

Configure Psycopg with `row_factory=dict_row` so read methods can return normal mappings with the same keys used by existing analytics code.

This avoids tuple indexing, manual column mapping, and backend-specific row objects leaking into `core.py`.

### Pattern 3: Use a persistent connection with explicit commits

For the sync Postgres backend, keep one connection on the backend instance:

- open it in `__init__`
- initialize schema immediately
- commit after writes
- rollback on psycopg errors before re-raising `StorageBackendError`
- close it in `close()`

That gives predictable resource management and a meaningful `close()` implementation, unlike SQLite's current no-op close.

### Pattern 4: Split unit coverage from live parity coverage

Add two test layers:

1. always-runnable unit tests:
   - lazy import
   - psycopg import failure path
   - schema init SQL invoked
   - translated `StorageBackendError`
   - `pyproject.toml` `[postgres]` extra

2. env-gated live tests:
   - only activate when `CORPULSE_POSTGRES_TEST_CONNINFO` is set
   - run the shared backend parity suite against a real PostgreSQL database
   - verify `Corpulse(backend=PostgresBackend(...))` records retrievals end-to-end

## Open Questions

1. **Should `PostgresBackend` expose connection kwargs beyond `conninfo` in Phase 7?**
   - What we know: roadmap only promises `conninfo="..."`.
   - Recommendation: keep the public constructor minimal in Phase 7 and defer pool/config expansion to Phase 8.

2. **Should shared parity tests always include Postgres?**
   - What we know: the current machine has no PostgreSQL tooling.
   - Recommendation: make live Postgres parity opt-in via env var, but structure the shared fixture so it includes `postgres` automatically when the env var is present.

3. **Should pooling land now because psycopg documents it separately?**
   - What we know: Psycopg pools live in a separate `psycopg_pool` package and the roadmap assigns pooling to Phase 8.
   - Recommendation: do not add pooling in Phase 7.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 9.0.2` |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/test_postgres_backend.py tests/test_import.py tests/test_package.py -q` |
| Full suite command | `pytest tests -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BACK-04 | Sync backend initializes schema and implements storage contract | unit + live integration | `pytest tests/test_postgres_backend.py -q` and `CORPULSE_POSTGRES_TEST_CONNINFO=... pytest tests/test_backend_contract.py tests/test_core_backend_integration.py tests/test_postgres_backend.py -q` | ❌ Wave 1 |
| INT-02 | `[postgres]` extra declares psycopg dependency | package smoke | `pytest tests/test_package.py -q` | ✅ |

### Sampling Rate

- **Per task commit:** run that task's `<automated>` command from the plan
- **After implementation task:** `pytest tests/test_postgres_backend.py tests/test_import.py tests/test_package.py -q`
- **After parity task with a real DSN available:** `CORPULSE_POSTGRES_TEST_CONNINFO=... pytest tests/test_backend_contract.py tests/test_core_backend_integration.py tests/test_postgres_backend.py -q`
- **Phase gate:** `pytest tests -q`

### Wave 0 Gaps

No separate Wave 0 is required.

The only environment prerequisite is a PostgreSQL connection string for the live parity branch:

- `CORPULSE_POSTGRES_TEST_CONNINFO`

Without that env var, live parity tests should skip cleanly and the rest of the test suite should remain green.

## Sources

### Primary (HIGH confidence)

- Repository code:
  - `corpulse/backends/base.py`
  - `corpulse/backends/sqlite.py`
  - `corpulse/backends/memory.py`
  - `corpulse/backends/__init__.py`
  - `corpulse/core.py`
  - `tests/test_backend_contract.py`
  - `tests/test_core_backend_integration.py`
  - `tests/test_import.py`
  - `tests/test_package.py`
  - `pyproject.toml`
- Psycopg installation docs: https://www.psycopg.org/psycopg3/docs/basic/install.html
  - Verified that library dependencies should target `psycopg`, not force a specific implementation.
- Psycopg basic adaptation docs: https://www.psycopg.org/psycopg3/docs/basic/adapt.html
  - Verified that Python `bytes` map to PostgreSQL `bytea`.
- Psycopg row factory docs: https://www.psycopg.org/psycopg3/docs/api/rows.html
  - Verified `dict_row` support for dictionary-shaped query results.
- Psycopg basic usage and transaction docs:
  - https://www.psycopg.org/psycopg3/docs/basic/usage.html
  - https://www.psycopg.org/psycopg3/docs/basic/transactions.html
  - Verified connection/context-manager and commit behavior.
- Psycopg pool docs: https://www.psycopg.org/psycopg3/docs/advanced/pool.html
  - Verified that pooling is in a separate package and should remain deferred.

### Secondary (MEDIUM confidence)

- `.planning/PROJECT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`

## Metadata

**Confidence breakdown:**

- Driver packaging guidance: HIGH
- SQL type translation (`bytes` -> `BYTEA`, dict rows): HIGH
- Local test execution path: HIGH
- Exact constructor/resource-management shape for `PostgresBackend`: MEDIUM
- Live parity test ergonomics without bundled PostgreSQL tooling: MEDIUM
