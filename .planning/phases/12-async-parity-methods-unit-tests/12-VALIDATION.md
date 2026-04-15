---
phase: 12
slug: async-parity-methods-unit-tests
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-10
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_async_core_integration.py -q` |
| **Full suite command** | `pytest tests/test_async_core_integration.py tests/test_report_helpers.py -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task's `<automated>` command from the map below
- **After every plan wave:** Run `pytest tests/test_async_core_integration.py tests/test_report_helpers.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | ASYNC-TEST-01 | T-12-01 | Shared fixture keeps sync and async parity inputs identical | unit | `pytest tests/test_report_helpers.py -q` | ✅ | ⬜ pending |
| 12-01-02 | 01 | 1 | ASYNC-PAR-01 | T-12-02 | Async dataframe path preserves optional pandas guard and sync status semantics | unit | `pytest tests/test_async_core_integration.py -q` | ✅ | ⬜ pending |
| 12-02-01 | 02 | 2 | ASYNC-PAR-02 | T-12-05 | Async report returns helper-derived structured payload without stdout coupling | unit | `pytest tests/test_async_core_integration.py -q` | ✅ | ⬜ pending |
| 12-02-02 | 02 | 2 | ASYNC-PAR-03, ASYNC-TEST-02 | T-12-06 | Async cleanup payload preserves counts, top-5 truncation, and section schema while the focused parity suite catches drift against sync/shared-helper outputs | unit | `pytest tests/test_async_core_integration.py tests/test_report_helpers.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- None. Existing infrastructure is sufficient because every planned task already has an explicit `<automated>` command; the shared frozen fixture extraction is Task `12-01-01`, not a prerequisite Wave 0 scaffold.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
