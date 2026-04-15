---
phase: 16
slug: postgres-multi-tenancy
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-15
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for Postgres tenancy refactoring.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (with pytest-asyncio, already configured) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_postgres_backend.py tests/test_async_postgres_backend.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~5 seconds quick / full suite per project norms |

---

## Sampling Rate

- **After wave 0 / shared helper changes:** run targeted backend tests
- **After each plan wave:** run `pytest tests/test_postgres_backend.py tests/test_async_postgres_backend.py -x`
- **Before phase sign-off:** run `pytest`
- **Max feedback latency:** under 10 seconds for targeted runs

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 16-01-01 | 01 | 0 | PGMT-03 | unit | `pytest tests/test_postgres_backend.py -k "schema_sql or identifier" -x` | ⬜ pending |
| 16-01-02 | 01 | 0 | PGMT-04 | unit | `pytest tests/test_postgres_backend.py -k "identifier" -x` | ⬜ pending |
| 16-02-01 | 02 | 1 | PGMT-01 | unit/integration | `pytest tests/test_postgres_backend.py -x` | ⬜ pending |
| 16-02-02 | 02 | 1 | PGMT-02 | unit/integration | `pytest tests/test_async_postgres_backend.py -x` | ⬜ pending |
| 16-03-01 | 03 | 2 | PGMT-05 | integration | `pytest tests/test_postgres_backend.py tests/test_async_postgres_backend.py -x` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] direct tests for `build_schema_sql(schema=None, prefix="")`
- [ ] direct tests for invalid `schema` and `table_prefix` rejection

---

## Manual-Only Verifications

All planned phase behaviors have automated verification paths. Live per-schema isolation should stay behind any existing Postgres env gate if real DB setup is required.

---

## Validation Sign-Off

- [x] All tasks have automated verification
- [x] Sampling continuity maintained
- [x] Wave 0 covers identifier and DDL builder risks
- [x] No watch-mode flags
- [x] Feedback latency < 10s for targeted runs
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready for execution
