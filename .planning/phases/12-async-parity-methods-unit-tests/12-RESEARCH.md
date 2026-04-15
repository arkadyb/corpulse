# Phase 12: Async Parity Methods + Unit Tests - Research

**Researched:** 2026-04-10 [VERIFIED: system date]
**Domain:** Python async facade parity over existing sync report helpers and pytest-based async unit coverage [VERIFIED: codebase `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `corpulse/async_core.py`, `corpulse/core.py`]
**Confidence:** HIGH [VERIFIED: codebase inspection plus official docs/PyPI metadata]

## User Constraints

No phase-local `CONTEXT.md` exists in `.planning/phases/12-async-parity-methods-unit-tests`, so there are no additional locked decisions beyond the repository planning files and the user prompt. [VERIFIED: `node /Users/arkady/.codex/get-shit-done/bin/gsd-tools.cjs init phase-op 12`]

## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| ASYNC-PAR-01 | `AsyncCorpulse.to_dataframe(window_days)` matches sync columns, ordering, statuses, and pandas error behavior. [VERIFIED: `.planning/REQUIREMENTS.md`] | Implement the async method as the sync `to_dataframe()` data flow with awaited backend reads, `_build_dataframe_rows(...)`, and the same lazy `import pandas as pd` guard string. [VERIFIED: `corpulse/core.py`, `corpulse/async_core.py`] |
| ASYNC-PAR-02 | `AsyncCorpulse.report(window_days)` returns structured report data at parity with sync output. [VERIFIED: `.planning/REQUIREMENTS.md`] | Return `{"summary": _build_report_summary(...), "rows": _build_report_rows(...)}` so tests can compare directly against the same helper outputs that drive sync formatting. [VERIFIED: `corpulse/core.py`, `.planning/phases/11-shared-report-helpers/11-RESEARCH.md`] |
| ASYNC-PAR-03 | `AsyncCorpulse.cleanup_report()` returns structured cleanup payload at parity with sync output. [VERIFIED: `.planning/REQUIREMENTS.md`] | Return `_build_cleanup_payload(...)` directly after awaited analysis/helper inputs are assembled. [VERIFIED: `corpulse/core.py`, `.planning/phases/11-shared-report-helpers/11-RESEARCH.md`] |
| ASYNC-TEST-01 | Deterministic async tests prove `to_dataframe()` parity against sync for the same fixture. [VERIFIED: `.planning/REQUIREMENTS.md`] | Reuse one frozen document/retrieval/engagement fixture across sync and fake-async backends, then assert exact columns, row ordering, and row dict equality after DataFrame normalization. [VERIFIED: `tests/test_report_helpers.py`, `tests/test_async_core_integration.py`] |
| ASYNC-TEST-02 | Deterministic async tests prove `report()` and `cleanup_report()` payload parity against sync structured data. [VERIFIED: `.planning/REQUIREMENTS.md`] | Compare async return values to helper-derived sync payloads rather than to rendered stdout, because sync formatting is already locked by Phase 11 tests. [VERIFIED: `tests/test_report_helpers.py`, `.planning/phases/11-shared-report-helpers/11-03-sync-formatter-refactor-PLAN.md`] |

## Summary

Phase 12 is a narrow parity phase, not a redesign. [VERIFIED: `.planning/ROADMAP.md`, `.planning/PROJECT.md`] The sync side already exposes the required computation seams through `_build_dataframe_rows`, `_build_report_rows`, `_build_report_summary`, and `_build_cleanup_payload`, while `AsyncCorpulse` currently stops at analysis methods and has no reporting surface yet. [VERIFIED: `corpulse/core.py`, `corpulse/async_core.py`]

The clean implementation path is to make each async method mirror the sync method's read pattern, but replace backend calls with awaited equivalents and return structured data instead of printing. [VERIFIED: `corpulse/core.py`, `corpulse/async_core.py`] For `report()`, the least ambiguous contract is a dict with `summary` and `rows`, because those are already the two helper outputs that define the sync report. [VERIFIED: `corpulse/core.py`, `.planning/phases/11-shared-report-helpers/11-RESEARCH.md`]

The main planning risk is test-fixture drift, not library complexity. [VERIFIED: `tests/test_report_helpers.py`, `tests/test_async_core_integration.py`] The repo already has a frozen report fixture on the sync side and fake async backends on the async side, so planning should allocate one task to unify those into a single reusable fixture source before adding the new parity assertions. [VERIFIED: `tests/test_report_helpers.py`, `tests/test_async_core_integration.py`, [CITED: https://docs.pytest.org/en/stable/how-to/fixtures.html]]

**Primary recommendation:** Add `AsyncCorpulse.to_dataframe()`, `report()`, and `cleanup_report()` as thin async wrappers over the Phase 11 helpers, and back them with one shared frozen fixture used by both sync and async tests. [VERIFIED: `corpulse/core.py`, `corpulse/async_core.py`, `tests/test_report_helpers.py`, `tests/test_async_core_integration.py`]

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---|---|---|---|
| Python | Repo floor `>=3.10`; local env `3.14.3`. [VERIFIED: `pyproject.toml`, `python3 --version`] | Runtime for library and tests. [VERIFIED: `pyproject.toml`] | The package and test suite are already configured around Python 3.10+ syntax and typing. [VERIFIED: `pyproject.toml`, codebase] |
| `pytest` | Repo floor `>=8.0`; current PyPI `9.0.3` published `2026-04-07`. [VERIFIED: `pyproject.toml`, PyPI JSON `https://pypi.org/pypi/pytest/json`] | Test runner. [VERIFIED: `pyproject.toml`] | The suite already uses pytest fixtures, parametrization, skips, and assertion rewriting extensively. [VERIFIED: `tests/`, [CITED: https://docs.pytest.org/en/stable/how-to/fixtures.html]] |
| `pytest-asyncio` | Repo floor `>=0.23`; current PyPI `1.3.0` published `2025-11-10`. [VERIFIED: `pyproject.toml`, PyPI JSON `https://pypi.org/pypi/pytest-asyncio/json`] | Async test execution. [VERIFIED: `pyproject.toml`] | The project already sets `asyncio_mode = "auto"` and has async tests passing under pytest. [VERIFIED: `pyproject.toml`, `tests/test_async_core_integration.py`, [CITED: https://pytest-asyncio.readthedocs.io/en/stable/reference/configuration.html]] |
| Shared helpers in `corpulse.core` | Current repo head `f77a9f1`. [VERIFIED: `git rev-parse --short HEAD`] | Single source of truth for row/status/payload assembly. [VERIFIED: `corpulse/core.py`] | Phase 11 intentionally extracted these helpers so Phase 12 would not duplicate sync report logic. [VERIFIED: `.planning/phases/11-shared-report-helpers/11-RESEARCH.md`, `.planning/STATE.md`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---|---|---|---|
| `pandas` | Optional in repo; current PyPI `3.0.2` published `2026-03-31`. [VERIFIED: `corpulse/core.py`, PyPI JSON `https://pypi.org/pypi/pandas/json`] | Materialize the DataFrame return for `to_dataframe()`. [VERIFIED: `corpulse/core.py`] | Import lazily inside `to_dataframe()` only, and preserve the exact sync error message when unavailable. [VERIFIED: `corpulse/core.py`] |
| `tabulate` | Optional runtime helper in sync path; current PyPI `0.10.0` published `2026-03-04`. [VERIFIED: `corpulse/core.py`, PyPI JSON `https://pypi.org/pypi/tabulate/json`] | Pretty-print sync tables only. [VERIFIED: `corpulse/core.py`, `README.md`] | Do not use it in async parity methods, because async `report()` must return payload data instead of stdout. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/PROJECT.md`] |
| `numpy` | Repo floor `>=1.24`; current PyPI `2.4.4` published `2026-03-29`. [VERIFIED: `pyproject.toml`, PyPI JSON `https://pypi.org/pypi/numpy/json`] | Existing embedding helpers and test fixtures. [VERIFIED: `corpulse/core.py`, `tests/test_report_helpers.py`] | Reuse existing seeded embedding helpers for deterministic fixtures. [VERIFIED: `tests/test_report_helpers.py`, `tests/test_async_core_integration.py`] |
| `scikit-learn` | Repo floor `>=1.3`; current PyPI `1.8.0` published `2025-12-10`. [VERIFIED: `pyproject.toml`, PyPI JSON `https://pypi.org/pypi/scikit-learn/json`] | Duplicate detection inside `corpus_health()`. [VERIFIED: `corpulse/core.py`] | Keep existing guard behavior untouched; this phase is not changing duplicate semantics. [VERIFIED: `corpulse/core.py`, `tests/test_async_core_integration.py`] |
| `asyncpg` | Optional extra in repo; current PyPI `0.31.0` published `2025-11-24`. [VERIFIED: `pyproject.toml`, PyPI JSON `https://pypi.org/pypi/asyncpg/json`] | Async Postgres backend. [VERIFIED: `pyproject.toml`, `corpulse/backends/postgres_async.py`] | Only Phase 13 needs live coverage; Phase 12 unit tests should stay backend-fake and deterministic. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `tests/test_async_core_integration.py`] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| Reusing `_build_*` helpers. [VERIFIED: `corpulse/core.py`] | Reimplement async-specific row/payload builders in `async_core.py`. [ASSUMED] | Reject this for planning because it duplicates the parity logic that Phase 11 was created to centralize. [VERIFIED: `.planning/phases/11-shared-report-helpers/11-RESEARCH.md`] |
| Shared frozen fixture module. [VERIFIED: `tests/test_report_helpers.py`, `tests/test_async_core_integration.py`] | Duplicate the sync fixture in async tests. [ASSUMED] | Reject this for planning because parity tests become weaker when the two paths can silently diverge at fixture setup time. [VERIFIED: current separate helper locations in `tests/test_report_helpers.py` and `tests/test_async_core_integration.py`] |

**Installation:**

```bash
pip install -e ".[dev]"
```

[VERIFIED: `pyproject.toml`]

**Version verification:** Current package releases above were verified against the PyPI JSON APIs on 2026-04-10. [VERIFIED: PyPI JSON `https://pypi.org/pypi/pytest/json`, `https://pypi.org/pypi/pytest-asyncio/json`, `https://pypi.org/pypi/pandas/json`, `https://pypi.org/pypi/tabulate/json`, `https://pypi.org/pypi/numpy/json`, `https://pypi.org/pypi/scikit-learn/json`, `https://pypi.org/pypi/asyncpg/json`]

## Architecture Patterns

### Recommended Project Structure

```text
corpulse/
├── core.py              # Shared sync logic and pure payload builders
├── async_core.py        # Async facade that awaits backend reads and reuses core helpers
└── backends/            # Sync and async backend implementations
tests/
├── conftest.py          # Shared pytest fixtures and backend parametrization
├── test_report_helpers.py
└── test_async_core_integration.py
```

[VERIFIED: codebase tree]

### Pattern 1: Thin Async Wrappers Over Shared Pure Builders

**What:** Fetch async backend rows with `await`, then hand the resulting lists/maps into the existing pure helper functions from `corpulse.core`. [VERIFIED: `corpulse/core.py`, `corpulse/async_core.py`]

**When to use:** Use this for all three new async parity methods in Phase 12. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`]

**Example:**

```python
# Source: corpulse/core.py + corpulse/async_core.py
async def report(self, window_days: int | None = None) -> dict[str, object]:
    since = _days_ago(window_days or self.ghost_threshold_days)
    all_docs = await self.db.all_documents()
    r_map = {r["doc_id"]: r for r in await self.db.retrieval_counts(since=since)}
    e_map = {e["doc_id"]: e["cnt"] for e in await self.db.engagement_counts(since=since)}
    ghosts = await self.get_ghosts()
    obsolete = await self.get_obsolete()
    stale = await self.get_stale_embeddings()
    health = await self.corpus_health()

    return {
        "summary": _build_report_summary(
            all_docs,
            window_days or self.ghost_threshold_days,
            health,
        ),
        "rows": _build_report_rows(
            all_docs,
            r_map,
            e_map,
            {row["doc_id"] for row in ghosts},
            {row["doc_id"] for row in obsolete},
            {row["doc_id"] for row in stale},
            self.top_k_report,
        ),
    }
```

[VERIFIED: `corpulse/core.py`, `corpulse/async_core.py`]

### Pattern 2: Preserve Sync Optional-Dependency Semantics Exactly

**What:** Keep the lazy pandas import inside the async `to_dataframe()` method and raise the exact same `RuntimeError("pip install pandas to use to_dataframe()")` string when pandas is unavailable. [VERIFIED: `corpulse/core.py`, `.planning/REQUIREMENTS.md`]

**When to use:** Only in `AsyncCorpulse.to_dataframe()`. [VERIFIED: `.planning/REQUIREMENTS.md`]

**Example:**

```python
# Source: corpulse/core.py
try:
    import pandas as pd
except ImportError:
    raise RuntimeError("pip install pandas to use to_dataframe()")
```

[VERIFIED: `corpulse/core.py`]

### Pattern 3: Fixture Reuse Through Pytest Fixtures or Shared Test Helpers

**What:** Move the frozen report fixture data builder into one shared location and feed both a sync backend and a fake async backend from the same source data. [VERIFIED: `tests/test_report_helpers.py`, `tests/test_async_core_integration.py`, [CITED: https://docs.pytest.org/en/stable/how-to/fixtures.html]]

**When to use:** Use this before adding the new parity assertions so Phase 12 tests prove same-fixture parity rather than same-shape coincidence. [VERIFIED: `.planning/REQUIREMENTS.md`]

**Example:**

```python
# Source pattern: pytest fixtures documentation + existing test style
@pytest.fixture
def report_fixture_rows():
    return make_report_fixture_rows()

@pytest.fixture
def sync_report_backend(report_fixture_rows):
    return build_sync_backend(report_fixture_rows)

@pytest.fixture
def async_report_backend(report_fixture_rows):
    return FakeAsyncBackend.from_rows(report_fixture_rows)
```

[VERIFIED: existing fixture patterns in `tests/conftest.py`; [CITED: https://docs.pytest.org/en/stable/how-to/fixtures.html]]

### Anti-Patterns to Avoid

- **Recomputing report payload shapes in `async_core.py`:** This breaks the Phase 11 single-source-of-truth design and increases parity drift risk. [VERIFIED: `corpulse/core.py`, `.planning/phases/11-shared-report-helpers/11-RESEARCH.md`]
- **Making async `report()` print to stdout:** v1.2 explicitly chose structured-return async reports for service integration. [VERIFIED: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`]
- **Comparing async report payloads to captured sync stdout:** Phase 11 already locked sync formatting, so Phase 12 should compare to helper-derived structured data instead. [VERIFIED: `tests/test_report_helpers.py`, `.planning/phases/11-shared-report-helpers/11-03-sync-formatter-refactor-PLAN.md`]
- **Using live Postgres for Phase 12 unit parity tests:** live asyncpg coverage is a separate Phase 13 requirement. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Async report row classification. [VERIFIED: requirements + codebase] | A second copy of status ordering and engagement-threshold logic in `async_core.py`. [VERIFIED: `corpulse/core.py`] | `_build_dataframe_rows(...)` and `_build_report_rows(...)`. [VERIFIED: `corpulse/core.py`] | These already encode the intentionally different rounded vs unrounded low-engagement behavior. [VERIFIED: `corpulse/core.py`, `tests/test_report_helpers.py`] |
| Async cleanup section assembly. [VERIFIED: requirements + codebase] | Manual top-5, overflow, and count math in async methods. [VERIFIED: `corpulse/core.py`] | `_build_cleanup_payload(...)`. [VERIFIED: `corpulse/core.py`] | The helper already defines the exact sync payload shape and section semantics. [VERIFIED: `corpulse/core.py`, `tests/test_report_helpers.py`] |
| Async report contract. [VERIFIED: Phase 12 scope] | A novel nested schema unrelated to sync helper outputs. [ASSUMED] | `{"summary": ..., "rows": ...}` where values come directly from `_build_report_summary(...)` and `_build_report_rows(...)`. [VERIFIED: `corpulse/core.py`] | This makes parity assertions direct and keeps future docs/examples simple. [VERIFIED: helper shapes in `corpulse/core.py`] |
| Optional-dependency test scaffolding. [VERIFIED: current tests] | Real pandas/tabulate installs just to cover missing-module branches. [VERIFIED: local env lacks both packages] | The existing monkeypatch pattern that intercepts imports. [VERIFIED: `tests/test_report_helpers.py`] | The repo already proves this pattern works and it keeps Phase 12 unit tests deterministic on machines without those extras. [VERIFIED: `tests/test_report_helpers.py`, local env import probe] |

**Key insight:** Phase 12 should add awaited data access, not new business logic. [VERIFIED: `corpulse/core.py`, `corpulse/async_core.py`, `.planning/ROADMAP.md`]

## Common Pitfalls

### Pitfall 1: Accidentally Normalizing the Rounded-vs-Unrounded Divergence

**What goes wrong:** `to_dataframe()` and `report()` stop disagreeing at the low-engagement boundary. [VERIFIED: `corpulse/core.py`, `tests/test_report_helpers.py`]
**Why it happens:** `_build_dataframe_rows(...)` classifies on the rounded float rate, while `_build_report_rows(...)` classifies on the raw ratio. [VERIFIED: `corpulse/core.py`, `tests/test_report_helpers.py`] 
**How to avoid:** Call the correct helper for each surface and do not refactor their status logic in Phase 12. [VERIFIED: `corpulse/core.py`] 
**Warning signs:** A parity test passes on top rows but fails on a synthetic `3 / 20` boundary case or on explicit helper tests. [VERIFIED: `tests/test_report_helpers.py`] 

### Pitfall 2: Returning a Payload Shape That Is Hard to Compare

**What goes wrong:** Tests become formatter-aware or have to reconstruct sync helper outputs to compare results. [VERIFIED: Phase 11 helper split + Phase 12 requirements]
**Why it happens:** Async `report()` returns a custom flat dict instead of the helper-native `summary` plus `rows` structure. [ASSUMED]
**How to avoid:** Return a two-key dict for report payloads and the raw cleanup payload dict for cleanup parity. [VERIFIED: helper contracts in `corpulse/core.py`] 
**Warning signs:** Test code needs to parse strings like `"10%"`, rebuild totals, or compare against stdout snapshots. [VERIFIED: sync formatter uses rendered strings in stdout only, `corpulse/core.py`, `tests/test_report_helpers.py`] 

### Pitfall 3: Fixture Drift Between Sync and Async Tests

**What goes wrong:** The parity test asserts "same backend fixture" in intent but actually seeds sync and async paths differently. [VERIFIED: current fixture code is split across files]
**Why it happens:** The sync frozen report fixture lives in `tests/test_report_helpers.py`, while async tests currently use a separate fixture factory. [VERIFIED: `tests/test_report_helpers.py`, `tests/test_async_core_integration.py`] 
**How to avoid:** Extract one shared fixture source or builder and feed both backends from it. [VERIFIED: existing pytest fixture system in `tests/conftest.py`; [CITED: https://docs.pytest.org/en/stable/how-to/fixtures.html]]
**Warning signs:** Async and sync test modules both define near-identical seed data or `FROZEN` constants. [VERIFIED: `tests/test_report_helpers.py`, `tests/test_async_core_integration.py`] 

### Pitfall 4: Forgetting That `pytest-asyncio` Defaults Matter

**What goes wrong:** Async tests behave differently across environments if loop handling is assumed rather than using the repo config. [VERIFIED: repo config + docs]
**Why it happens:** `pytest-asyncio` defaults to `strict` when `asyncio_mode` is not set, but this repo explicitly sets `asyncio_mode = "auto"`. [VERIFIED: `pyproject.toml`, [CITED: https://pytest-asyncio.readthedocs.io/en/stable/reference/configuration.html]]
**How to avoid:** Keep new tests consistent with the existing async test style and repo config; do not add redundant per-test loop hacks unless a failure demonstrates a need. [VERIFIED: `pyproject.toml`, `tests/test_async_core_integration.py`] 
**Warning signs:** New tests introduce explicit event-loop fixtures or markers inconsistent with the existing module style. [VERIFIED: `tests/test_async_core_integration.py`] 

## Code Examples

Verified patterns from current code and official docs:

### Async Report Parity Assertion

```python
# Source: corpulse/core.py + tests/test_async_core_integration.py
sync = Corpulse(backend=sync_backend, ghost_threshold_days=30)
async_corp = AsyncCorpulse(backend=async_backend, ghost_threshold_days=30)

expected = {
    "summary": _build_report_summary(all_docs, 30, sync.corpus_health()),
    "rows": _build_report_rows(
        all_docs,
        r_map,
        e_map,
        ghost_ids,
        obsolete_ids,
        stale_ids,
        sync.top_k_report,
    ),
}

assert await async_corp.report(window_days=30) == expected
```

[VERIFIED: helper contracts in `corpulse/core.py`; existing async assertion style in `tests/test_async_core_integration.py`]

### DataFrame Normalization for Equality Checks

```python
# Source: pandas docs + sync to_dataframe behavior
sync_rows = sync_corpulse.to_dataframe(window_days=30).to_dict("records")
async_rows = (await async_corpulse.to_dataframe(window_days=30)).to_dict("records")

assert async_rows == sync_rows
```

[VERIFIED: `corpulse/core.py`, [CITED: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.sort_values.html]]

### Parametrized Async Tests Stay Sequential

```python
# Source: pytest-asyncio docs
@pytest.mark.asyncio
@pytest.mark.parametrize("window_days", [7, 30])
async def test_async_report_parity(window_days, report_fixture_rows):
    ...
```

[CITED: https://pytest-asyncio.readthedocs.io/en/stable/how-to-guides/parametrize_with_asyncio.html]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Sync methods owned their own report payload assembly. [VERIFIED: Phase 11 research] | Shared pure helpers in `corpulse/core.py` own row and cleanup payload assembly. [VERIFIED: `corpulse/core.py`] | Phase 11 on 2026-04-10. [VERIFIED: `.planning/STATE.md`, `.planning/ROADMAP.md`] | Async parity can now reuse the exact same computation path instead of porting formatting logic. [VERIFIED: `corpulse/core.py`, `.planning/phases/11-shared-report-helpers/11-RESEARCH.md`] |
| `AsyncCorpulse` covered ingestion and analysis only. [VERIFIED: `corpulse/async_core.py`] | v1.2 roadmap expects full async report parity. [VERIFIED: `.planning/ROADMAP.md`, `.planning/PROJECT.md`] | Milestone v1.2 started on 2026-04-10. [VERIFIED: `.planning/PROJECT.md`, `.planning/STATE.md`] | Phase 12 is the first place where async must expose user-facing report surfaces. [VERIFIED: `.planning/ROADMAP.md`] |

**Deprecated/outdated:**

- Planning any new async report implementation that reuses sync stdout formatting is outdated for v1.2, because the milestone explicitly chose structured-return async reports. [VERIFIED: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | Returning `{"summary": ..., "rows": ...}` is the best async `report()` contract. [ASSUMED] | `## Architecture Patterns`, `## Don't Hand-Roll` | Low-medium; implementation still works with another dict shape, but tests/docs/plans become less direct. |
| A2 | A shared fixture module is preferable to importing builders across test files. [ASSUMED] | `## Summary`, `## Architecture Patterns` | Low; parity can still be tested with duplicated setup, but maintenance cost rises. |

## Open Questions (RESOLVED)

1. **Shared deterministic fixture location:** resolve to a tiny helper module at `tests/report_fixtures.py`, not `tests/conftest.py`. [VERIFIED: existing plan artifacts `12-01-PLAN.md`, `12-02-PLAN.md`]
   Why: the report corpus is phase-specific test data rather than a repo-global autouse fixture, so a helper module keeps reuse explicit and avoids broad `conftest.py` coupling for unrelated tests. [INFERRED from current `tests/conftest.py` scope plus Phase 12 plan file ownership]

2. **Fake async backend approach:** keep the existing `FakeAsyncBackend` type in `tests/test_async_core_integration.py` and seed it from shared rows/helpers exposed by `tests/report_fixtures.py`; do not add a second fake backend class. [VERIFIED: current `FakeAsyncBackend` surface in `tests/test_async_core_integration.py`, existing plan artifacts `12-01-PLAN.md`, `12-02-PLAN.md`]
   Why: this preserves the established async test seam from Phase 10 while making same-fixture parity explicit through shared seed data instead of duplicating backend behavior. [INFERRED from Phase 10 history + current test file layout]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python | Library and tests. [VERIFIED: `pyproject.toml`] | ✓ [VERIFIED: local command] | `3.14.3` [VERIFIED: `python3 --version`] | — |
| `pytest` | Unit and async parity tests. [VERIFIED: `pyproject.toml`] | ✓ [VERIFIED: local command] | `9.0.2` locally. [VERIFIED: `pytest --version`] | — |
| `pytest-asyncio` | Async test execution. [VERIFIED: `pyproject.toml`] | ✓ [VERIFIED: import probe] | Installed locally. [VERIFIED: `python3` import probe] | — |
| `pandas` | Real `to_dataframe()` execution outside monkeypatched tests. [VERIFIED: `corpulse/core.py`] | ✗ [VERIFIED: import probe] | — | Existing tests can keep using fake `pandas` imports for guard/shape coverage. [VERIFIED: `tests/test_report_helpers.py`] |
| `tabulate` | Sync pretty-print path only. [VERIFIED: `corpulse/core.py`] | ✗ [VERIFIED: import probe] | — | Existing fallback and fake-import tests already cover both branches. [VERIFIED: `tests/test_report_helpers.py`] |
| `asyncpg` | Phase 13 live async integration only. [VERIFIED: `.planning/REQUIREMENTS.md`] | ✓ [VERIFIED: import probe] | Installed locally. [VERIFIED: `python3` import probe] | Phase 12 does not require it. [VERIFIED: `.planning/ROADMAP.md`] |

**Missing dependencies with no fallback:**

- None for Phase 12 planning and implementation. [VERIFIED: local environment probe + current test strategy]

**Missing dependencies with fallback:**

- `pandas` is absent locally, but Phase 12 can still implement and test parity using the existing monkeypatch pattern; only manual real-DataFrame smoke runs would remain deferred until pandas is installed. [VERIFIED: `tests/test_report_helpers.py`, local import probe]
- `tabulate` is absent locally, but this phase does not need it because async methods return payloads and sync fallback coverage already exists. [VERIFIED: `corpulse/core.py`, `tests/test_report_helpers.py`, local import probe]

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | `pytest` with `pytest-asyncio`. [VERIFIED: `pyproject.toml`, `pytest --version`, local import probe] |
| Config file | `pyproject.toml` with `testpaths = ["tests"]`, `addopts = ["-ra", "-q", "--import-mode=importlib"]`, and `asyncio_mode = "auto"`. [VERIFIED: `pyproject.toml`] |
| Quick run command | `pytest tests/test_async_core_integration.py -q` [VERIFIED: `.planning/ROADMAP.md`] |
| Full suite command | `pytest tests/test_async_core_integration.py tests/test_report_helpers.py -q` [VERIFIED: current Phase 12 plan verification sections in `12-01-PLAN.md`, `12-02-PLAN.md`] |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| ASYNC-PAR-01 | Async DataFrame parity and pandas guard. [VERIFIED: `.planning/REQUIREMENTS.md`] | async unit | `pytest tests/test_async_core_integration.py -q` [VERIFIED: roadmap success criteria] | ✅ `tests/test_async_core_integration.py` [VERIFIED: codebase] |
| ASYNC-PAR-02 | Async report payload parity. [VERIFIED: `.planning/REQUIREMENTS.md`] | async unit | `pytest tests/test_async_core_integration.py -q` [VERIFIED: roadmap success criteria] | ✅ `tests/test_async_core_integration.py` [VERIFIED: codebase] |
| ASYNC-PAR-03 | Async cleanup payload parity. [VERIFIED: `.planning/REQUIREMENTS.md`] | async unit | `pytest tests/test_async_core_integration.py -q` [VERIFIED: roadmap success criteria] | ✅ `tests/test_async_core_integration.py` [VERIFIED: codebase] |
| ASYNC-TEST-01 | Same-fixture async/sync DataFrame parity assertions. [VERIFIED: `.planning/REQUIREMENTS.md`] | async unit | `pytest tests/test_async_core_integration.py -q` [VERIFIED: roadmap success criteria] | ✅ `tests/test_async_core_integration.py` [VERIFIED: codebase] |
| ASYNC-TEST-02 | Same-fixture async/sync structured payload parity assertions. [VERIFIED: `.planning/REQUIREMENTS.md`] | async unit | `pytest tests/test_async_core_integration.py -q` [VERIFIED: roadmap success criteria] | ✅ `tests/test_async_core_integration.py` [VERIFIED: codebase] |

### Sampling Rate

- **Per task commit:** `pytest tests/test_async_core_integration.py -q` [VERIFIED: `.planning/ROADMAP.md`]
- **Per wave merge:** `pytest tests/test_async_core_integration.py tests/test_report_helpers.py -q` [VERIFIED: focused suite passes locally]
- **Phase gate:** `pytest tests/test_async_core_integration.py tests/test_report_helpers.py -q` [VERIFIED: current Phase 12 plan verification sections in `12-01-PLAN.md`, `12-02-PLAN.md`]

### Wave 0 Gaps

- [ ] Shared report fixture source for both sync and async tests is missing; current rich fixture only exists in `tests/test_report_helpers.py`. [VERIFIED: `tests/test_report_helpers.py`, `tests/test_async_core_integration.py`]
- [ ] `tests/test_async_core_integration.py` has no coverage yet for `AsyncCorpulse.to_dataframe()`, `report()`, or `cleanup_report()`. [VERIFIED: `tests/test_async_core_integration.py`]
- [ ] No current test asserts the async pandas guard string. [VERIFIED: `tests/test_async_core_integration.py`, `tests/test_report_helpers.py`]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no [VERIFIED: phase scope] | Not applicable; the phase adds library methods only. [VERIFIED: `.planning/ROADMAP.md`] |
| V3 Session Management | no [VERIFIED: phase scope] | Not applicable; no sessions or tokens are involved. [VERIFIED: `.planning/ROADMAP.md`] |
| V4 Access Control | no [VERIFIED: phase scope] | Not applicable; no authorization boundary is introduced. [VERIFIED: `.planning/ROADMAP.md`] |
| V5 Input Validation | yes [ASSUMED] | Reuse the existing sync method constraints for `window_days` and backend row shapes rather than adding divergent async parsing logic. [VERIFIED: `corpulse/core.py`, `corpulse/async_core.py`] |
| V6 Cryptography | no [VERIFIED: phase scope] | Not applicable; no cryptographic functionality is added. [VERIFIED: `.planning/ROADMAP.md`] |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Async method accidentally prints sync report output into service logs. [VERIFIED: project decision] | Information Disclosure | Keep async `report()` and `cleanup_report()` structured-return only and avoid `tabulate`/`print` usage in `async_core.py`. [VERIFIED: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`] |
| Async parity logic diverges from sync and silently changes status classification. [VERIFIED: helper split and tests] | Tampering | Reuse `_build_*` helpers and add direct parity assertions against sync helper outputs. [VERIFIED: `corpulse/core.py`, `tests/test_report_helpers.py`] |
| Optional dependency handling differs between sync and async methods. [VERIFIED: requirement] | Denial of Service | Preserve the exact pandas guard string and test it explicitly in async coverage. [VERIFIED: `corpulse/core.py`, `.planning/REQUIREMENTS.md`] |

## Sources

### Primary (HIGH confidence)

- `corpulse/core.py` - Verified helper contracts, sync report/dataframe behavior, and pandas/tabulate guards. [VERIFIED: codebase]
- `corpulse/async_core.py` - Verified current async surface ends at analysis methods. [VERIFIED: codebase]
- `tests/test_report_helpers.py` - Verified frozen report fixture, helper contract tests, and optional-dependency monkeypatch patterns. [VERIFIED: codebase]
- `tests/test_async_core_integration.py` - Verified existing fake async backend patterns and current async coverage gaps. [VERIFIED: codebase]
- `pyproject.toml` - Verified dependency floors, pytest config, and optional extras. [VERIFIED: codebase]
- `.planning/REQUIREMENTS.md` - Verified Phase 12 requirement texts. [VERIFIED: codebase]
- `.planning/ROADMAP.md` - Verified Phase 12 goal, success criteria, and downstream phase split. [VERIFIED: codebase]
- `.planning/PROJECT.md` - Verified milestone decisions, especially structured-return async reports and optional pandas. [VERIFIED: codebase]
- `https://docs.pytest.org/en/stable/how-to/fixtures.html` - Verified fixture reuse guidance. [CITED: https://docs.pytest.org/en/stable/how-to/fixtures.html]
- `https://pytest-asyncio.readthedocs.io/en/stable/reference/configuration.html` - Verified `asyncio_mode` configuration behavior and defaults. [CITED: https://pytest-asyncio.readthedocs.io/en/stable/reference/configuration.html]
- `https://pytest-asyncio.readthedocs.io/en/stable/how-to-guides/parametrize_with_asyncio.html` - Verified async parametrization behavior. [CITED: https://pytest-asyncio.readthedocs.io/en/stable/how-to-guides/parametrize_with_asyncio.html]
- `https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.sort_values.html` - Verified the canonical DataFrame sorting API used by sync `to_dataframe()`. [CITED: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.sort_values.html]

### Secondary (MEDIUM confidence)

- `https://pypi.org/pypi/pytest/json` - Verified current pytest release version and publish date. [VERIFIED: PyPI JSON]
- `https://pypi.org/pypi/pytest-asyncio/json` - Verified current pytest-asyncio release version and publish date. [VERIFIED: PyPI JSON]
- `https://pypi.org/pypi/pandas/json` - Verified current pandas release version and publish date. [VERIFIED: PyPI JSON]
- `https://pypi.org/pypi/tabulate/json` - Verified current tabulate release version and publish date. [VERIFIED: PyPI JSON]
- `https://pypi.org/pypi/numpy/json` - Verified current numpy release version and publish date. [VERIFIED: PyPI JSON]
- `https://pypi.org/pypi/scikit-learn/json` - Verified current scikit-learn release version and publish date. [VERIFIED: PyPI JSON]
- `https://pypi.org/pypi/asyncpg/json` - Verified current asyncpg release version and publish date. [VERIFIED: PyPI JSON]

### Tertiary (LOW confidence)

- None. [VERIFIED: this research avoided unverified web-only claims]

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - package floors came from `pyproject.toml`, current releases came from PyPI JSON, and local availability was probed directly. [VERIFIED: codebase + local commands + PyPI JSON]
- Architecture: HIGH - the implementation seam is explicit in current `core.py` and `async_core.py`, and Phase 11 documented the helper intent. [VERIFIED: `corpulse/core.py`, `corpulse/async_core.py`, `.planning/phases/11-shared-report-helpers/11-RESEARCH.md`]
- Pitfalls: HIGH - the main parity risks are already codified by helper tests and current fixture layout. [VERIFIED: `tests/test_report_helpers.py`, `tests/test_async_core_integration.py`]

**Research date:** 2026-04-10 [VERIFIED: system date]
**Valid until:** 2026-05-10 for codebase facts; re-check PyPI release metadata before implementation if package versions matter to planning again. [VERIFIED: stable codebase domain + fast-moving package registries]
