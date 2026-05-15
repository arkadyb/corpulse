---
phase: 35
slug: trusted-publishing-release-automation
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-15
updated: 2026-05-15
---

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_release_workflow.py` |
| **Full suite command** | `python -m pytest tests/test_release_workflow.py tests/test_package.py` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_release_workflow.py`
- **After every plan wave:** Run `python -m pytest tests/test_release_workflow.py tests/test_package.py`
- **Before `$gsd-verify-work`:** Full suite must be green, and `python -m build` must succeed
- **Max feedback latency:** 30 seconds for static tests, plus build time

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 35-01-T1 | 35-01 | 1 | REL-01 | T35-01 | Build job has no OIDC publish permission | static | `python -m pytest tests/test_release_workflow.py -k build` | ✅ W0 | ✅ green |
| 35-01-T2 | 35-01 | 1 | REL-01 | T35-02 | Release artifacts are built once and uploaded from `dist/*` | static/build | `python -m pytest tests/test_release_workflow.py tests/test_package.py` | ✅ W0 | ✅ green |
| 35-02-T1 | 35-02 | 2 | REL-02 | T35-03 | TestPyPI publish uses OIDC Trusted Publishing and no token secret | static | `python -m pytest tests/test_release_workflow.py -k testpypi` | ✅ W0 | ✅ green |
| 35-02-T2 | 35-02 | 2 | REL-02 | T35-04 | Trusted publisher setup values are documented | static | `python -m pytest tests/test_release_workflow.py -k trusted_publishing` | ✅ W0 | ✅ green |
| 35-03-T1 | 35-03 | 3 | REL-03 / REL-04 | T35-05 | PyPI publish is tag-gated and environment-gated | static | `python -m pytest tests/test_release_workflow.py -k pypi` | ✅ W0 | ✅ green |
| 35-03-T2 | 35-03 | 3 | REL-03 / REL-04 | T35-06 | No long-lived PyPI token is referenced | static | `python -m pytest tests/test_release_workflow.py` | ✅ W0 | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TestPyPI trusted publisher exists | REL-02 | PyPI/TestPyPI project settings live outside the repository | Configure TestPyPI publisher with owner `arkadyb`, repository `corpulse`, workflow `release.yml`, environment `testpypi`, then run workflow dispatch when ready. |
| PyPI trusted publisher exists | REL-03 | PyPI project settings live outside the repository | Configure PyPI publisher with owner `arkadyb`, repository `corpulse`, workflow `release.yml`, environment `pypi`, before pushing a release tag. |
| `pypi` environment has required reviewers or equivalent gate | REL-04 | GitHub environment protection rules live outside the repository | In GitHub repository settings, create or update `pypi` environment with required reviewers or equivalent explicit approval before first real release. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30 seconds for static tests
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
