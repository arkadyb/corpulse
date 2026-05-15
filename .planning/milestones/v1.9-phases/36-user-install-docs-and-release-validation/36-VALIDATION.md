---
phase: 36
slug: user-install-docs-and-release-validation
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-15
updated: 2026-05-15
---

# Phase 36 - Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_package.py tests/test_release_workflow.py` |
| **Full suite command** | `python -m pytest` |
| **Estimated runtime** | ~30 seconds for quick docs/release tests |

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_package.py tests/test_release_workflow.py`
- **After every plan wave:** Run `python -m pytest`
- **Before `$gsd-verify-work`:** Full suite must be green, local build must succeed, and published-package manual checks must be recorded if a real release was performed.
- **Max feedback latency:** 30 seconds for quick checks, excluding external publish smoke tests.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 36-01-T1 | 01 | 1 | DOC-01, DOC-02 | T36-01 | Install docs stay PyPI-first and do not reintroduce unpublished/source-first guidance. | static docs | `python -m pytest tests/test_package.py` | Yes | green |
| 36-01-T2 | 01 | 1 | DOC-03 | T36-02, T36-03 | Release checklist uses Trusted Publishing and no API-token flow. | static docs | `python -m pytest tests/test_release_workflow.py` | Yes | green |
| 36-02-T1 | 02 | 2 | VAL-01 | T36-04 | Base published install smoke is exact and isolated. | static docs/manual | `python -m pytest tests/test_release_workflow.py` | Yes | green |
| 36-02-T2 | 02 | 2 | VAL-02 | T36-05 | Qdrant extra published install smoke verifies wrapper import surface. | static docs/manual | `python -m pytest tests/test_release_workflow.py` | Yes | green |
| 36-02-T3 | 02 | 2 | DOC-01, DOC-02, DOC-03, VAL-01, VAL-02 | T36-06 | Local artifacts are buildable and install-testable before external publish. | integration | `CORPULSE_RUN_INSTALL_TESTS=1 python -m pytest tests/test_distribution_installs.py` | Yes | green |

## Wave 0 Requirements

Existing infrastructure covers all phase requirements:

- `tests/test_package.py`
- `tests/test_release_workflow.py`
- `tests/test_distribution_installs.py`
- `pyproject.toml`

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Published base package installs from PyPI. | VAL-01 | Requires package to exist on PyPI after release. | Run the base PyPI smoke commands documented in `.github/RELEASE_CHECKLIST.md`. |
| Published Qdrant extra installs from PyPI and exposes wrapper classes. | VAL-02 | Requires package to exist on PyPI after release. | Run the Qdrant PyPI smoke commands documented in `.github/RELEASE_CHECKLIST.md`. |
| TestPyPI package can be installed before production publish. | DOC-03 | Requires a TestPyPI publish event. | Run the TestPyPI validation command documented in `.github/RELEASE_CHECKLIST.md`. |

## Validation Sign-Off

- [x] All tasks have automated static verification or explicit manual checkpoints.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all missing references.
- [x] No watch-mode flags.
- [x] Feedback latency < 30 seconds for quick checks.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** pending
