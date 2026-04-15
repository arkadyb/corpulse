---
phase: 12-async-parity-methods-unit-tests
reviewed: 2026-04-10T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - corpulse/async_core.py
  - tests/report_fixtures.py
  - tests/test_async_core_integration.py
  - tests/test_report_helpers.py
findings:
  critical: 0
  warning: 2
  info: 0
  total: 2
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-04-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the new async parity implementation in `AsyncCorpulse` plus the shared frozen fixtures and parity tests. The main implementation matches the sync helpers and the targeted test suite passes, but the new async facade still has two falsy-value bugs: explicit timestamps of `0.0` are discarded, and explicit `window_days=0` requests silently fall back to the default 30-day window.

## Warnings

### WR-01: `log_source_update()` drops explicit zero timestamps

**File:** `corpulse/async_core.py:77`
**Issue:** `updated_at or _now()` treats `0.0` as false and replaces it with the current time. That makes it impossible to persist a legitimate epoch timestamp and silently corrupts caller input.
**Fix:**
```python
await self.db.update_source_timestamp(
    doc_id,
    updated_at if updated_at is not None else _now(),
)
```

### WR-02: Explicit `window_days=0` falls back to the default lookback

**File:** `corpulse/async_core.py:115`
**Issue:** `get_suspects()`, `to_dataframe()`, and `report()` all use `window_days or self.ghost_threshold_days`. Passing `0` therefore behaves the same as omitting the argument, so a caller asking for a zero-day window gets a 30-day window instead. This is observable in `report(window_days=0)`, which currently reports `window_days: 30`.
**Fix:**
```python
effective_window_days = (
    window_days if window_days is not None else self.ghost_threshold_days
)
since = _days_ago(effective_window_days)
```
Apply the same `is not None` check in every async method that accepts `window_days`.

---

_Reviewed: 2026-04-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
