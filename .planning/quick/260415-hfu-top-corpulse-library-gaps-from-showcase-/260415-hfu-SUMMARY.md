---
task: 260415-hfu
type: quick-task-summary
date_completed: 2026-04-15
commits:
  - ba39e3e
---

# Quick Task 260415-hfu Summary

Shipped the two highest-priority library gaps from the showcase audit: the async Qdrant wrapper now works with `AsyncCorpulse`, and the library now exposes a public `delete_document` API across sync and async flows.

## Completed Work

1. Updated [qdrant.py](/Users/arkady/src/corpulse/corpulse/integrations/qdrant.py) so `AsyncQdrantCorpulseClient` detects coroutine-based `log_retrieval` methods and awaits them directly, while keeping the existing off-thread fallback for sync `Corpulse` instances.
2. Added public `delete_document` methods to [core.py](/Users/arkady/src/corpulse/corpulse/core.py) and [async_core.py](/Users/arkady/src/corpulse/corpulse/async_core.py), backed by a new shared storage-contract method in [base.py](/Users/arkady/src/corpulse/corpulse/backends/base.py).
3. Implemented delete behavior for [sqlite.py](/Users/arkady/src/corpulse/corpulse/backends/sqlite.py), [memory.py](/Users/arkady/src/corpulse/corpulse/backends/memory.py), [postgres.py](/Users/arkady/src/corpulse/corpulse/backends/postgres.py), and [postgres_async.py](/Users/arkady/src/corpulse/corpulse/backends/postgres_async.py), including dependent retrieval and engagement cleanup.
4. Expanded targeted regression coverage in [test_qdrant_wrapper.py](/Users/arkady/src/corpulse/tests/test_qdrant_wrapper.py), [test_backend_contract.py](/Users/arkady/src/corpulse/tests/test_backend_contract.py), [test_core_backend_integration.py](/Users/arkady/src/corpulse/tests/test_core_backend_integration.py), [test_async_core_integration.py](/Users/arkady/src/corpulse/tests/test_async_core_integration.py), [test_postgres_backend.py](/Users/arkady/src/corpulse/tests/test_postgres_backend.py), and [test_async_postgres_backend.py](/Users/arkady/src/corpulse/tests/test_async_postgres_backend.py).

## Verification

`pytest tests/test_backend_contract.py tests/test_core_backend_integration.py tests/test_async_core_integration.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_qdrant_wrapper.py -q`

Result: passed locally with only the existing environment-gated live Postgres tests skipped because `CORPULSE_POSTGRES_TEST_CONNINFO` plus `psycopg`/`asyncpg` were not available.

## Deviations from Plan

None. The quick task stayed within audit items #1 and #3.

## Self-Check: PASSED

Verified the code/test commit exists in git history, the summary references the shipped surfaces accurately, and the targeted regression suite passes after the patch.
