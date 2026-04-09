---
phase: 06
slug: storage-foundation
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-08
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_backend_contract.py tests/test_core_backend_integration.py -q` |
| **Full suite command** | `pytest tests -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task's own `<automated>` command from the active PLAN.
- **After wave 1 (06-01):** Run `pytest tests/test_backend_contract.py tests/test_core_backend_integration.py -q`
- **After wave 2 (06-02):** Run `pytest tests/test_backend_contract.py tests/test_core_backend_integration.py tests/test_analytics.py tests/test_qdrant_wrapper.py tests/test_import.py tests/test_package.py -q`
- **After wave 3 (06-03):** Run `pytest tests/test_backend_contract.py tests/test_core_backend_integration.py tests/test_analytics.py -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | ABS-01/ABS-02/ABS-03 | unit | `python - <<'PY' ... PY` contract probe from `06-01` Task 1 | ✅ after task | ⬜ pending |
| 06-01-02 | 01 | 1 | scaffolding for later ABS-04/INT-01 | unit | `pytest tests/test_backend_contract.py tests/test_core_backend_integration.py -q` | ✅ after task | ⬜ pending |
| 06-02-01 | 02 | 2 | BACK-01/BACK-02 | regression | `pytest tests/test_backend_contract.py tests/test_analytics.py tests/test_qdrant_wrapper.py -q` | ✅ | ⬜ pending |
| 06-02-02 | 02 | 2 | INT-01/BACK-06 | regression | `pytest tests/test_core_backend_integration.py tests/test_analytics.py tests/test_qdrant_wrapper.py tests/test_import.py tests/test_package.py -q` | ✅ | ⬜ pending |
| 06-03-01 | 03 | 3 | BACK-03/BACK-06 | unit | `python - <<'PY' ... PY` direct `InMemoryBackend` parity probe from `06-03` Task 1 | ✅ after task | ⬜ pending |
| 06-03-02 | 03 | 3 | ABS-04 | regression | `pytest tests/test_backend_contract.py tests/test_core_backend_integration.py tests/test_analytics.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Execution Prerequisites

- No separate wave 0 is required after revision.
- `06-01` creates passing scaffolding only; SQLite activation happens in `06-02`, and full all-backend parity happens in `06-03`.
- `06-03` Task 1 verifies `InMemoryBackend` directly before shared pytest fixture activation expands in Task 2.
- SQLite-private assertions remain in `tests/test_qdrant_wrapper.py`; parity coverage must not absorb `_conn()` or WAL-specific checks.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify and no unresolved wave-0 dependency
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave/task ordering matches `06-01 -> 06-02 -> 06-03`
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-08
