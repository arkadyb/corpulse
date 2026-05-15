---
phase: 34
slug: optional-extras-install-verification
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-15
---

# Phase 34 - Validation Strategy

> Per-phase validation contract for optional extras and artifact install checks.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_import.py tests/test_package.py` |
| **Full suite command** | `python -m pytest tests/test_package.py tests/test_import.py tests/test_distribution_installs.py` |
| **Estimated runtime** | ~60-180 seconds when isolated install tests run |

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_import.py tests/test_package.py`
- **After every plan wave:** Run the plan-specific focused command.
- **Before `$gsd-verify-work`:** Build artifacts and gated isolated install tests must pass.
- **Max feedback latency:** 180 seconds for install-matrix tasks.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 34-01-T1 | 01 | 1 | PKG-04, EXTRA-02 | T34-01 | Base install does not include optional packages | integration | `CORPULSE_RUN_INSTALL_TESTS=1 python -m pytest tests/test_distribution_installs.py` | no | pending |
| 34-01-T2 | 01 | 1 | PKG-04, EXTRA-02 | T34-01 | Built wheel imports cleanly in a fresh venv | integration | `CORPULSE_RUN_INSTALL_TESTS=1 python -m pytest tests/test_distribution_installs.py` | no | pending |
| 34-02-T1 | 02 | 2 | EXTRA-01, EXTRA-04 | T34-02 | Optional extras install only when requested | integration | `CORPULSE_RUN_INSTALL_TESTS=1 python -m pytest tests/test_distribution_installs.py` | no | pending |
| 34-02-T2 | 02 | 2 | EXTRA-01, EXTRA-04 | T34-02 | Qdrant wrapper surface imports from extra install | integration | `CORPULSE_RUN_INSTALL_TESTS=1 python -m pytest tests/test_distribution_installs.py` | no | pending |
| 34-03-T1 | 03 | 3 | EXTRA-03 | T34-03 | Missing extras return actionable install commands | unit | `python -m pytest tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_fastapi.py tests/test_report_helpers.py` | yes | pending |
| 34-03-T2 | 03 | 3 | EXTRA-03 | T34-03 | User docs mention install constraints clearly | static | `python -m pytest tests/test_package.py` | yes | pending |

## Wave 0 Requirements

- [ ] `tests/test_distribution_installs.py` - isolated venv install test module.
- [ ] `dist/*.whl` - built artifact from Phase 33 or current `python -m build`.
- [ ] `build` and `twine` tooling available through active environment or `/tmp/corpulse-gsd-tools`.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | N/A | N/A | All phase behaviors have automated verification. |

## Validation Sign-Off

- [x] All tasks have automated verification commands.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all missing references.
- [x] No watch-mode flags.
- [x] Feedback latency < 180s.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-05-15
