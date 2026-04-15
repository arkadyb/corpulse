---
task: 260410-mf8
type: quick-task-summary
date_completed: 2026-04-10
commits:
  - 3b739d1
  - 0c31724
  - 01d5842
---

# Quick Task 260410-mf8 Summary

Added async analysis parity for `AsyncCorpulse` so the async API now exposes duplicate, obsolete, stale-embedding, suspect, and corpus-health analysis with the same payload shapes and thresholds as sync `Corpulse`.

## Completed Work

1. Extracted reusable private analysis helpers in [core.py](/Users/arkady/src/corpulse/corpulse/core.py) for ghost detection, duplicate pairing, obsolete version grouping, stale embedding detection, suspect scoring, and corpus health aggregation while preserving sync behavior.
2. Implemented `AsyncCorpulse.get_duplicates()`, `get_obsolete()`, `get_stale_embeddings()`, `get_suspects()`, and `corpus_health()` in [async_core.py](/Users/arkady/src/corpulse/corpulse/async_core.py) on top of awaited backend reads plus shared helper logic.
3. Expanded [test_async_core_integration.py](/Users/arkady/src/corpulse/tests/test_async_core_integration.py) with deterministic parity coverage, backend await-pattern assertions, and the scikit-learn guard case for async duplicate detection.

## Verification

`pytest tests/test_async_core_integration.py -q`

Result: passed locally with one existing skipped live async-postgres integration test gated on `CORPULSE_POSTGRES_TEST_CONNINFO` and `asyncpg`.

## Deviations from Plan

None. The quick plan was executed as written.

## Self-Check: PASSED

Verified summary target exists, referenced commits exist in git history, and the async integration suite passes after all task commits.
