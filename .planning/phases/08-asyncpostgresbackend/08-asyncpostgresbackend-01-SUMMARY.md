---
phase: 08-asyncpostgresbackend
plan: 01
subsystem: database
tags: [postgres, asyncpg, storage-backend, pytest, lazy-import, asyncio]
requires:
  - phase: 07-postgresbackend-sync
    provides: Shared Postgres schema, lazy backend export pattern, and env-gated live parity coverage approach
provides:
  - Lazy-loaded AsyncPostgresBackend with asyncpg pool creation and schema initialization
  - Optional [postgres-async] package extra using asyncpg>=0.29
  - Deterministic fake-driver async tests plus env-gated live async PostgreSQL round-trip coverage
affects: [async-services, backend-testing, package-extras]
tech-stack:
  added: []
  patterns: [async backend factory, pooled async database access, env-gated live async parity]
key-files:
  created: [corpulse/backends/postgres_async.py, tests/test_async_postgres_backend.py]
  modified: [corpulse/backends/__init__.py, pyproject.toml, tests/conftest.py, tests/test_import.py, tests/test_package.py]
key-decisions:
  - "AsyncPostgresBackend reuses the sync Postgres SCHEMA constant but splits it into individual statements because asyncpg execute() cannot run the full multi-statement schema at once."
  - "AsyncPostgresBackend stays outside the sync StorageBackend ABC and exposes async CRUD methods plus create()/close()/async context manager for event-loop-safe usage."
  - "Async live round-trip coverage is gated behind CORPULSE_POSTGRES_TEST_CONNINFO and asyncpg availability so default local runs stay green without a real database."
patterns-established:
  - "Optional async storage backends should lazy-load their driver in a private loader and be exported through corpulse.backends.__getattr__."
  - "Async database backends should use pooled acquire/transaction blocks per operation and translate driver errors into StorageBackendError."
requirements-completed: [BACK-05, INT-02]
duration: 18 min
completed: 2026-04-09
---

# Phase 08 Plan 01: AsyncPostgresBackend Summary

**Asyncpg-backed AsyncPostgresBackend with package extra wiring, pooled async operations, and deterministic plus live-gated coverage**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-09T08:34:00Z
- **Completed:** 2026-04-09T08:52:00Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Added `AsyncPostgresBackend` with `create()` factory, async CRUD methods, pool-backed queries, async context manager support, and `StorageBackendError` translation.
- Exposed `AsyncPostgresBackend` lazily from `corpulse.backends` and declared the optional `[postgres-async]` extra without making `asyncpg` mandatory for base imports.
- Added fake-driver async coverage, import/package smoke coverage, env-gated live async round-trip testing, and an `async_backend` fixture for shared async parity.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write fake-driver tests and packaging assertions (tests first)** - `7ea4c44` (test)
2. **Task 2: Implement AsyncPostgresBackend, lazy export, and [postgres-async] extra** - `b646354` (feat)
3. **Task 3: Add async_backend fixture to conftest.py for shared parity** - `deadf4c` (test)

## Files Created/Modified

- `corpulse/backends/postgres_async.py` - Async PostgreSQL backend with lazy asyncpg loading, pool factory, schema init, and translated errors.
- `corpulse/backends/__init__.py` - Lazy `AsyncPostgresBackend` export path via module-level `__getattr__`.
- `pyproject.toml` - Optional `[postgres-async]` extra using `asyncpg>=0.29`.
- `tests/test_async_postgres_backend.py` - Fake-driver unit tests and env-gated live async Postgres round-trip coverage.
- `tests/conftest.py` - `async_backend` fixture for shared async parity when conninfo and asyncpg are available.
- `tests/test_import.py` - Smoke tests proving `corpulse.backends` and the lazy `AsyncPostgresBackend` export do not import `asyncpg` eagerly.
- `tests/test_package.py` - Package metadata assertion for the `[postgres-async]` extra.

## Decisions Made

- Reused the sync Postgres `SCHEMA` constant as the single DDL source of truth, but executed each statement separately because `asyncpg` only accepts one statement per `execute()` call.
- Kept the async backend separate from the sync `StorageBackend` ABC because Phase 8 is about non-blocking async storage operations, not sync/async bridging.
- Left live async PostgreSQL verification env-gated to match the existing local workflow and avoid requiring a running database in default test runs.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 1 needed import-safe async tests before the backend existed**
- **Found during:** Task 1
- **Issue:** Importing `corpulse.backends.postgres_async` would fail at collection time before Task 2 created the module.
- **Fix:** Added a module-level import guard in `tests/test_async_postgres_backend.py` so the file collects cleanly before implementation and activates automatically once the backend exists.
- **Files modified:** `tests/test_async_postgres_backend.py`
- **Verification:** `python -c "import ast; ast.parse(open('tests/test_async_postgres_backend.py').read()); print('syntax OK')"` and later full task-2 pytest pass
- **Committed in:** `7ea4c44`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** No scope change. The test-first sequence remained intact while avoiding a collection-time hard failure.

## Issues Encountered

- No local PostgreSQL connection string was available, so the live async round-trip test remains implemented but skipped in this workspace.

## User Setup Required

- Set `CORPULSE_POSTGRES_TEST_CONNINFO` to a reachable PostgreSQL test database to run the live async branch:
  `CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://... pytest tests/test_async_postgres_backend.py -q`

## Next Phase Readiness

- Phase 8 implementation is complete and ready for phase-goal verification.
- Full live async parity still depends on `CORPULSE_POSTGRES_TEST_CONNINFO`, matching the sync Postgres verification pattern from Phase 7.

## Self-Check

PASSED

---
*Phase: 08-asyncpostgresbackend*
*Completed: 2026-04-09*
