---
phase: 07
slug: postgresbackend-sync
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-09
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_postgres_backend.py tests/test_import.py tests/test_package.py -q` |
| **Full suite command** | `pytest tests -q` |
| **Estimated runtime** | ~20 seconds without live Postgres, ~35 seconds with live parity enabled |

---

## Sampling Rate

- **After every task commit:** Run the task's own `<automated>` command from the active PLAN.
- **After Task 1:** Run `pytest tests/test_postgres_backend.py tests/test_import.py tests/test_package.py -q`
- **After Task 2 with live PostgreSQL available:** Run `CORPULSE_POSTGRES_TEST_CONNINFO=... pytest tests/test_backend_contract.py tests/test_core_backend_integration.py tests/test_postgres_backend.py -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 35 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | BACK-04 / INT-02 | unit + package smoke | `pytest tests/test_postgres_backend.py tests/test_import.py tests/test_package.py -q` | ✅ after task | ⬜ pending |
| 07-01-02 | 01 | 1 | BACK-04 | live parity | `CORPULSE_POSTGRES_TEST_CONNINFO=... pytest tests/test_backend_contract.py tests/test_core_backend_integration.py tests/test_postgres_backend.py -q` | ✅ after task | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Execution Prerequisites

- No separate Wave 0 is required.
- Live PostgreSQL parity coverage requires `CORPULSE_POSTGRES_TEST_CONNINFO` to be set to a reachable test database.
- When that env var is absent, Postgres live tests must skip cleanly rather than failing the suite.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Validate a consumer can actually connect using their chosen psycopg implementation (`python`, `c`, or `binary`) | INT-02 | Repo tests can verify declared dependency and lazy imports, but not every downstream deployment combination | Install `corpulse[postgres]` in a clean environment, instantiate `PostgresBackend(conninfo="...")`, then run a minimal `Corpulse.log_retrieval()` / `get_ghosts()` flow against a real PostgreSQL instance |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify and no unresolved wave-0 dependency
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Live integration dependency is explicit and bounded to an env var
- [x] No watch-mode flags
- [x] Feedback latency < 35s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-09
