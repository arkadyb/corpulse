---
phase: 29
slug: workload-trace-jsonl-import-export
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-04
---

# Phase 29 - Validation Strategy

> Per-phase validation contract for JSONL workload trace import/export.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_trace_jsonl.py tests/test_docstrings.py -q` |
| **Full suite command** | `pytest tests/test_trace_jsonl.py tests/test_trace_capture.py tests/test_backend_contract.py tests/test_docstrings.py -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_trace_jsonl.py -q` once the file exists.
- **After every plan wave:** Run that wave's plan-specific pytest command.
- **Before `$gsd-verify-work`:** Full phase command must be green.
- **Max feedback latency:** 30 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 29-01-T1 | 01 | 1 | IO-01, IO-03 | T-29-01 | JSONL schema version and privacy redaction are deterministic | unit | `pytest tests/test_trace_jsonl.py -q` | W0 | pending |
| 29-01-T2 | 01 | 1 | IO-02 | T-29-02 | Strict import rejects malformed records | unit | `pytest tests/test_trace_jsonl.py -q` | W0 | pending |
| 29-01-T3 | 01 | 1 | IO-02 | T-29-03 | Duplicate fingerprint skips re-imports | unit | `pytest tests/test_trace_jsonl.py -q` | W0 | pending |
| 29-02-T1 | 02 | 2 | IO-01, IO-03 | T-29-01 | Sync export omits raw fields by default | integration | `pytest tests/test_trace_jsonl.py -q` | W0 | pending |
| 29-02-T2 | 02 | 2 | IO-02 | T-29-02, T-29-03 | Sync import appends valid traces and skips duplicates | integration | `pytest tests/test_trace_jsonl.py -q` | W0 | pending |
| 29-03-T1 | 03 | 2 | IO-01, IO-03 | T-29-01 | Async export matches sync JSONL semantics | integration | `pytest tests/test_trace_jsonl.py -q` | W0 | pending |
| 29-03-T2 | 03 | 2 | IO-02 | T-29-02, T-29-03 | Async import matches sync result counts | integration | `pytest tests/test_trace_jsonl.py -q` | W0 | pending |
| 29-04-T1 | 04 | 3 | IO-01, IO-03 | T-29-01 | Docs make raw export opt-in explicit | docs | `pytest tests/test_docstrings.py -q` | W0 | pending |
| 29-04-T2 | 04 | 3 | IO-01, IO-02, IO-03 | T-29-01, T-29-02, T-29-03 | Compatibility tests remain green | regression | `pytest tests/test_trace_jsonl.py tests/test_trace_capture.py tests/test_backend_contract.py tests/test_docstrings.py -q` | W0 | pending |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have automated verification or Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all missing references.
- [x] No watch-mode flags.
- [x] Feedback latency < 30s.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-05-04
