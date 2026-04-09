---
phase: 10
slug: async-backend-corpulse-integration
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-09
updated: 2026-04-09
---

# Phase 10 — Validation Strategy

> Final validation map for the async corpulse integration path and its recorded proof.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.x` + `pytest-asyncio 1.3.0` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_async_core_integration.py tests/test_async_postgres_backend.py tests/test_import.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After AsyncCorpulse changes:** Run `pytest tests/test_async_core_integration.py tests/test_async_postgres_backend.py tests/test_import.py -q`
- **Before closing live async integration proof:** Run `CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test pytest tests/test_async_core_integration.py -q`
- **Before closing roadmap/requirement traceability:** Ensure `.planning/phases/10-async-backend-corpulse-integration/10-VERIFICATION.md` records executed deterministic and live commands with observed outcomes

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | BACK-05 | integration | `pytest tests/test_async_core_integration.py -q` | ✅ | ✅ green |
| 10-01-02 | 01 | 1 | BACK-05 | import/lazy-load | `pytest tests/test_import.py -q` | ✅ | ✅ green |
| 10-02-01 | 02 | 2 | INT-03 | backend/integration | `pytest tests/test_async_core_integration.py tests/test_async_postgres_backend.py tests/test_import.py -q` | ✅ | ✅ green |
| 10-02-02 | 02 | 2 | BACK-05 | live integration | `CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test pytest tests/test_async_core_integration.py -q` | ✅ | ✅ green |

*Status: ✅ green = command executed and recorded*

---

## Wave 0 Requirements

- [x] `tests/test_async_core_integration.py` proves the corpulse-facing async flow and facade lifecycle
- [x] `corpulse/async_core.py` provides the supported `AsyncCorpulse` integration path
- [x] `corpulse/__init__.py` exports `AsyncCorpulse` without eager optional-driver import
- [x] `.planning/phases/08-asyncpostgresbackend/08-VERIFICATION.md` exists
- [x] `.planning/phases/08-asyncpostgresbackend/08-VALIDATION.md` is finalized
- [x] `.planning/phases/10-async-backend-corpulse-integration/10-VERIFICATION.md` exists with explicit live async command proof

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live async corpulse flow reaches a real Postgres database through `AsyncCorpulse` | BACK-05, INT-03 | Requires reachable Postgres and `CORPULSE_POSTGRES_TEST_CONNINFO` in the executing shell | `CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test pytest tests/test_async_core_integration.py -q` |

The live command is env-gated, but it was executed successfully during this plan refresh.

---

## Validation Sign-Off

- [x] All final tasks map to executed automated commands
- [x] The final two-plan structure contains only `10-01-01`, `10-01-02`, `10-02-01`, and `10-02-02`
- [x] No third-plan task rows remain
- [x] Wave 0 placeholders replaced with shipped artifacts and evidence
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed on 2026-04-09
