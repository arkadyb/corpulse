---
phase: 21-low-confidence-zero-result-rate-analytics
reviewed: 2026-04-19T07:18:40Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - corpulse/async_core.py
  - corpulse/backends/__init__.py
  - corpulse/backends/base.py
  - corpulse/backends/memory.py
  - corpulse/backends/postgres.py
  - corpulse/backends/postgres_async.py
  - corpulse/backends/sqlite.py
  - corpulse/core.py
  - corpulse/integrations/qdrant.py
  - corpulse/models.py
  - tests/conftest.py
  - tests/test_analytics.py
  - tests/test_async_core_integration.py
  - tests/test_async_postgres_backend.py
  - tests/test_backend_contract.py
  - tests/test_core_backend_integration.py
  - tests/test_postgres_backend.py
  - tests/test_qdrant_wrapper.py
findings:
  critical: 0
  warning: 1
  info: 1
  total: 2
status: issues_found
---

# Phase 21: Code Review Report

**Reviewed:** 2026-04-19T07:18:40Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

I reviewed the phase 21 zero-result analytics gap-closure changes across the storage contract, sync/async analytics layers, Qdrant wrapper, and backend parity tests. The touched test subset passed, but there is one logic issue in the new zero-result metric semantics and one contract-shape drift to call out for downstream callers.

## Warnings

### WR-01: Zero-result analytics still filters by query hash, not zero-result attempts

**File:** [`/Users/arkady/src/corpulse/corpulse/core.py:351`](/Users/arkady/src/corpulse/corpulse/core.py#L351)
**Issue:** `_build_zero_result_queries()` only returns rows where `result_cnt == 0`, and `zero_result_rate()` divides by the number of unique query hashes. That means any mixed query hash with both empty and non-empty attempts is excluded entirely, so the metric undercounts real zero-result behavior whenever the same query is retried. The new `query_attempts` table gives you attempt-level data, but the current aggregation does not use it.
**Fix:**
```python
total_attempts = sum(int(row["cnt"]) for row in query_rows)
zero_result_attempts = sum(
    int(row["cnt"]) - int(row["result_cnt"])
    for row in query_rows
)
return round(zero_result_attempts / total_attempts, 2) if total_attempts else 0.0
```
If the detail surface should stay query-hash based, add an explicit `zero_result_cnt` field and return hashes where `zero_result_cnt > 0`; otherwise rename the API to match the unique-query semantics.

## Info

### IN-01: `get_zero_result_queries()` is now a breaking payload-shape change

**File:** [`/Users/arkady/src/corpulse/corpulse/models.py:38`](/Users/arkady/src/corpulse/corpulse/models.py#L38)
**Issue:** `ZeroResultQueryRow` now aliases `QueryAttemptRow` instead of `QueryRow`, so callers that previously consumed `avg_rank`, `avg_score`, and rank bounds will fail after this phase unless they are updated. This is a real contract change, even though it appears intentional for the new analytics model.
**Fix:** Document the new payload shape in the public API docs or provide a compatibility shim that maps attempt aggregates back to the prior retrieval-row shape for existing callers.

---

_Reviewed: 2026-04-19T07:18:40Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
