---
phase: 12-async-parity-methods-unit-tests
verified: 2026-04-10T08:29:45Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 12: Async Parity Methods + Unit Tests Verification Report

**Phase Goal:** `AsyncCorpulse` exposes `to_dataframe()`, `report()`, and `cleanup_report()` backed by the Phase 11 shared helpers, and deterministic async tests prove their output is at parity with sync for the same backend fixture.
**Verified:** 2026-04-10T08:29:45Z
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | `AsyncCorpulse.to_dataframe(window_days)` returns a pandas DataFrame with identical column set, row ordering, and status classification as `Corpulse.to_dataframe()` on the same fixture. | ✓ VERIFIED | [`corpulse/async_core.py` line 141](/Users/arkady/src/corpulse/corpulse/async_core.py#L141) builds rows via `_build_dataframe_rows(...)` from awaited backend reads and sorts by `retrievals` descending; [`tests/test_async_core_integration.py` line 379](/Users/arkady/src/corpulse/tests/test_async_core_integration.py#L379) compares async vs sync `to_dict("records")` on the shared fixture. |
| 2 | `AsyncCorpulse.report(window_days)` returns a dict whose summary, top-K rows, and totals match the structured payload underlying sync `report()` output for the same fixture. | ✓ VERIFIED | [`corpulse/async_core.py` line 179](/Users/arkady/src/corpulse/corpulse/async_core.py#L179) returns `{"summary": ..., "rows": ...}` using `_build_report_summary(...)` and `_build_report_rows(...)`; [`tests/test_async_core_integration.py` line 423](/Users/arkady/src/corpulse/tests/test_async_core_integration.py#L423) asserts exact equality to helper-derived expected payloads, and line 449 locks the low-engagement boundary behavior. |
| 3 | `AsyncCorpulse.cleanup_report()` returns a dict whose sections, counts, and top-5 examples match the structured payload underlying sync `cleanup_report()` output for the same fixture. | ✓ VERIFIED | [`corpulse/async_core.py` line 164](/Users/arkady/src/corpulse/corpulse/async_core.py#L164) returns `_build_cleanup_payload(...)` from awaited async analysis methods; [`tests/test_async_core_integration.py` line 462](/Users/arkady/src/corpulse/tests/test_async_core_integration.py#L462) asserts helper-derived payload equality and line 480 asserts concrete counts, metadata, and top-5 section contents. |
| 4 | Calling `AsyncCorpulse.to_dataframe()` without pandas installed raises `RuntimeError` with a clear install hint. | ✓ VERIFIED | [`corpulse/async_core.py` line 142](/Users/arkady/src/corpulse/corpulse/async_core.py#L142) raises `RuntimeError("pip install pandas to use to_dataframe()")`; [`tests/test_async_core_integration.py` line 407](/Users/arkady/src/corpulse/tests/test_async_core_integration.py#L407) verifies the exact message. |
| 5 | `pytest tests/test_async_core_integration.py -q` passes with no failures or errors; skipped live tests are acceptable. | ✓ VERIFIED | Ran `pytest tests/test_async_core_integration.py -q` -> `15 passed, 1 skipped`; the skip is the gated live asyncpg path and does not block Phase 12. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `tests/report_fixtures.py` | Shared deterministic report-fixture builders usable by sync and async tests | ✓ VERIFIED | Exists with substantive fixture seeds and helper builders at [`tests/report_fixtures.py` line 22](/Users/arkady/src/corpulse/tests/report_fixtures.py#L22), line 165, line 196, and line 208; imported by both test suites. |
| `corpulse/async_core.py` | Async parity methods built on shared helper logic | ✓ VERIFIED | `to_dataframe`, `cleanup_report`, and `report` exist at [`corpulse/async_core.py` line 141](/Users/arkady/src/corpulse/corpulse/async_core.py#L141), line 164, and line 179; all are coroutine functions and reuse Phase 11 builders instead of duplicating logic. |
| `tests/test_async_core_integration.py` | Deterministic async parity and guard coverage | ✓ VERIFIED | Contains shared-fixture parity tests for dataframe, report, and cleanup payloads at [`tests/test_async_core_integration.py` line 379](/Users/arkady/src/corpulse/tests/test_async_core_integration.py#L379) through line 532, plus the async suite passes. |
| `tests/test_report_helpers.py` | Sync helper suite still anchored to the shared fixture and Phase 11 baselines | ✓ VERIFIED | Imports shared fixtures at [`tests/test_report_helpers.py` line 18](/Users/arkady/src/corpulse/tests/test_report_helpers.py#L18); golden stdout baseline tests remain in place and `pytest tests/test_report_helpers.py -q` passed with `13 passed`. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `tests/report_fixtures.py` | `tests/test_report_helpers.py` | shared sync fixture imports | ✓ WIRED | [`tests/test_report_helpers.py` line 18](/Users/arkady/src/corpulse/tests/test_report_helpers.py#L18) imports `FROZEN`, `build_report_fixture_backend`, and `build_report_fixture_snapshot` from the shared fixture module. |
| `tests/report_fixtures.py` | `tests/test_async_core_integration.py` | shared async parity fixture imports | ✓ WIRED | [`tests/test_async_core_integration.py` line 15](/Users/arkady/src/corpulse/tests/test_async_core_integration.py#L15) imports `build_report_fixture_snapshot` and `helper_inputs`; `_shared_report_fixture_backends()` consumes the shared snapshot at line 92. |
| `corpulse/async_core.py` | `corpulse/core.py` | shared dataframe/report/cleanup payload builders | ✓ WIRED | [`corpulse/async_core.py` line 6](/Users/arkady/src/corpulse/corpulse/async_core.py#L6) imports `_build_dataframe_rows`, `_build_report_summary`, `_build_report_rows`, and `_build_cleanup_payload`, then uses them in the new parity methods at lines 154, 170, 190, and 195. |
| `corpulse/async_core.py` | structured-return async API | absence of stdout formatting | ✓ WIRED | `report()` and `cleanup_report()` return dict payloads directly and contain no `print` or `tabulate` usage; this preserves the structured-return contract required by ASYNC-PAR-02 and ASYNC-PAR-03. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `AsyncCorpulse.to_dataframe()` | `rows` | Awaited `all_documents()`, `retrieval_counts()`, `engagement_counts()`, plus awaited `get_ghosts()`, `get_obsolete()`, `get_stale_embeddings()` feeding `_build_dataframe_rows(...)` | Yes - data comes from backend rows, not static placeholders | ✓ FLOWING |
| `AsyncCorpulse.report()` | `summary`, `rows` | Awaited backend aggregates plus awaited analysis helpers feeding `_build_report_summary(...)` and `_build_report_rows(...)` | Yes - payload fields are built from real fixture rows and health computation | ✓ FLOWING |
| `AsyncCorpulse.cleanup_report()` | cleanup payload dict | Awaited `corpus_health()`, `get_ghosts()`, `get_obsolete()`, `get_stale_embeddings()`, `get_suspects()` feeding `_build_cleanup_payload(...)` | Yes - sections and metadata derive from populated analysis outputs | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Phase 12 async parity suite passes | `pytest tests/test_async_core_integration.py -q` | `15 passed, 1 skipped` | ✓ PASS |
| Shared sync helper suite still passes on the shared fixture | `pytest tests/test_report_helpers.py -q` | `13 passed` | ✓ PASS |
| New async parity methods are actually async call surfaces | `python - <<'PY' ... inspect.iscoroutinefunction(...) ... PY` | `to_dataframe True`, `report True`, `cleanup_report True` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| ASYNC-PAR-01 | 12-01 | Async dataframe parity with sync columns, ordering, status, and pandas guard | ✓ SATISFIED | [`corpulse/async_core.py` line 141](/Users/arkady/src/corpulse/corpulse/async_core.py#L141) through line 162 and [`tests/test_async_core_integration.py` line 379](/Users/arkady/src/corpulse/tests/test_async_core_integration.py#L379) through line 420. |
| ASYNC-PAR-02 | 12-02 | Async report returns structured payload equivalent to sync structured output | ✓ SATISFIED | [`corpulse/async_core.py` line 179](/Users/arkady/src/corpulse/corpulse/async_core.py#L179) through line 204 and [`tests/test_async_core_integration.py` line 423](/Users/arkady/src/corpulse/tests/test_async_core_integration.py#L423) through line 459. |
| ASYNC-PAR-03 | 12-02 | Async cleanup_report returns structured cleanup payload equivalent to sync structured output | ✓ SATISFIED | [`corpulse/async_core.py` line 164](/Users/arkady/src/corpulse/corpulse/async_core.py#L164) through line 177 and [`tests/test_async_core_integration.py` line 462](/Users/arkady/src/corpulse/tests/test_async_core_integration.py#L462) through line 532. |
| ASYNC-TEST-01 | 12-01 | Deterministic async tests prove dataframe parity on identical fixture | ✓ SATISFIED | Shared snapshot builder at [`tests/report_fixtures.py` line 196](/Users/arkady/src/corpulse/tests/report_fixtures.py#L196) plus dataframe parity tests at [`tests/test_async_core_integration.py` line 379](/Users/arkady/src/corpulse/tests/test_async_core_integration.py#L379) through line 420. |
| ASYNC-TEST-02 | 12-02 | Deterministic async tests prove report and cleanup payload parity | ✓ SATISFIED | Shared helper inputs at [`tests/report_fixtures.py` line 208](/Users/arkady/src/corpulse/tests/report_fixtures.py#L208) plus report/cleanup parity tests at [`tests/test_async_core_integration.py` line 423](/Users/arkady/src/corpulse/tests/test_async_core_integration.py#L423) through line 532. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| None | - | No blocker or warning stub patterns found in the scanned phase files. The only empty-list/dict initialisations were benign test-double or optional-branch defaults. | ℹ️ Info | No evidence of placeholder implementations, hollow returns, or stdout-coupled async methods. |

### Human Verification Required

None.

### Gaps Summary

No gaps found. Phase 12 delivers the async parity methods required by the roadmap, wires them through the shared Phase 11 helper layer, and proves parity with deterministic tests on the same frozen fixture.

---

_Verified: 2026-04-10T08:29:45Z_
_Verifier: Claude (gsd-verifier)_
