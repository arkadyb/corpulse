---
phase: 13-live-async-integration-tests
verified: 2026-04-12T00:00:00Z
status: human_needed
score: 3/3 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run with CORPULSE_POSTGRES_TEST_CONNINFO set against a live Postgres instance"
    expected: "pytest tests/test_async_core_integration.py -q reports 15 passed, 0 skipped (all 4 live tests run and pass including the 3 new parity tests)"
    why_human: "Cannot start or connect to a real PostgreSQL instance programmatically in this environment; live asyncpg path requires an actual database"
---

# Phase 13: Live Async Integration Tests Verification Report

**Phase Goal:** Running `pytest` with `CORPULSE_POSTGRES_TEST_CONNINFO` set exercises `to_dataframe`, `report`, and `cleanup_report` end-to-end against a real Postgres instance via `asyncpg`.
**Verified:** 2026-04-12
**Status:** human_needed — automated checks all pass; live database execution requires human verification
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | With `CORPULSE_POSTGRES_TEST_CONNINFO` set, `pytest tests/test_async_core_integration.py -q` runs the live integration tests for `to_dataframe`, `report`, and `cleanup_report` without skip and without error. | PASS (override: human) | Four live test functions exist at lines 595, 609, 630, 649 of `tests/test_async_core_integration.py`; all accept `async_backend` fixture which skips only when the DSN env var is absent. No DSN is hardcoded. |
| 2 | Without `CORPULSE_POSTGRES_TEST_CONNINFO` set, the same live tests are skipped cleanly — the non-live suite still passes in full. | ✓ VERIFIED | `pytest tests/test_async_core_integration.py -q` (without DSN) produced: `15 passed, 4 skipped`. Skip message is "requires CORPULSE_POSTGRES_TEST_CONNINFO and asyncpg" sourced from `conftest.py:68`. |
| 3 | The live tests ingest fixture data, call all three new parity methods, and assert on the shape and key values of the returned payloads — not merely that the calls complete without exception. | ✓ VERIFIED | `test_live_async_to_dataframe_shape_and_ordering` (line 609) asserts columns, row count == 10, descending ordering, and `retrieval_counts[:4] == [10, 8, 7, 6]`. `test_live_async_report_summary_and_representative_rows` (line 630) asserts `payload["summary"] == expected["summary"]`, noisy-doc status is "low_engagement", and row count matches helper. `test_live_async_cleanup_report_metadata_and_section_counts` (line 649) asserts `total_docs`, `ghost_threshold_days`, `bloat_warning`, all four section counts, and `ghosts["top5"]` and `stale["top5"]` against shared expected payload. |

**Score:** 3/3 truths verified (truth 1 requires human for live execution)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_async_core_integration.py` | Env-gated live async integration tests for dataframe, report, and cleanup parity surfaces | ✓ VERIFIED + WIRED | Contains `test_live_async_corpulse_round_trip` (line 595), `test_live_async_to_dataframe_shape_and_ordering` (609), `test_live_async_report_summary_and_representative_rows` (630), `test_live_async_cleanup_report_metadata_and_section_counts` (649). All import and use `seed_async_backend` from `report_fixtures`. |
| `tests/report_fixtures.py` | Shared canonical seed rows or helpers reused by the live async integration tests | ✓ VERIFIED | `build_report_fixture_snapshot` at line 196, `seed_async_backend` async helper at line 275 that mirrors the in-memory seeding path exactly. |
| `tests/conftest.py` | Env-gated async Postgres fixture that truncates the shared database before and after each live test | ✓ VERIFIED | `async_backend` fixture (line 65) params via `_async_backend_params()`: skips with `pytest.skip(...)` when DSN absent; when present creates `AsyncPostgresBackend`, truncates tables before yield and in finally block after. Contains `async_backend` marker at line 65. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/conftest.py` | `tests/test_async_core_integration.py` | `async_backend` fixture injection | ✓ WIRED | All four live test functions accept `async_backend` parameter. Pattern `async def test_live_.*\(async_backend\)` matches lines 595, 609, 630, 649. |
| `tests/report_fixtures.py` | `tests/test_async_core_integration.py` | shared seed rows and expected-value helpers | ✓ WIRED | `from tests.report_fixtures import ... seed_async_backend` at line 18-24. `seed_async_backend` is called via `_seed_live_backend()` in all three new live parity tests. |
| `tests/test_async_core_integration.py` | `CORPULSE_POSTGRES_TEST_CONNINFO` | pytest skip behavior and sequential live command | ✓ WIRED | Gating is in `conftest.py::_async_backend_params()` which reads `os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")`. Skip message "requires CORPULSE_POSTGRES_TEST_CONNINFO and asyncpg" appears at `conftest.py:68`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `test_live_async_to_dataframe_shape_and_ordering` | `df` / `records` | `await corpulse.to_dataframe(window_days=30)` via `AsyncPostgresBackend` | Yes — seeded by `seed_async_backend()` which calls `upsert_document`, `insert_retrieval`, `insert_engagement` through the real backend | ✓ FLOWING (live path; human-gated) |
| `test_live_async_report_summary_and_representative_rows` | `payload` | `await corpulse.report(window_days=30)` | Yes — same canonical seed corpus | ✓ FLOWING (live path; human-gated) |
| `test_live_async_cleanup_report_metadata_and_section_counts` | `payload` | `await corpulse.cleanup_report()` | Yes — same canonical seed corpus | ✓ FLOWING (live path; human-gated) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Non-live suite passes, live tests skip without DSN | `python -m pytest tests/test_async_core_integration.py -q` | `15 passed, 4 skipped` | ✓ PASS |
| Live tests skip with message "requires CORPULSE_POSTGRES_TEST_CONNINFO and asyncpg" | Confirmed from conftest.py:68 | Skip message correct | ✓ PASS |
| Live DB path: run with real Postgres | Requires live Postgres — cannot run in this environment | N/A | ? SKIP (human needed) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| ASYNC-TEST-03 | `13-01-PLAN.md` | Live asyncpg integration tests (gated by `CORPULSE_POSTGRES_TEST_CONNINFO`) exercise `to_dataframe`, `report`, and `cleanup_report` end-to-end against a real Postgres instance. | ✓ SATISFIED (human verification for live execution) | Four live tests present; three cover the required parity surfaces with concrete assertions against shared fixture helpers; skip behavior confirmed; wiring verified. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No hardcoded DSNs or credentials. No TODO/FIXME/placeholder comments in phase 13 files. `seed_async_backend` is substantive (inserts documents, retrievals, engagements from canonical rows). Live test bodies contain real assertions, not just "does not raise" checks.

### Human Verification Required

#### 1. Live Postgres Round-Trip

**Test:** Set `CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test` and run sequentially:

```
CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test \
  pytest tests/test_async_postgres_backend.py -q

CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test \
  pytest tests/test_async_core_integration.py -q
```

**Expected:** Second command reports `19 passed, 0 skipped` (15 non-live + 4 live tests all green). Specifically:
- `test_live_async_to_dataframe_shape_and_ordering` passes: 10 rows, descending order, `[10, 8, 7, 6]` top-4 retrievals
- `test_live_async_report_summary_and_representative_rows` passes: summary matches `expected_report_payload()`, noisy-doc row is `low_engagement` with 10 retrievals
- `test_live_async_cleanup_report_metadata_and_section_counts` passes: section counts and top entries match `expected_cleanup_payload()`
- `test_live_async_corpulse_round_trip` passes (existing narrow ghost test)

**Why human:** Cannot start or connect to a real PostgreSQL instance in this environment. The live asyncpg path is the core deliverable of this phase and requires an actual database to verify.

### Gaps Summary

No gaps found. All three phase success criteria are met at the code level. The single human verification item is the live database execution itself — a necessary condition that cannot be tested programmatically without a running Postgres instance. All artifacts are substantive, correctly wired, and derive assertions from shared canonical fixture helpers (not ad-hoc literals). Skip behavior for the no-DSN case is confirmed working.

---

_Verified: 2026-04-12_
_Verifier: Claude (gsd-verifier)_
