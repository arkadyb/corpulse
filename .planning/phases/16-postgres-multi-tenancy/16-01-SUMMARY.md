---
phase: 16-postgres-multi-tenancy
plan: 01
subsystem: database
tags: [postgres, multitenancy, ddl, testing]
requires:
  - phase: 15-dsn-normalization
    provides: normalized Postgres DSNs for the sync backend constructor
provides:
  - validated schema and table-prefix identifier helpers
  - public build_schema_sql(schema=None, prefix="") DDL generator
  - direct regression tests for default, schema, prefix, and invalid identifier behavior
affects: [16-02, 16-03, postgres_async, tenancy]
tech-stack:
  added: []
  patterns: [validated SQL identifier interpolation, shared Postgres DDL builder]
key-files:
  created: []
  modified:
    - corpulse/backends/postgres.py
    - tests/test_postgres_backend.py
key-decisions:
  - "build_schema_sql preserves the exact legacy default DDL string shape so current initialization behavior stays byte-for-byte compatible."
  - "Prefix-only mode namespaces index names as well as table names to prevent collisions within one schema."
patterns-established:
  - "Postgres identifier interpolation must go through regex validation before SQL generation."
  - "Tenant-aware DDL should be generated from one shared helper instead of module-level duplicated SQL strings."
requirements-completed: [PGMT-03, PGMT-04]
duration: 1 min
completed: 2026-04-15
---

# Phase 16 Plan 01: Shared Postgres DDL Summary

**Validated Postgres identifier helpers and a public tenant-aware DDL builder that preserves the existing default schema SQL exactly**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-15T03:32:51Z
- **Completed:** 2026-04-15T03:33:48Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Added strict regex-backed validation for `schema` and `table_prefix` inputs before SQL generation.
- Replaced the static schema constant with `build_schema_sql(schema=None, prefix="")`, including optional schema bootstrap and prefixed index names.
- Added direct regression tests for default output, schema-qualified output, prefix-only output, and invalid identifier rejection.

## Task Commits

1. **Task 1: Add identifier validation helpers** - `5cb8a9f` (`feat`)
2. **Task 2: Add public `build_schema_sql(schema=None, prefix="")`** - `506f680` (`feat`)
3. **Task 3: Lock down helper behavior with direct tests** - `0734115` (`test`)

## Files Created/Modified

- `corpulse/backends/postgres.py` - adds shared identifier validation and the tenant-aware DDL builder used by backend initialization.
- `tests/test_postgres_backend.py` - adds direct regression coverage for DDL generation and invalid identifier rejection.

## Decisions Made

- Preserved the exact legacy default DDL string formatting so `build_schema_sql()` is backward-compatible with the previous module constant.
- Applied prefixes to index names as well as table names so prefix-only tenancy cannot collide on shared-schema indexes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restored exact legacy default DDL formatting**
- **Found during:** Task 2
- **Issue:** The initial builder output introduced extra blank lines between index statements, breaking strict backward-compatibility for the default SQL string.
- **Fix:** Split table and index formatting so the generated default SQL matches the previous constant exactly while keeping tenant-aware variants.
- **Files modified:** `corpulse/backends/postgres.py`
- **Verification:** `pytest tests/test_postgres_backend.py -k schema_sql -x`
- **Committed in:** `506f680`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The fix was required to satisfy the plan's backward-compatibility constraint. No scope expansion.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Shared validation and DDL primitives are in place for sync and async query rewiring in Plan 16-02.
- The direct helper tests now guard the public contract that later tenancy work must preserve.

## Self-Check: PASSED
