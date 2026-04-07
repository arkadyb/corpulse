---
phase: 5
slug: address-review-findings-in-corpus-health-and-qdrant-wrapper
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-07
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest>=8.0 + pytest-asyncio>=0.23 |
| **Config file** | pyproject.toml |
| **Quick run command** | `python3 -m pytest -q tests/test_analytics.py tests/test_qdrant_wrapper.py` |
| **Full suite command** | `python3 -m pytest -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest -q tests/test_analytics.py tests/test_qdrant_wrapper.py`
- **After every plan wave:** Run `python3 -m pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | RVW-CH-01 | unit | `python3 -m pytest -q tests/test_analytics.py -k corpus_health` | ✅ | ⬜ pending |
| 05-01-02 | 01 | 1 | RVW-CH-02 | unit | `python3 -m pytest -q tests/test_analytics.py -k corpus_health` | ✅ | ⬜ pending |
| 05-03-01 | 03 | 2 | RVW-QD-01 | integration | `python3 -m pytest -q tests/test_qdrant_wrapper.py` | ✅ | ⬜ pending |
| 05-03-02 | 03 | 2 | RVW-QD-02 | integration | `python3 -m pytest -q tests/test_qdrant_wrapper.py -k vectors` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `python3 -m pip install -e ".[dev,qdrant]"` — provision missing local test dependencies
- [ ] `tests/test_analytics.py` — add empty-corpus schema and overlapping-noise regression coverage
- [ ] `tests/test_qdrant_wrapper.py` — add upstream-behavior and named-vector regression coverage

---

## Manual-Only Verifications

All phase behaviors should have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
