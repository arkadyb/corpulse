---
phase: 15-dsn-normalization
plan: 01
type: summary
date_completed: 2026-04-15
requirements:
  - DSN-01
  - DSN-02
  - DSN-03
commits:
  - 380f648
---

# Phase 15 Plan 01 Summary

Implemented shared DSN normalization for the sync and async Postgres backends so SQLAlchemy-style driver-qualified DSNs are accepted without changing existing plain-DSN behavior.

## Completed Work

1. Added [corpulse/backends/_dsn.py](/Users/arkady/src/corpulse/corpulse/backends/_dsn.py) with a private `_normalize_postgres_dsn()` helper that strips only the leading `postgresql+<driver>://` or `postgres+<driver>://` qualifier and leaves all other input unchanged.
2. Wired normalization into [corpulse/backends/postgres.py](/Users/arkady/src/corpulse/corpulse/backends/postgres.py) at `ConnectionPool(...)` construction so sync callers can pass SQLAlchemy-style DSNs.
3. Wired normalization into [corpulse/backends/postgres_async.py](/Users/arkady/src/corpulse/corpulse/backends/postgres_async.py) at `asyncpg.create_pool(...)` construction so async callers can pass SQLAlchemy-style DSNs.
4. Added [tests/test_dsn_normalization.py](/Users/arkady/src/corpulse/tests/test_dsn_normalization.py) covering passthrough, `+psycopg`, `+psycopg2`, `+asyncpg`, encoded credentials, IPv6 hosts, uppercase non-match behavior, malformed inputs, and libpq key=value passthrough.
5. Extended [tests/test_postgres_backend.py](/Users/arkady/src/corpulse/tests/test_postgres_backend.py) and [tests/test_async_postgres_backend.py](/Users/arkady/src/corpulse/tests/test_async_postgres_backend.py) with backend-boundary assertions proving the normalized DSN is what reaches the fake pool constructors.

## Requirements Satisfied

- **DSN-01**: `AsyncPostgresBackend.create()` now normalizes SQLAlchemy-style async DSNs before pool creation.
- **DSN-02**: `PostgresBackend(...)` now normalizes SQLAlchemy-style sync DSNs before pool creation.
- **DSN-03**: Shared helper tests plus mirrored sync/async call-site tests prove identical normalization behavior across both backends.

## Verification

Executed:

```bash
pytest tests/test_dsn_normalization.py -x
pytest tests/test_postgres_backend.py -k dsn -x
pytest tests/test_async_postgres_backend.py -k dsn -x
pytest tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_dsn_normalization.py -x
pytest
```

Result:
- Targeted DSN suite passed.
- Full project test suite passed.
- Existing live Postgres tests remained env-gated and skipped when `CORPULSE_POSTGRES_TEST_CONNINFO` plus drivers were unavailable.

## Notes

- No new runtime dependencies were added.
- The helper remains underscore-private and is not re-exported from `corpulse.backends`.
- No logging or public API signatures changed.
