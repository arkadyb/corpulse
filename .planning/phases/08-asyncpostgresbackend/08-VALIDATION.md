---
phase: 08
slug: asyncpostgresbackend
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-09
updated: 2026-04-09
---

# Phase 08 — Validation Strategy

> Final validation map for the shipped async Postgres backend and its recorded proof.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.x` + `pytest-asyncio 1.3.0` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_async_postgres_backend.py tests/test_import.py -q` |
| **Full suite command** | `pytest tests/test_async_postgres_backend.py tests/test_package.py tests/test_import.py -q` |
| **Estimated runtime** | ~5 seconds local; live async run depends on Postgres availability |

---

## Sampling Rate

- **After implementation changes touching async Postgres:** Run `pytest tests/test_async_postgres_backend.py tests/test_import.py -q`
- **Before closing backend packaging or extras claims:** Run `pytest tests/test_package.py -q`
- **Before closing shared parity/live proof:** Run `CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test pytest tests/test_backend_contract.py tests/test_core_backend_integration.py -q`
- **Before milestone closure:** Ensure `.planning/phases/08-asyncpostgresbackend/08-VERIFICATION.md` records the deterministic and live command outcomes

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | BACK-05 | unit/integration | `pytest tests/test_async_postgres_backend.py -q` | ✅ | ✅ green |
| 08-01-02 | 01 | 1 | INT-02 | package | `pytest tests/test_package.py -q` | ✅ | ✅ green |
| 08-01-03 | 01 | 1 | INT-03 | import/lazy-load | `pytest tests/test_import.py -q` | ✅ | ✅ green |
| 08-01-04 | 01 | 1 | BACK-05 | parity/live | `CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test pytest tests/test_backend_contract.py tests/test_core_backend_integration.py -q` | ✅ | ✅ green |

*Status: ✅ green = command executed and recorded*

---

## Wave 0 Requirements

- [x] `tests/test_async_postgres_backend.py` exists and passed deterministic plus live async backend coverage on 2026-04-09
- [x] `tests/conftest.py` exposes the env-gated `async_backend` fixture branch keyed by `CORPULSE_POSTGRES_TEST_CONNINFO`
- [x] `.planning/phases/08-asyncpostgresbackend/08-VERIFICATION.md` exists with executable proof fields

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live async Postgres round-trip | BACK-05 | Requires reachable Postgres and `CORPULSE_POSTGRES_TEST_CONNINFO` in the executing shell | `CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test pytest tests/test_async_postgres_backend.py -q` |

The live command remains env-gated even though it passed in this refresh run.

---

## Validation Sign-Off

- [x] All planned tasks map to executed automated commands
- [x] Sampling continuity preserved with executable pytest commands
- [x] Wave 0 placeholders replaced with shipped artifacts
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed on 2026-04-09
