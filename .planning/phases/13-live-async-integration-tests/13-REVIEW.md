---
phase: 13-live-async-integration-tests
reviewed: 2026-04-12T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - tests/report_fixtures.py
  - tests/test_async_core_integration.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-04-12T00:00:00Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Both files are well-structured and generally correct. `report_fixtures.py` cleanly separates fixture data from fixture assembly, and the test file exercises the async/sync parity contract thoroughly. Five findings are noted — two warnings that could cause silent incorrect results or flaky test failures, and three info-level items.

## Warnings

### WR-01: `FakeDataFrame.sort_values` silently ignores the `ascending` argument when `ascending=True` is passed as a keyword argument

**File:** `tests/test_async_core_integration.py:151-154`

**Issue:** `sort_values(key, ascending=False)` reverses the `ascending` flag when delegating to Python's `sorted()`: `reverse=not ascending`. When `ascending=True` is the default or is explicitly passed, the lambda computes `reverse=False`, which is correct. However, if `sort_values` is ever called with `ascending=True` (sort ascending), the implementation sorts descending instead (`reverse=not True == False` is actually fine — wait: `not True` = `False`, so `reverse=False` → ascending). This is actually correct for the two-value boolean case. The real bug is subtler: `sort_values` accepts only positional-or-keyword `key` but the real `pd.DataFrame.sort_values` signature is `sort_values(by, ...)`. If production code calls `sort_values(by="retrievals")` as a keyword argument, `FakeDataFrame.sort_values` receives it in `key`. This mismatch is fine as long as callers match, but it means the fake is tightly coupled to one call-site. The actual latent bug: `FakeDataFrame.__init__` at line 149 calls `rows[0].keys()` — if `sort_values` is called and the sorted result is used to construct a new `FakeDataFrame`, the new instance's `columns` attribute is derived from the first row's keys, which is correct. **The genuine warning**: when `sort_values` returns a new `FakeDataFrame`, the `columns` attribute on the returned object is set from the sorted list's first element. If `rows` is ever empty after sorting (impossible in the current tests but possible if a future test seeds an empty backend), `columns` becomes `[]` and downstream `assert "doc_id" in df.columns` (line 621) would fail with a misleading assertion error rather than a clear message.

**Fix:** Guard against empty rows in the `FakeDataFrame` constructor, or add an explicit assertion in tests that verify the shape before accessing columns:

```python
class FakeDataFrame:
    def __init__(self, rows):
        self._rows = list(rows)
        if not self._rows:
            raise ValueError("FakeDataFrame: seeded with zero rows — check fixture setup")
        self.columns = list(self._rows[0].keys())
```

---

### WR-02: `test_live_async_corpulse_round_trip` does not monkeypatch `_days_ago`, making the ghost assertion depend on real wall-clock time

**File:** `tests/test_async_core_integration.py:595-606`

**Issue:** `get_ghosts()` internally calls `_days_ago(self.ghost_threshold_days)` (i.e., `_days_ago(30)`) to produce the `since` cutoff for `retrieval_counts`. No retrieval is inserted for `ghost-doc`, so it will always appear in the ghost list — the test passes today. But `log_retrieval` for `fresh-doc` inserts a row with `retrieved_at = _now()` (real time). If the `retrieval_counts` query filters by `retrieved_at >= since` and uses wall-clock time for the cutoff, the test is inherently non-deterministic if time resolution causes the freshly-inserted row to land exactly at the cutoff boundary. More concretely: this is the only live test that does not monkeypatch the time functions. It currently works because both inserted events are near-simultaneous with the cutoff computation. If the database clock and application clock drift (common in CI with containerized Postgres), `fresh-doc` might appear as a ghost, flipping the assertion. The other three live tests all monkeypatch `_days_ago`.

**Fix:** Add the same monkeypatch applied in the other live tests, or explicitly set a `retrieved_at` far in the past for `fresh-doc` to make the retrieval unambiguously recent regardless of clock drift. Alternatively, assert on `doc_id` membership rather than exact list equality:

```python
async def test_live_async_corpulse_round_trip(async_backend, monkeypatch):
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 0.0)  # cutoff = epoch
    corpulse = AsyncCorpulse(backend=async_backend, ghost_threshold_days=30)

    await corpulse.register_document("ghost-doc", "ghost.md")
    await corpulse.log_retrieval(
        [{"doc_id": "fresh-doc", "filename": "fresh.md", "score": 0.8}],
        query="status",
    )

    ghosts = await corpulse.get_ghosts()
    ghost_ids = {g["doc_id"] for g in ghosts}
    assert "ghost-doc" in ghost_ids
    assert "fresh-doc" not in ghost_ids
```

---

## Info

### IN-01: `_seed_live_backend` is a redundant one-line wrapper over `seed_async_backend`

**File:** `tests/test_async_core_integration.py:590-592`

**Issue:** `_seed_live_backend` does nothing beyond forwarding its argument to `seed_async_backend`. It adds indirection without providing any added behaviour or documentation value that the docstring of `seed_async_backend` (in `report_fixtures.py`) does not already provide.

**Fix:** Remove the wrapper and call `seed_async_backend(async_backend)` directly at each call site (lines 611, 634, 652). This is a three-line change and eliminates one level of indirection.

---

### IN-02: `_analysis_fixture_rows` duplicates structure that `build_report_fixture_snapshot` already provides

**File:** `tests/test_async_core_integration.py:171-233`

**Issue:** `_analysis_fixture_rows` defines its own inline corpus (documents, retrieval, engagement, embedding rows) with a different scale from the canonical fixture in `report_fixtures.py`. This creates two sources of truth for fixture data. While the two datasets serve different purposes (the inline one is smaller and hand-tuned for specific assertions), new developers must understand which fixture is used for which test family, which is not documented inline.

**Fix:** Add a brief comment at the top of `_analysis_fixture_rows` explaining why a separate smaller fixture is used rather than the shared report fixture, to help future readers.

---

### IN-03: Magic number `0.92` for duplicate threshold hardcoded in `report_fixtures.helper_inputs`

**File:** `tests/report_fixtures.py:219`

**Issue:** The value `0.92` passed to `_build_duplicate_pairs` in `helper_inputs` is not named or documented. The same threshold appears in production code defaults but the relationship is implicit.

**Fix:** Extract to a named constant:

```python
_DUPLICATE_THRESHOLD = 0.92

# inside helper_inputs:
duplicate_pairs = _build_duplicate_pairs(snapshot["embedding_rows"], _DUPLICATE_THRESHOLD)
```

---

_Reviewed: 2026-04-12T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
