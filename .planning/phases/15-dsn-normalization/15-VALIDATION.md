---
phase: 15
slug: dsn-normalization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (with pytest-asyncio, already configured) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_dsn_normalization.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~5 seconds (quick) / full suite per project norms |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_dsn_normalization.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 0 | DSN-03 | — | N/A | unit | `pytest tests/test_dsn_normalization.py -x` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | DSN-02 | — | N/A | unit | `pytest tests/test_postgres_backend.py -k dsn -x` | ✅ | ⬜ pending |
| 15-01-03 | 01 | 1 | DSN-01 | — | N/A | unit | `pytest tests/test_async_postgres_backend.py -k dsn -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dsn_normalization.py` — parametrized unit tests for `_normalize_postgres_dsn` (covers DSN-03)

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
