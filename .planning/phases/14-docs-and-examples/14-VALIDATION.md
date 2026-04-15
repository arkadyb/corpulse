---
phase: 14
slug: docs-and-examples
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/ -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -q`
- **After every plan wave:** Run `pytest tests/ -q && python examples/async-demo/demo.py`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | ASYNC-DOC-02 | — | N/A | unit | `pytest tests/test_docstrings.py -q` | ✅ (needs extension) | ⬜ pending |
| 14-01-02 | 01 | 1 | ASYNC-DOC-01 | — | N/A | smoke | `python -c "import pathlib; txt=pathlib.Path('README.md').read_text(); assert 'Async usage' in txt"` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 1 | ASYNC-DOC-03 | — | N/A | smoke | `python examples/async-demo/demo.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `examples/async-demo/demo.py` — stubs for ASYNC-DOC-03
- [ ] Extension of `tests/test_docstrings.py` — covers ASYNC-DOC-02 for `AsyncCorpulse`

*Existing infrastructure covers remaining phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| README async section reads well and is accurate | ASYNC-DOC-01 | Content quality is subjective | Read the section; verify code snippets match actual API |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
