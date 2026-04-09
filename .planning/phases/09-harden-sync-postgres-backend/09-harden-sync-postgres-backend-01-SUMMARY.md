---
phase: 09-harden-sync-postgres-backend
plan: 01
subsystem: database
tags: [postgres, psycopg, psycopg-pool, storage-backend, pytest]
requires:
  - phase: 07-postgresbackend-sync
    provides: Lazy sync Postgres backend export, schema SQL, and env-gated parity coverage
  - phase: 08-asyncpostgresbackend
    provides: Pool-oriented Postgres backend pattern and audit context for INT-03
provides:
  - Sync PostgresBackend backed by psycopg_pool.ConnectionPool with configurable sizing
  - Deterministic pooling-focused tests for the sync backend contract
  - Pooled live Postgres fixture paths for parity and Corpulse backend injection
affects: [phase-07-postgresbackend-sync, phase-10-make-async-backend-usable-from-corpulse, backend-testing]
tech-stack:
  added: []
  patterns: [constructor-owned sync connection pool, per-operation pool checkout, env-gated live pooled parity]
key-files:
  created: []
  modified: [corpulse/backends/postgres.py, pyproject.toml, tests/test_postgres_backend.py, tests/conftest.py, tests/test_core_backend_integration.py, tests/test_package.py]
key-decisions:
  - "PostgresBackend now owns a psycopg_pool.ConnectionPool and checks out a connection per public operation so the sync Corpulse facade stays unchanged while meeting INT-03."
  - "The [postgres] extra now uses psycopg[pool]>=3.2 so the optional install surface matches the separate psycopg_pool runtime package."
patterns-established:
  - "Sync Postgres tests should verify pooling through fake pool objects and keep live verification behind CORPULSE_POSTGRES_TEST_CONNINFO."
  - "Shared parity fixtures must reset live Postgres state through backend._pool.connection() instead of backend-private raw connections."
requirements-completed: [BACK-04, INT-03]
duration: 11 min
completed: 2026-04-09
---

# Phase 09 Plan 01: Harden Sync Postgres Backend Summary

**Configurable sync psycopg connection pooling with deterministic pooled-backend coverage and unchanged Corpulse injection semantics**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-09T11:18:00Z
- **Completed:** 2026-04-09T11:29:24Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Replaced the sync Postgres backend's single long-lived connection with a constructor-owned `ConnectionPool` that initializes schema eagerly and checks out per operation.
- Updated the optional `[postgres]` dependency and packaging assertion to require `psycopg[pool]>=3.2`.
- Switched deterministic and env-gated live Postgres tests to pooled verification paths without changing `Corpulse(backend=PostgresBackend(...))`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Refactor PostgresBackend to use a configurable sync connection pool** - `2c4b36d` (test), `7b2141c` (feat)
2. **Task 2: Update sync Postgres tests and fixtures to prove pooling without changing the facade** - `bd5b23a` (test)

## Files Created/Modified
- `corpulse/backends/postgres.py` - Reworked sync backend construction and query execution around `psycopg_pool.ConnectionPool`.
- `pyproject.toml` - Updated the optional `[postgres]` extra to install pool support.
- `tests/test_postgres_backend.py` - Added fake pool coverage for schema init, configurable sizing, per-operation checkout, and live pooled round-trip setup.
- `tests/conftest.py` - Reset live Postgres fixture state through pooled sync connections.
- `tests/test_core_backend_integration.py` - Kept `Corpulse(backend=PostgresBackend(...))` coverage on the pooled backend path.
- `tests/test_package.py` - Asserted the exact pooled Postgres extra string.

## Decisions Made
- Kept the sync `Corpulse` boundary unchanged and localized pooling entirely inside `PostgresBackend` so no new sync/async adapter surface was introduced.
- Called `ConnectionPool.wait()` during backend construction so schema-init and connectivity failures surface before the backend is handed to callers.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Live PostgreSQL verification remains env-gated in this workspace because `CORPULSE_POSTGRES_TEST_CONNINFO` was not set, so the live pooled tests were skipped rather than executed.

## User Setup Required

- Set `CORPULSE_POSTGRES_TEST_CONNINFO` to a reachable PostgreSQL test database to run the live pooled parity branch:
  `CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://... pytest tests/test_postgres_backend.py tests/test_backend_contract.py tests/test_core_backend_integration.py -q`

## Next Phase Readiness

- Phase 09 now closes the sync pooling implementation gap and leaves Phase 09 Plan 02 to refresh verification artifacts and requirement traceability.
- Phase 10 can assume both Postgres backends use explicit pool abstractions, but async facade verification still remains separate.

## Self-Check

PASSED

---
*Phase: 09-harden-sync-postgres-backend*
*Completed: 2026-04-09*
