# Phase 13: Live Async Integration Tests - Research

**Researched:** 2026-04-10 [VERIFIED: local system date]
**Domain:** Live `pytest` integration coverage for `AsyncCorpulse` report surfaces against real PostgreSQL via `asyncpg`. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`]
**Confidence:** HIGH [VERIFIED: codebase audit, local environment audit, official docs, PyPI registry]

<user_constraints>
## User Constraints (from CONTEXT.md)

No phase-specific `CONTEXT.md` exists for Phase 13, so there are no additional locked decisions, discretion notes, or deferred ideas beyond the roadmap and requirements already loaded. [VERIFIED: `node ~/.codex/get-shit-done/bin/gsd-tools.cjs init phase-op 13` output]
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ASYNC-TEST-03 | Live `asyncpg` integration tests gated by `CORPULSE_POSTGRES_TEST_CONNINFO` must exercise `to_dataframe`, `report`, and `cleanup_report` end to end against a real PostgreSQL instance. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`] | Extend [`tests/test_async_core_integration.py`](/Users/arkady/src/corpulse/tests/test_async_core_integration.py) with env-gated live tests that seed a real `AsyncPostgresBackend`, call all three parity methods, and assert stable payload shape plus key values while preserving clean skip behavior when the DSN is absent. [VERIFIED: `tests/conftest.py`, `tests/test_async_core_integration.py`, `.planning/ROADMAP.md`] |
</phase_requirements>

## Summary

Phase 13 should not introduce new infrastructure or new libraries. [VERIFIED: `pyproject.toml`, `tests/conftest.py`] The repo already has the exact building blocks needed: `AsyncCorpulse` implements `to_dataframe()`, `report()`, and `cleanup_report()`; `AsyncPostgresBackend` is already live-tested; and [`tests/conftest.py`](/Users/arkady/src/corpulse/tests/conftest.py) already provides an env-gated `async_backend` fixture that truncates the three PostgreSQL tables before and after each test. [VERIFIED: `corpulse/async_core.py`, `corpulse/backends/postgres_async.py`, `tests/conftest.py`, `tests/test_async_postgres_backend.py`]

The planning focus is test design and isolation. [VERIFIED: `.planning/ROADMAP.md`, local live-test audit on 2026-04-10] The new live coverage belongs in [`tests/test_async_core_integration.py`](/Users/arkady/src/corpulse/tests/test_async_core_integration.py), should reuse the existing `async_backend` fixture, and should seed deterministic rows before asserting on `to_dataframe()`, `report()`, and `cleanup_report()`. [VERIFIED: `tests/test_async_core_integration.py`, `tests/conftest.py`] Because pandas is still optional in this project, the live `to_dataframe()` path should reuse the existing fake-pandas import shim instead of adding pandas as a hard dependency or skipping the test when pandas is missing. [VERIFIED: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `tests/test_async_core_integration.py`, local module probe showing `pandas: no`]

The main hidden risk is database contamination across concurrent live commands. [VERIFIED: local live-test audit on 2026-04-10] Running `tests/test_async_postgres_backend.py` and `tests/test_async_core_integration.py` in parallel against the same DSN produced cross-test row leakage, while rerunning them sequentially against `postgresql://postgres:postgres@localhost:5432/corpulse_test` passed cleanly. [VERIFIED: local parallel and sequential pytest runs on 2026-04-10] The plan should therefore treat the live PostgreSQL database as a sequential shared resource unless it also introduces database-per-process isolation. [VERIFIED: `tests/conftest.py`, local live-test audit on 2026-04-10]

**Primary recommendation:** Add deterministic, env-gated live tests to [`tests/test_async_core_integration.py`](/Users/arkady/src/corpulse/tests/test_async_core_integration.py) using the existing `async_backend` fixture, Phase 12 report fixtures for expected values, fake-pandas for `to_dataframe()`, and sequential verification commands only. [VERIFIED: `tests/conftest.py`, `tests/test_async_core_integration.py`, `tests/report_fixtures.py`, local live-test audit on 2026-04-10]

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pytest` | `9.0.3` latest on PyPI; `9.0.2` installed locally. [VERIFIED: PyPI JSON `https://pypi.org/pypi/pytest/json`, local `pytest --version`] | Test runner for unit and live integration suites. [VERIFIED: `pyproject.toml`, `tests/`] | The repo is already standardized on `pytest`, and the live phase only extends existing pytest coverage rather than introducing another runner. [VERIFIED: `pyproject.toml`, `tests/`] |
| `pytest-asyncio` | `1.3.0`. [VERIFIED: PyPI JSON `https://pypi.org/pypi/pytest-asyncio/json`, local import version] | Async test and fixture support for `async def` tests and async fixtures. [VERIFIED: `pyproject.toml`, `tests/conftest.py`] | The project already configures `asyncio_mode = "auto"`, which matches the existing async test style in this repo. [VERIFIED: `pyproject.toml`, `tests/test_async_core_integration.py`, [CITED: https://pytest-asyncio.readthedocs.io/en/stable/reference/configuration.html]] |
| `asyncpg` | `0.31.0`. [VERIFIED: PyPI JSON `https://pypi.org/pypi/asyncpg/json`, local import version] | Real async PostgreSQL driver and connection pool used by `AsyncPostgresBackend`. [VERIFIED: `corpulse/backends/postgres_async.py`] | The phase requirement explicitly says the live integration path must go through a real Postgres instance via `asyncpg`, and the backend already uses `asyncpg.create_pool(...)`. [VERIFIED: `.planning/REQUIREMENTS.md`, `corpulse/backends/postgres_async.py`, [CITED: https://magicstack.github.io/asyncpg/current/usage.html]] |
| PostgreSQL | Local environment currently has `postgres:16` / `16.13` in Docker. [VERIFIED: `docker inspect corpulse-pg`] | Real datastore for end-to-end async integration coverage. [VERIFIED: `.planning/REQUIREMENTS.md`, `tests/conftest.py`] | The phase exists specifically to close the gap between fake-backend parity tests and a real database round trip. [VERIFIED: `.planning/ROADMAP.md`, `tests/test_async_postgres_backend.py`] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `psycopg` | `3.3.3` locally and on PyPI. [VERIFIED: PyPI JSON `https://pypi.org/pypi/psycopg/json`, local import version] | Sync Postgres tests and sync backend fixtures already in the repo. [VERIFIED: `tests/conftest.py`, `corpulse/backends/postgres.py`] | Use only as context for existing sync Postgres coverage; Phase 13 itself targets the async path. [VERIFIED: `.planning/REQUIREMENTS.md`, `tests/test_core_backend_integration.py`] |
| Docker | `29.3.1` locally. [VERIFIED: local `docker --version`] | Practical local fallback when the DSN env var is unset but a developer still needs a live Postgres instance. [VERIFIED: local environment audit] | Use as setup support only; tests themselves should still connect through `CORPULSE_POSTGRES_TEST_CONNINFO`. [VERIFIED: `tests/conftest.py`] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reusing `tests/test_async_core_integration.py`. [VERIFIED: `.planning/ROADMAP.md` success criteria references this file] | Create a brand-new live-only async test module. [ASSUMED] | A separate file would work technically, but it would diverge from the roadmap’s explicit verification command and split async behavior across two files for little gain. [VERIFIED: `.planning/ROADMAP.md`] |
| Existing env-gated fixture plus table truncation. [VERIFIED: `tests/conftest.py`] | `pytest-postgresql`, Testcontainers, or a bespoke DB lifecycle harness. [ASSUMED] | Those add setup complexity the repo does not currently need, because function-scoped live fixtures and Docker-backed DSNs are already established here. [VERIFIED: `tests/conftest.py`, `tests/test_async_postgres_backend.py`, local Docker audit] |
| Fake-pandas import shim for live `to_dataframe()` coverage. [VERIFIED: `tests/test_async_core_integration.py`, local `pandas: no`] | Install pandas as a required dev dependency for live tests. [ASSUMED] | Making pandas mandatory would contradict the locked project decision that pandas remains optional. [VERIFIED: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`] |

**Installation:**
```bash
pip install "corpulse[postgres-async]" ".[dev]"
```
[VERIFIED: `pyproject.toml`]

**Version verification:** Verify current versions before implementation with:
```bash
python3 -m pip index versions pytest
python3 -m pip index versions pytest-asyncio
python3 -m pip index versions asyncpg
```
[VERIFIED: local `pip index versions` audit on 2026-04-10]

Verified current latest versions and first upload timestamps on 2026-04-10: [VERIFIED: PyPI JSON `https://pypi.org/pypi/pytest/json`, `https://pypi.org/pypi/pytest-asyncio/json`, `https://pypi.org/pypi/asyncpg/json`]
- `pytest 9.0.3` published `2026-04-07T17:16:16Z`. [VERIFIED: PyPI JSON `https://pypi.org/pypi/pytest/json`]
- `pytest-asyncio 1.3.0` published `2025-11-10T16:07:45Z`. [VERIFIED: PyPI JSON `https://pypi.org/pypi/pytest-asyncio/json`]
- `asyncpg 0.31.0` published `2025-11-24T23:25:23Z`. [VERIFIED: PyPI JSON `https://pypi.org/pypi/asyncpg/json`]

## Architecture Patterns

### Recommended Project Structure
```text
tests/
├── conftest.py                      # env-gated async_backend fixture with truncate setup/teardown
├── report_fixtures.py              # deterministic Phase 12 expected payload builders
└── test_async_core_integration.py  # deterministic async tests plus Phase 13 live asyncpg coverage
```
[VERIFIED: `tests/conftest.py`, `tests/report_fixtures.py`, `tests/test_async_core_integration.py`]

### Pattern 1: Reuse the Existing `async_backend` Fixture for Every Live Test
**What:** Build all new live async integration tests on top of the existing async fixture that creates `AsyncPostgresBackend`, truncates `documents`, `retrievals`, and `engagements` before the test, then truncates again during teardown. [VERIFIED: `tests/conftest.py`, [CITED: https://docs.pytest.org/en/stable/how-to/fixtures.html]]

**When to use:** Use it for every live `AsyncCorpulse` integration test in this phase. [VERIFIED: `.planning/ROADMAP.md`, `tests/conftest.py`]

**Example:**
```python
# Source: tests/conftest.py
@pytest.fixture(params=_async_backend_params())
async def async_backend(request):
    if request.param == "skip":
        pytest.skip("requires CORPULSE_POSTGRES_TEST_CONNINFO and asyncpg")

    from corpulse.backends import AsyncPostgresBackend

    backend = await AsyncPostgresBackend.create(
        os.environ["CORPULSE_POSTGRES_TEST_CONNINFO"]
    )
    async with backend._pool.acquire() as conn:
        await conn.execute("TRUNCATE engagements, retrievals, documents RESTART IDENTITY")
    try:
        yield backend
    finally:
        async with backend._pool.acquire() as conn:
            await conn.execute(
                "TRUNCATE engagements, retrievals, documents RESTART IDENTITY"
            )
        await backend.close()
```
[VERIFIED: `tests/conftest.py`]

### Pattern 2: Seed Real PostgreSQL With Deterministic AsyncCorpulse Inputs, Then Compare Against Phase 12 Expectations
**What:** Reuse the Phase 12 frozen report fixture module as the source of expected rows and payloads, and add only the minimum extra helper needed to seed the live async backend with matching document, retrieval, and engagement rows. [VERIFIED: `tests/report_fixtures.py`, `tests/test_async_core_integration.py`]

**When to use:** Use this for the new live `to_dataframe()`, `report()`, and `cleanup_report()` tests so the live phase proves parity against the same canonical expectations already locked in Phase 12. [VERIFIED: `.planning/phases/12-async-parity-methods-unit-tests/12-VERIFICATION.md`, `tests/report_fixtures.py`]

**Example:**
```python
# Source pattern: existing fixtures + live async_backend fixture
async def _seed_live_report_fixture(corpulse):
    for row in document_seed_rows():
        await corpulse.register_document(
            row["doc_id"],
            row["filename"],
            embedding=row["embedding"],
        )
        await corpulse.log_source_update(
            row["doc_id"],
            updated_at=row["source_updated_at"],
        )
    for row in retrieval_seed_rows():
        await corpulse.db.insert_retrieval(
            row["doc_id"],
            row["query_hash"],
            row["rank"],
            row["score"],
            row["retrieved_at"],
        )
    for row in engagement_seed_rows():
        await corpulse.db.insert_engagement(
            row["doc_id"],
            row["event_type"],
            row["engaged_at"],
        )
```
[ASSUMED]

### Pattern 3: Keep `to_dataframe()` Live Coverage Independent of Real pandas
**What:** Reuse the existing fake-pandas import shim so the live `to_dataframe()` test exercises real Postgres reads without making pandas mandatory in the environment. [VERIFIED: `tests/test_async_core_integration.py`, `.planning/PROJECT.md`, local module probe showing `pandas: no`]

**When to use:** Use it in the live `to_dataframe()` test unless the project explicitly decides to install pandas in the test environment. [VERIFIED: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`]

**Example:**
```python
# Source: tests/test_async_core_integration.py
_install_fake_pandas(monkeypatch)
df = await corpulse.to_dataframe(window_days=30)
assert df.to_dict("records")[0]["doc_id"] == "healthy-a"
```
[VERIFIED: `tests/test_async_core_integration.py`]

### Pattern 4: Verify Live Suites Sequentially, Not in Parallel, Against One Shared DSN
**What:** Treat the PostgreSQL test database as a shared mutable resource and run live async suites sequentially unless the plan adds process-level isolation. [VERIFIED: local live-test audit on 2026-04-10]

**When to use:** Use this for verification commands, CI recommendations, and any local instructions in the phase plan. [VERIFIED: local live-test audit on 2026-04-10]

**Example:**
```bash
CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test \
pytest tests/test_async_postgres_backend.py -q

CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test \
pytest tests/test_async_core_integration.py -q
```
[VERIFIED: local sequential rerun on 2026-04-10]

### Anti-Patterns to Avoid
- **Adding pandas as a required dependency just for live tests:** This violates the project decision that pandas remains optional. [VERIFIED: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`]
- **Writing live tests that only assert “no exception”:** The roadmap requires shape and key-value assertions for `to_dataframe`, `report`, and `cleanup_report`. [VERIFIED: `.planning/ROADMAP.md`]
- **Parallelizing multiple live suites against the same DSN:** Local parallel runs caused row contamination and false failures. [VERIFIED: local live-test audit on 2026-04-10]
- **Duplicating expected report math inside the live tests:** Phase 12 already centralized expected payload logic in [`tests/report_fixtures.py`](/Users/arkady/src/corpulse/tests/report_fixtures.py). [VERIFIED: `tests/report_fixtures.py`, `.planning/phases/12-async-parity-methods-unit-tests/12-VERIFICATION.md`]
- **Creating a new fixture stack when `async_backend` already does the required setup and teardown:** That adds more stateful teardown surface without closing any gap. [VERIFIED: `tests/conftest.py`, [CITED: https://docs.pytest.org/en/stable/how-to/fixtures.html]]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Live async backend setup. [VERIFIED: codebase] | A new ad hoc connection helper inside the test module. [VERIFIED: `tests/conftest.py`] | The existing `async_backend` fixture in [`tests/conftest.py`](/Users/arkady/src/corpulse/tests/conftest.py). [VERIFIED: `tests/conftest.py`] | It already centralizes DSN gating, backend creation, cleanup, and close behavior. [VERIFIED: `tests/conftest.py`] |
| Expected report payloads. [VERIFIED: codebase] | Manually reconstructed dicts for every live test. [VERIFIED: `tests/report_fixtures.py`] | `helper_inputs(...)` and `expected_report_payload(...)` from [`tests/report_fixtures.py`](/Users/arkady/src/corpulse/tests/report_fixtures.py). [VERIFIED: `tests/report_fixtures.py`] | These functions already encode the Phase 12 parity contract and reduce drift between deterministic and live suites. [VERIFIED: `tests/report_fixtures.py`, `.planning/phases/12-async-parity-methods-unit-tests/12-VERIFICATION.md`] |
| Optional pandas handling. [VERIFIED: project decision + local env] | Conditional skip of the live `to_dataframe()` test whenever pandas is absent. [ASSUMED] | Reuse `_install_fake_pandas(monkeypatch)` from [`tests/test_async_core_integration.py`](/Users/arkady/src/corpulse/tests/test_async_core_integration.py). [VERIFIED: `tests/test_async_core_integration.py`] | This preserves real DB coverage while honoring the optional dependency policy. [VERIFIED: `.planning/PROJECT.md`, local module probe showing `pandas: no`] |
| Pooling semantics. [VERIFIED: backend code] | A custom async connection pool or transaction wrapper for tests. [VERIFIED: `corpulse/backends/postgres_async.py`] | `asyncpg.create_pool(...)` through `AsyncPostgresBackend.create(...)`. [VERIFIED: `corpulse/backends/postgres_async.py`, [CITED: https://magicstack.github.io/asyncpg/current/usage.html]] | The backend already implements the supported pool lifecycle and is live-tested separately. [VERIFIED: `corpulse/backends/postgres_async.py`, `tests/test_async_postgres_backend.py`] |

**Key insight:** Phase 13 is a verification-and-isolation phase, not a new-logic phase. [VERIFIED: `.planning/ROADMAP.md`, `corpulse/async_core.py`] The work should stay concentrated in tests and possibly small shared test helpers. [VERIFIED: `tests/`, `corpulse/async_core.py`]

## Common Pitfalls

### Pitfall 1: Shared-Database Contamination Across Parallel Live Commands
**What goes wrong:** Live tests fail with unexpected extra rows even though each suite appears to truncate tables correctly. [VERIFIED: local live-test audit on 2026-04-10]
**Why it happens:** The current fixture isolates tests within one pytest process, but two separate pytest processes pointed at the same DSN can race and repopulate tables between assertions. [VERIFIED: `tests/conftest.py`, local live-test audit on 2026-04-10]
**How to avoid:** Run live suites sequentially or give each process its own database. [VERIFIED: local sequential rerun on 2026-04-10]
**Warning signs:** A full-file live run fails, but the single live test passes when rerun alone. [VERIFIED: local live-test audit on 2026-04-10]

### Pitfall 2: Accidentally Turning Optional pandas Into a Hidden Test Requirement
**What goes wrong:** The live `to_dataframe()` coverage fails on machines that otherwise have a valid async Postgres setup. [VERIFIED: local module probe showing `pandas: no`]
**Why it happens:** `AsyncCorpulse.to_dataframe()` imports pandas lazily and raises if pandas is unavailable. [VERIFIED: `corpulse/async_core.py`]
**How to avoid:** Reuse the fake-pandas shim in the live test or explicitly provision pandas in the phase environment if the user chooses that path. [VERIFIED: `tests/test_async_core_integration.py`, `.planning/PROJECT.md`]
**Warning signs:** The new live test errors before any payload assertion, with `RuntimeError("pip install pandas to use to_dataframe()")`. [VERIFIED: `corpulse/async_core.py`, `tests/test_async_core_integration.py`]

### Pitfall 3: Re-Seeding a Different Corpus Than the One Used for Expected Payloads
**What goes wrong:** The live assertions become flaky or misleading because the expected payload helpers and the real seeded database no longer describe the same corpus. [VERIFIED: `tests/report_fixtures.py`, `tests/test_async_core_integration.py`]
**Why it happens:** The Phase 12 expected payload builders are deterministic, but they currently seed an in-memory backend, not the live async backend directly. [VERIFIED: `tests/report_fixtures.py`]
**How to avoid:** Export raw seed rows or a shared seeding helper from [`tests/report_fixtures.py`](/Users/arkady/src/corpulse/tests/report_fixtures.py) and use it for both expected-value construction and live DB population. [ASSUMED]
**Warning signs:** The live test adds inline seed data instead of consuming shared fixture definitions. [VERIFIED: `tests/report_fixtures.py`, `tests/test_async_core_integration.py`]

### Pitfall 4: Asserting Too Little on `report()` and `cleanup_report()`
**What goes wrong:** The live tests pass even if payload shape or status labeling regresses. [VERIFIED: `.planning/ROADMAP.md`]
**Why it happens:** “No exception” checks do not exercise the user-visible contract for rows, sections, and counts. [VERIFIED: `.planning/ROADMAP.md`]
**How to avoid:** Assert on summary keys, representative row ordering/status fields, cleanup section counts, and representative `doc_id` members. [VERIFIED: `.planning/ROADMAP.md`, `tests/test_async_core_integration.py`] 
**Warning signs:** Assertions only check for `dict`/`DataFrame` type or non-empty output. [ASSUMED]

## Code Examples

Verified patterns from current code and official docs:

### Env-Gated Async Fixture With Safe Teardown
```python
# Source: tests/conftest.py
@pytest.fixture(params=_async_backend_params())
async def async_backend(request):
    if request.param == "skip":
        pytest.skip("requires CORPULSE_POSTGRES_TEST_CONNINFO and asyncpg")
    ...
    try:
        yield backend
    finally:
        ...
        await backend.close()
```
[VERIFIED: `tests/conftest.py`, [CITED: https://docs.pytest.org/en/stable/how-to/fixtures.html]]

### Existing Live AsyncCorpulse Pattern
```python
# Source: tests/test_async_core_integration.py
async def test_live_async_corpulse_round_trip(async_backend):
    corpulse = AsyncCorpulse(backend=async_backend, ghost_threshold_days=30)

    await corpulse.register_document("ghost-doc", "ghost.md")
    await corpulse.log_retrieval(
        [{"doc_id": "fresh-doc", "filename": "fresh.md", "score": 0.8}],
        query="status",
    )

    ghosts = await corpulse.get_ghosts()

    assert ghosts == [{"doc_id": "ghost-doc", "filename": "ghost.md"}]
```
[VERIFIED: `tests/test_async_core_integration.py`]

### asyncpg Pool Usage Pattern
```python
# Source: corpulse/backends/postgres_async.py
pool = await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)
async with pool.acquire() as conn:
    async with conn.transaction():
        await conn.execute(statement)
```
[VERIFIED: `corpulse/backends/postgres_async.py`, [CITED: https://magicstack.github.io/asyncpg/current/usage.html]]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| One live async smoke test only for `get_ghosts()`. [VERIFIED: `tests/test_async_core_integration.py`] | Live async integration must cover `to_dataframe()`, `report()`, and `cleanup_report()`. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`] | Milestone `v1.2`, defined `2026-04-10`. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/PROJECT.md`] | The live suite now has to prove report-surface correctness, not just basic async storage reachability. [VERIFIED: `.planning/ROADMAP.md`] |
| Deterministic fake-backend parity only for report surfaces. [VERIFIED: `.planning/phases/12-async-parity-methods-unit-tests/12-VERIFICATION.md`] | Deterministic parity stays, but a real-Postgres async layer now verifies the same methods end to end. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`] | Phase 13 after Phase 12 completion on `2026-04-10`. [VERIFIED: `.planning/STATE.md`, `.planning/ROADMAP.md`] | Regressions in real driver behavior, pool usage, and DB seeding become detectable. [VERIFIED: local environment audit, `tests/conftest.py`] |
| Local live verification as an isolated manual step. [VERIFIED: `.planning/phases/10-async-backend-corpulse-integration/10-VALIDATION.md`] | Phase 13 needs codified live assertions in the normal async integration test module. [VERIFIED: `.planning/ROADMAP.md`] | 2026-04-10. [VERIFIED: `.planning/ROADMAP.md`] | The evidence moves from “recorded once” to “runnable whenever the DSN is present.” [VERIFIED: `.planning/ROADMAP.md`] |

**Deprecated/outdated:**
- Relying on the old live `get_ghosts()` test alone is outdated for v1.2 because it does not exercise any of the newly added parity methods. [VERIFIED: `tests/test_async_core_integration.py`, `.planning/REQUIREMENTS.md`]
- Treating live runs as safely parallel against one shared DSN is outdated in this workspace because the local audit reproduced contamination under parallel execution. [VERIFIED: local live-test audit on 2026-04-10]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A separate live-only async test module would be net-worse than extending `tests/test_async_core_integration.py`. | Standard Stack → Alternatives Considered | Low. The planner could still choose a separate file if it also updates verification commands and keeps skip behavior intact. |
| A2 | Adding `pytest-postgresql`, Testcontainers, or similar harnesses is unnecessary for this phase. | Standard Stack → Alternatives Considered | Medium. If the target environment stops providing a stable DSN, the planner may need a stronger environment bootstrap story. |
| A3 | The best implementation is to export raw seed rows or a shared live seeder from `tests/report_fixtures.py`. | Architecture Patterns / Common Pitfalls | Low. The planner could instead keep a compact live-only seed helper if it still derives expected values from the same canonical fixture data. |
| A4 | Assertions that only check output type or non-emptiness are the main likely failure mode for under-specified live tests. | Common Pitfalls | Low. Even if the exact weak assertion shape differs, the planner should still require concrete row/section assertions. |

## Open Questions

1. **How much of the Phase 12 frozen report corpus should the live phase reuse?** [VERIFIED: `tests/report_fixtures.py`, `.planning/ROADMAP.md`]
   - What we know: Full reuse maximizes parity with existing expectations, but it requires a live seeding path that can recreate the deterministic rows in PostgreSQL. [VERIFIED: `tests/report_fixtures.py`, `tests/conftest.py`]
   - What's unclear: Whether the planner should seed the entire Phase 12 corpus or define a smaller live corpus that still covers ghost, obsolete, stale, suspect, and healthy cases. [ASSUMED]
   - Recommendation: Prefer a compact live corpus if it still covers every report/cleanup status needed by ASYNC-TEST-03; only reuse the full Phase 12 corpus if that reduces implementation complexity rather than increasing it. [ASSUMED]

2. **Should the live tests use AsyncCorpulse ingestion methods exclusively, or seed some rows through the backend for precision?** [VERIFIED: `corpulse/async_core.py`, `tests/test_async_core_integration.py`]
   - What we know: `register_document`, `log_retrieval`, and `log_source_update` are available, but raw backend inserts offer more direct timestamp control. [VERIFIED: `corpulse/async_core.py`, `corpulse/backends/postgres_async.py`]
   - What's unclear: Which balance gives the cleanest tests without obscuring the “end-to-end through AsyncCorpulse” requirement. [ASSUMED]
   - Recommendation: Use `AsyncCorpulse` ingestion methods where practical, and use backend inserts only when exact seeded timestamps or query hashes materially simplify the test. [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Test execution | ✓ [VERIFIED: local `python3 --version`] | `3.14.3` [VERIFIED: local `python3 --version`] | — |
| `pytest` | All phase verification | ✓ [VERIFIED: local `pytest --version`] | `9.0.2` installed [VERIFIED: local `pytest --version`] | — |
| `pytest-asyncio` | Async tests and async fixtures | ✓ [VERIFIED: local import probe] | `1.3.0` [VERIFIED: local import version] | — |
| `asyncpg` | Real async Postgres backend | ✓ [VERIFIED: local import probe] | `0.31.0` [VERIFIED: local import version] | None for this phase. [VERIFIED: `.planning/REQUIREMENTS.md`] |
| pandas | Live `to_dataframe()` assertions if using real pandas | ✗ [VERIFIED: local import probe] | — | Reuse fake-pandas shim in tests. [VERIFIED: `tests/test_async_core_integration.py`] |
| Docker | Local Postgres bootstrap | ✓ [VERIFIED: local `docker --version`] | `29.3.1` [VERIFIED: local `docker --version`] | — |
| PostgreSQL container | Real DB target for live tests in this workspace | ✓ [VERIFIED: `docker ps`, `docker inspect corpulse-pg`] | `postgres:16` / `16.13` [VERIFIED: `docker inspect corpulse-pg`] | Start or reuse a local Postgres container if absent. [ASSUMED] |
| `CORPULSE_POSTGRES_TEST_CONNINFO` env var | Enables live tests instead of skips | ✗ in current shell [VERIFIED: local env probe] | — | Export `postgresql://postgres:postgres@localhost:5432/corpulse_test` for the running local container. [VERIFIED: `docker inspect corpulse-pg`, `.planning/phases/10-async-backend-corpulse-integration/10-VALIDATION.md`] |

**Missing dependencies with no fallback:**
- None in this workspace, because `asyncpg`, Docker, and a running PostgreSQL container are already present. [VERIFIED: local environment audit on 2026-04-10]

**Missing dependencies with fallback:**
- `CORPULSE_POSTGRES_TEST_CONNINFO` is unset, so live tests currently skip by default. [VERIFIED: local env probe, current `pytest tests/test_async_core_integration.py -q` run] The local fallback is to export `postgresql://postgres:postgres@localhost:5432/corpulse_test`, which matches the running `corpulse-pg` container’s configured user, password, database, and published port. [VERIFIED: `docker inspect corpulse-pg`]
- pandas is absent, but the existing fake-pandas shim already covers the optional dependency branch. [VERIFIED: local import probe, `tests/test_async_core_integration.py`] 

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest 9.0.2` + `pytest-asyncio 1.3.0`. [VERIFIED: local versions, `pyproject.toml`] |
| Config file | [`pyproject.toml`](/Users/arkady/src/corpulse/pyproject.toml). [VERIFIED: `pyproject.toml`] |
| Quick run command | `pytest tests/test_async_core_integration.py -q`. [VERIFIED: `.planning/ROADMAP.md`, current suite behavior] |
| Full suite command | `CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test pytest tests/test_async_postgres_backend.py -q && CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test pytest tests/test_async_core_integration.py -q`. [VERIFIED: local sequential rerun on 2026-04-10] |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ASYNC-TEST-03 | With the DSN set, live async tests seed a real PostgreSQL backend and assert `to_dataframe()`, `report()`, and `cleanup_report()` shape plus key values. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`] | integration | `CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test pytest tests/test_async_core_integration.py -q`. [VERIFIED: `.planning/ROADMAP.md`, local live rerun] | ✅ existing target file; ❌ missing required live report-surface assertions. [VERIFIED: `tests/test_async_core_integration.py`] |

### Sampling Rate
- **Per task commit:** `pytest tests/test_async_core_integration.py -q`. [VERIFIED: current file contains all target async integration coverage]
- **Per wave merge:** `CORPULSE_POSTGRES_TEST_CONNINFO=postgresql://postgres:postgres@localhost:5432/corpulse_test pytest tests/test_async_core_integration.py -q`. [VERIFIED: `.planning/ROADMAP.md`, local live rerun]
- **Phase gate:** Run live async backend and live async corpulse suites sequentially before `/gsd-verify-work`. [VERIFIED: local parallel contamination and sequential pass audit on 2026-04-10]

### Wave 0 Gaps
- None in infrastructure terms. [VERIFIED: `pyproject.toml`, `tests/conftest.py`, `tests/test_async_core_integration.py`] Existing pytest, async fixture, async backend, and live Postgres setup are already present; the phase only needs new assertions and possibly shared test helpers. [VERIFIED: codebase audit]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no [VERIFIED: test phase scope in `.planning/ROADMAP.md`] | The phase does not add auth flows. [VERIFIED: `.planning/ROADMAP.md`] |
| V3 Session Management | no [VERIFIED: test phase scope in `.planning/ROADMAP.md`] | The phase does not manage user sessions. [VERIFIED: `.planning/ROADMAP.md`] |
| V4 Access Control | no [VERIFIED: test phase scope in `.planning/ROADMAP.md`] | The phase runs against a test database DSN, not multi-actor authorization logic. [VERIFIED: `.planning/ROADMAP.md`, `tests/conftest.py`] |
| V5 Input Validation | yes [VERIFIED: backend executes parameterized SQL with bound arguments] | Keep using parameterized driver calls through `asyncpg` rather than interpolated SQL in tests or helpers. [VERIFIED: `corpulse/backends/postgres_async.py`] |
| V6 Cryptography | no [VERIFIED: phase scope and codebase] | No cryptographic logic is introduced here. [VERIFIED: `.planning/ROADMAP.md`, `tests/`] |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Pointing `CORPULSE_POSTGRES_TEST_CONNINFO` at a non-test database and truncating live data. [VERIFIED: `tests/conftest.py`] | Tampering | Keep the DSN env-gated, prefer a dedicated `corpulse_test` database, and document the expected local DSN explicitly in the plan. [VERIFIED: `tests/conftest.py`, `docker inspect corpulse-pg`, `.planning/phases/10-async-backend-corpulse-integration/10-VALIDATION.md`] |
| Credential leakage through hard-coded DSNs in committed test files. [VERIFIED: current tests use env vars, not literals in code paths] | Information Disclosure | Continue reading credentials from `CORPULSE_POSTGRES_TEST_CONNINFO` instead of embedding secrets in test code. [VERIFIED: `tests/conftest.py`, `tests/test_async_postgres_backend.py`] |
| SQL injection via raw string interpolation in backend calls. [VERIFIED: backend code] | Tampering | Keep using bound parameters in `asyncpg` execute/fetch calls. [VERIFIED: `corpulse/backends/postgres_async.py`] |
| Parallel test processes mutating the same live database. [VERIFIED: local live-test audit on 2026-04-10] | Denial of Service / Tampering | Run live commands sequentially or partition databases per process. [VERIFIED: local sequential rerun on 2026-04-10] |

## Sources

### Primary (HIGH confidence)
- Local codebase audit of [`tests/conftest.py`](/Users/arkady/src/corpulse/tests/conftest.py), [`tests/test_async_core_integration.py`](/Users/arkady/src/corpulse/tests/test_async_core_integration.py), [`tests/test_async_postgres_backend.py`](/Users/arkady/src/corpulse/tests/test_async_postgres_backend.py), [`tests/report_fixtures.py`](/Users/arkady/src/corpulse/tests/report_fixtures.py), [`corpulse/async_core.py`](/Users/arkady/src/corpulse/corpulse/async_core.py), and [`corpulse/backends/postgres_async.py`](/Users/arkady/src/corpulse/corpulse/backends/postgres_async.py). [VERIFIED: codebase]
- [`pyproject.toml`](/Users/arkady/src/corpulse/pyproject.toml), [`.planning/REQUIREMENTS.md`](/Users/arkady/src/corpulse/.planning/REQUIREMENTS.md), [`.planning/ROADMAP.md`](/Users/arkady/src/corpulse/.planning/ROADMAP.md), [`.planning/PROJECT.md`](/Users/arkady/src/corpulse/.planning/PROJECT.md), and [`.planning/STATE.md`](/Users/arkady/src/corpulse/.planning/STATE.md). [VERIFIED: codebase]
- PyPI JSON APIs for `pytest`, `pytest-asyncio`, `asyncpg`, and `psycopg`. [VERIFIED: `https://pypi.org/pypi/pytest/json`, `https://pypi.org/pypi/pytest-asyncio/json`, `https://pypi.org/pypi/asyncpg/json`, `https://pypi.org/pypi/psycopg/json`]
- Official asyncpg docs: `https://magicstack.github.io/asyncpg/current/usage.html`. [CITED: https://magicstack.github.io/asyncpg/current/usage.html]
- Official pytest fixtures docs: `https://docs.pytest.org/en/stable/how-to/fixtures.html`. [CITED: https://docs.pytest.org/en/stable/how-to/fixtures.html]

### Secondary (MEDIUM confidence)
- Official pytest-asyncio configuration docs: `https://pytest-asyncio.readthedocs.io/en/stable/reference/configuration.html`. [CITED: https://pytest-asyncio.readthedocs.io/en/stable/reference/configuration.html]
- Local Docker inspection of `corpulse-pg` plus prior Phase 10 validation artifacts describing the same DSN. [VERIFIED: `docker ps`, `docker inspect corpulse-pg`, `.planning/phases/10-async-backend-corpulse-integration/10-VALIDATION.md`]

### Tertiary (LOW confidence)
- None. [VERIFIED: this research contains only VERIFIED or CITED claims except for items listed in the Assumptions Log]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - versions and tooling were verified from the repo, local environment, PyPI, and official docs. [VERIFIED: codebase, local audit, PyPI JSON, official docs]
- Architecture: HIGH - the repo already contains the exact fixture, backend, and report-helper seams this phase should reuse. [VERIFIED: codebase]
- Pitfalls: HIGH - the biggest pitfalls were confirmed directly in the workspace, including the parallel shared-DB contamination case. [VERIFIED: local live-test audit on 2026-04-10]

**Research date:** 2026-04-10 [VERIFIED: local system date]
**Valid until:** 2026-05-10 for repo-local structure; re-check package versions and local DB availability before planning if this slips. [VERIFIED: stable repo structure + time-sensitive package/env data]
