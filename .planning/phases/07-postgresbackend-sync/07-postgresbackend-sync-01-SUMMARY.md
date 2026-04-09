---
phase: 07-postgresbackend-sync
plan: 01
subsystem: database
tags: [postgres, psycopg, storage-backend, pytest, lazy-import]
requires:
  - phase: 06-storage-foundation
    provides: StorageBackend contract, backend injection, and shared parity fixtures for non-SQLite backends
provides:
  - Lazy-loaded PostgresBackend with schema auto-init and translated storage errors
  - Optional [postgres] package extra using psycopg>=3.2
  - Deterministic fake-driver tests plus env-gated live PostgreSQL parity coverage
affects: [phase-08-asyncpostgresbackend, backend-testing, package-extras]
tech-stack:
  added: []
  patterns: [lazy backend export, env-gated live backend parity, fake-driver storage tests]
key-files:
  created: [corpulse/backends/postgres.py, tests/test_postgres_backend.py]
  modified: [corpulse/backends/__init__.py, pyproject.toml, tests/conftest.py, tests/test_backend_contract.py, tests/test_core_backend_integration.py, tests/test_import.py, tests/test_package.py]
key-decisions:
  - "PostgresBackend keeps psycopg imports behind _load_psycopg() and corpulse.backends.__getattr__ so base imports remain dependency-free."
  - "Live PostgreSQL parity is activated only when CORPULSE_POSTGRES_TEST_CONNINFO is set; local runs without a database skip that branch cleanly."
patterns-established:
  - "Optional storage backends should be exported lazily from corpulse.backends and load their driver only at instantiation."
  - "Backend contract tests may add env-gated real-database branches while preserving deterministic fake-driver coverage for default CI/local runs."
requirements-completed: [BACK-04, INT-02]
duration: 16 min
completed: 2026-04-09
---

# Phase 07 Plan 01: PostgresBackend Sync Summary

**Lazy-loaded psycopg-backed PostgresBackend with package extra wiring and deterministic plus live-gated parity coverage**

## Performance

- **Duration:** 16 min
- **Started:** 2026-04-09T08:03:00Z
- **Completed:** 2026-04-09T08:19:13Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Added `PostgresBackend` with PostgreSQL schema initialization, `BYTEA` embedding storage, and `StorageBackendError` translation at the backend boundary.
- Exposed `PostgresBackend` lazily from `corpulse.backends` and declared the optional `[postgres]` extra without making `psycopg` mandatory for base imports.
- Added deterministic fake-driver tests, import/package smoke coverage, and env-gated live PostgreSQL parity hooks through `CORPULSE_POSTGRES_TEST_CONNINFO`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the sync Postgres backend and lazy package surface** - `b317371` (feat)
2. **Task 2: Add deterministic tests and env-gated live parity coverage for PostgresBackend** - `2d4cabe` (test)

## Files Created/Modified
- `corpulse/backends/postgres.py` - Sync PostgreSQL backend with lazy psycopg loading, schema auto-init, and translated storage errors.
- `corpulse/backends/__init__.py` - Lazy `PostgresBackend` export path via module-level `__getattr__`.
- `pyproject.toml` - Optional `[postgres]` extra using `psycopg>=3.2`.
- `tests/test_postgres_backend.py` - Fake-driver unit tests and env-gated live Postgres round-trip coverage.
- `tests/conftest.py` - Shared backend fixture activation for Postgres when a conninfo is provided.
- `tests/test_backend_contract.py` - Shared fixture assertions extended to recognize the Postgres backend branch.
- `tests/test_core_backend_integration.py` - Env-gated `Corpulse(backend=PostgresBackend(...))` integration coverage.
- `tests/test_import.py` - Smoke tests proving `corpulse.backends` and the lazy `PostgresBackend` export do not import psycopg eagerly.
- `tests/test_package.py` - Package metadata assertion for the `[postgres]` extra.

## Decisions Made
- Kept `psycopg` import logic inside `_load_psycopg()` and the package export path lazy so `import corpulse` and `import corpulse.backends` remain safe without Postgres dependencies installed.
- Used deterministic fake connection tests for backend behavior and reserved real PostgreSQL parity for `CORPULSE_POSTGRES_TEST_CONNINFO` environments because this workspace has no local Postgres service.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 1 verification command depended on Task 2's new test file**
- **Found during:** Task 1 (Add the sync Postgres backend and lazy package surface)
- **Issue:** The plan's Task 1 automated command referenced `tests/test_postgres_backend.py`, which did not exist until Task 2.
- **Fix:** Verified Task 1 with import/package smoke tests and the task acceptance criteria first, then ran the full Postgres-targeted test commands once Task 2 landed.
- **Files modified:** None
- **Verification:** `pytest tests/test_import.py tests/test_package.py -q` after Task 1; full targeted Postgres commands passed after Task 2.
- **Committed in:** `b317371` and `2d4cabe`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** No scope change. Verification was sequenced to match actual file availability.

## Issues Encountered

- No local PostgreSQL database or conninfo was available in this workspace, so the live parity tests were intentionally skipped and left as a verification follow-up.

## User Setup Required

- Set `CORPULSE_POSTGRES_TEST_CONNINFO` to a reachable PostgreSQL test database to run the live parity branch:
  `CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://... pytest tests/test_backend_contract.py tests/test_core_backend_integration.py tests/test_postgres_backend.py -q`

## Next Phase Readiness

- Phase 8 can build on the lazy backend export and env-gated parity pattern established here for `AsyncPostgresBackend`.
- Phase 7 implementation is complete, but full real-database verification still requires a PostgreSQL conninfo.

## Self-Check

PASSED

---
*Phase: 07-postgresbackend-sync*
*Completed: 2026-04-09*
