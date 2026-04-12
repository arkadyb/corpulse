---
phase: 13-live-async-integration-tests
plan: 01
subsystem: testing
tags: [asyncio, asyncpg, pytest, live-integration, parity, postgres]
requires:
  - phase: 12-async-parity-methods-unit-tests
    provides: deterministic async report and cleanup parity tests backed by shared frozen fixtures
provides:
  - Env-gated live asyncpg integration tests for to_dataframe(), report(), and cleanup_report()
  - seed_async_backend() helper for seeding a real async backend from the canonical fixture corpus
affects: [async facade, live asyncpg test coverage, parity verification]
tech-stack:
  added: []
  patterns: [env-gated live tests via async_backend fixture, canonical seed helper for real db insertion]
key-files:
  created: [.planning/phases/13-live-async-integration-tests/13-01-SUMMARY.md]
  modified: [tests/report_fixtures.py, tests/test_async_core_integration.py]
key-decisions:
  - "Exposed seed_async_backend() in report_fixtures.py so live asyncpg seeding reuses the exact same rows as the deterministic in-memory tests."
  - "Kept live tests env-gated exclusively through the async_backend conftest fixture; no manual DSN checks in test bodies."
  - "Kept the narrow ghost round-trip test alongside the new parity tests for regression coverage."
  - "Monkeypatched _days_ago to 123.0 in live report/cleanup tests for consistent expected-payload alignment with the shared helper builders."
patterns-established:
  - "Live async tests seed real Postgres via seed_async_backend() and derive expected values from shared fixture helpers."
  - "Live and deterministic async tests share the same canonical seed data through _document_seed_rows, _retrieval_seed_rows, and _engagement_seed_rows."
requirements-completed: [ASYNC-TEST-03]
duration: 10min
completed: 2026-04-12
---

# Phase 13 Plan 01: Live Async Integration Tests Summary

**Live asyncpg round-trip coverage for AsyncCorpulse.to_dataframe(), report(), and cleanup_report() using canonical fixture seeding**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-12T00:00:00Z
- **Completed:** 2026-04-12T00:10:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `seed_async_backend()` to `tests/report_fixtures.py` as the single async seeding path that inserts the same canonical document, retrieval, engagement, and source-timestamp rows used by the deterministic in-memory parity tests.
- Added three env-gated live integration tests to `tests/test_async_core_integration.py`:
  - `test_live_async_to_dataframe_shape_and_ordering` — verifies columns, 10-row count, descending retrieval ordering, and top-4 counts from the canonical corpus
  - `test_live_async_report_summary_and_representative_rows` — verifies summary matches the shared expected payload, noisy-doc status and retrieval count, and total row count
  - `test_live_async_cleanup_report_metadata_and_section_counts` — verifies total_docs, ghost_threshold_days, bloat_warning, all section counts, and ghost and stale top-5 entries
- All 4 live tests (including the existing narrow ghost test) skip cleanly without `CORPULSE_POSTGRES_TEST_CONNINFO`; 15 non-live tests continue to pass.

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add failing live async parity tests** - `1f2e375` (test)
2. **Task 1 GREEN: Implement seed_async_backend helper** - `45df690` (feat)

_Note: Task 2 behavioral requirements were satisfied by the Task 1 implementation - the three new live tests cover all three parity surfaces (to_dataframe, report, cleanup_report) with concrete assertions._

## Files Created/Modified

- `tests/report_fixtures.py` - adds `seed_async_backend()` async function that inserts the canonical corpus into a real async backend using the same private seed row builders as the in-memory fixture.
- `tests/test_async_core_integration.py` - adds `seed_async_backend` import, `_seed_live_backend()` private helper, and three live integration tests covering all three Phase 12 parity surfaces.

## Decisions Made

- Exposed `seed_async_backend()` in the public surface of `report_fixtures.py` so test files can import it without coupling to private helpers.
- Kept `test_live_async_corpulse_round_trip` (narrow ghost test) alongside the new parity tests for regression coverage.
- Used `monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)` in the live report and cleanup tests to ensure the `since` cutoff (epoch 123.0) includes all seed rows, matching the behavior of the shared expected payload builders which use `FROZEN - 30*_DAY`.

## Deviations from Plan

None - plan executed exactly as written.

## Verification Commands

After Task 2 (without DSN - deterministic and skip behavior):
```
pytest tests/test_async_core_integration.py -q
# Expected: 15 passed, 4 skipped
```

Live verification (sequential, shared DB):
```
CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test pytest tests/test_async_postgres_backend.py -q
CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test pytest tests/test_async_core_integration.py -q
```

_These two commands must run sequentially against the same database to avoid cross-test contamination._

## Known Stubs

None.

## Threat Flags

No new network endpoints, auth paths, or schema changes introduced. The threat model mitigations from the plan are satisfied:
- T-13-01: Live path remains env-gated through `CORPULSE_POSTGRES_TEST_CONNINFO`; truncation is in the `async_backend` conftest fixture.
- T-13-02: Live verification commands documented as sequential above.
- T-13-03: Live expectations derived from `expected_report_payload()` and `expected_cleanup_payload()` from `report_fixtures.py`.
- T-13-04: No credentials or DSNs are hardcoded; only `os.environ["CORPULSE_POSTGRES_TEST_CONNINFO"]` is referenced.

## Self-Check: PASSED

- `tests/report_fixtures.py` contains `seed_async_backend` at line 275
- `tests/test_async_core_integration.py` contains `test_live_async_corpulse_round_trip` and 3 new live parity tests
- Commit `1f2e375`: test(13-01) RED phase
- Commit `45df690`: feat(13-01) GREEN phase

---
*Phase: 13-live-async-integration-tests*
*Completed: 2026-04-12*
