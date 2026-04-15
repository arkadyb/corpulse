---
phase: 13
slug: live-async-integration-tests
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_async_core_integration.py -q` |
| **Full suite command** | `pytest tests/test_async_core_integration.py -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_async_core_integration.py -q`
- **After every plan wave:** Run `pytest tests/test_async_core_integration.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | ASYNC-TEST-03 | T-13-01 | Live async fixture remains env-gated and skips cleanly with no DSN | integration | `pytest tests/test_async_core_integration.py -q` | ✅ | ⬜ pending |
| 13-01-02 | 01 | 1 | ASYNC-TEST-03 | T-13-02 | Live report-surface tests assert payload shape and key values against real Postgres state | integration | `pytest tests/test_async_core_integration.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/report_fixtures.py` exports any raw seed rows or helpers needed to seed the live async backend from the same canonical corpus as Phase 12 expectations
- [ ] Plan verification must keep live async commands sequential when they target one shared `CORPULSE_POSTGRES_TEST_CONNINFO` database

---

## Manual-Only Verifications

All phase behaviors have automated verification once a live Postgres DSN is available.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
