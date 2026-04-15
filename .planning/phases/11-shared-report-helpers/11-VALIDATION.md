---
phase: 11
slug: shared-report-helpers
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (detected — `tests/conftest.py` exists, `pyproject.toml` has `[tool.pytest.ini_options]`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_report_helpers.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~3 seconds quick, ~15 seconds full |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_report_helpers.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green with zero regressions in `test_async_core_integration.py`
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 0 | REPORT-HELPERS-01/02 | — | N/A (internal refactor, no attack surface) | fixture+baseline capture | `pytest tests/test_report_helpers.py::test_baseline_capture_report_output -x` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 0 | REPORT-HELPERS-01/02 | — | N/A | fixture+baseline capture | `pytest tests/test_report_helpers.py::test_baseline_capture_cleanup_output -x` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | REPORT-HELPERS-01 | — | N/A | unit | `pytest tests/test_report_helpers.py::test_build_dataframe_rows -x` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 1 | REPORT-HELPERS-01 | — | N/A | unit | `pytest tests/test_report_helpers.py::test_build_report_rows -x` | ❌ W0 | ⬜ pending |
| 11-02-03 | 02 | 1 | REPORT-HELPERS-01 | — | N/A | unit | `pytest tests/test_report_helpers.py::test_build_report_summary -x` | ❌ W0 | ⬜ pending |
| 11-02-04 | 02 | 1 | REPORT-HELPERS-01 | — | N/A | unit | `pytest tests/test_report_helpers.py::test_build_cleanup_payload -x` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 2 | REPORT-HELPERS-02 | — | N/A (printed output unchanged — no new I/O) | stdout snapshot | `pytest tests/test_report_helpers.py::test_report_stdout_unchanged -x` | ❌ W0 | ⬜ pending |
| 11-03-02 | 03 | 2 | REPORT-HELPERS-02 | — | N/A | stdout snapshot | `pytest tests/test_report_helpers.py::test_cleanup_report_stdout_unchanged -x` | ❌ W0 | ⬜ pending |
| 11-03-03 | 03 | 2 | REPORT-HELPERS-02 | — | N/A | unit | `pytest tests/test_report_helpers.py::test_to_dataframe_raises_without_pandas -x` | ❌ W0 | ⬜ pending |
| 11-03-04 | 03 | 2 | REPORT-HELPERS-02 | — | N/A | unit | `pytest tests/test_report_helpers.py::test_report_fallback_without_tabulate -x` | ❌ W0 | ⬜ pending |
| 11-03-05 | 03 | 2 | REPORT-HELPERS-02 | — | N/A | regression | `pytest tests/ -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Sampling continuity:** Every task in this phase has an `<automated>` verify command. No 3-in-a-row gap.

---

## Wave 0 Requirements

- [ ] `tests/test_report_helpers.py` — new test module covering all four helpers and both stdout snapshots
- [ ] `_report_fixture_backend()` — deterministic `InMemoryBackend` with known documents, retrievals, and engagements (module-level helper inside `test_report_helpers.py`)
- [ ] `EXPECTED_REPORT_OUTPUT` — multi-line string constant captured from pre-refactor `Corpulse.report()` run against the fixture
- [ ] `EXPECTED_CLEANUP_OUTPUT` — multi-line string constant captured from pre-refactor `Corpulse.cleanup_report()` run against the fixture

**Wave 0 ordering is critical:** The expected-string constants MUST be captured from the current (pre-refactor) code and pinned into the test file BEFORE the refactor begins. Otherwise the "byte-for-byte identical" assertion becomes tautological.

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification via pytest.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (fixture + both expected-string constants)
- [ ] No watch-mode flags
- [ ] Feedback latency < 20 seconds
- [ ] `nyquist_compliant: true` set in frontmatter (flip after planner aligns to this contract)

**Approval:** pending
