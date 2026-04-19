# Phase 21: Low-Confidence / Zero-Result Rate analytics - Research

**Researched:** 2026-04-19
**Domain:** query-level retrieval analytics, backend aggregation parity, sync/async API symmetry
**Confidence:** HIGH

## Summary

Phase 21 should follow the existing corpulse pattern: backends own aggregate queries, `Corpulse` and `AsyncCorpulse` expose thin read-only analysis methods, and lightweight TypedDict payloads define the public shape. The current storage layer already persists enough signal to compute both low-confidence and zero-result analytics from `query_hash`, `rank`, `score`, and `retrieved_at`, so no schema or ingestion changes are needed.

**Primary recommendation:** add a backend-level query aggregate surface first, then build paired summary/detail analytics methods on top of it for both sync and async APIs. Keep zero-result analytics separate from low-confidence analytics, but share the same underlying grouped retrieval data model.

## User Constraints

- Phase context explicitly locks summary-plus-detail APIs rather than a single opaque metric.
- Zero-result and low-confidence must remain separate signals.
- No schema changes or new ingestion APIs.
- Backend implementations must remain aligned across SQLite, Postgres, async Postgres, and in-memory storage.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| v1.4-01 | Summary + detail low-confidence analytics | Matches existing `get_*` analysis pattern with a scalar companion metric |
| v1.4-02 | Separate zero-result analytics | Best modeled as a distinct summary/detail surface over grouped query hashes |
| v1.4-03 | Backend parity for query aggregation | Requires extending storage contract and concrete backends uniformly |

## Key Findings

### Existing storage already contains the needed raw data
- Retrieval rows already store `query_hash`, `rank`, `score`, and `retrieved_at` in every backend implementation.
- Existing aggregate methods (`retrieval_counts`) already compute averages from retrieval rows, proving the architecture expects backend-owned aggregation.
- Because `log_retrieval()` hashes the raw query and writes one row per ranked result, query-level grouping can be recovered without schema changes.

### Current public API suggests the right naming and layering
- Sync analysis methods live in `corpulse/core.py` and use `get_*` names for actionable lists.
- Async methods in `corpulse/async_core.py` mirror sync behavior closely rather than defining an async-only shape.
- Typed analysis payloads in `corpulse/models.py` are lightweight `TypedDict`s rather than classes with runtime behavior.

### Zero-result needs a definition choice
- A strict zero-result query cannot be inferred from stored retrieval rows alone if nothing was logged for that query.
- In practice, this phase can only measure zero-result behavior for queries observed by wrappers that log a retrieval attempt even when the result set is empty, or for grouped query aggregates that explicitly count empty attempts.
- Planning should therefore include a validation step to pin the exact zero-result derivation against the current wrappers and manual API behavior before implementation starts.

## Recommended Architecture

### Pattern 1: Extend storage contract with query aggregate methods
Add backend methods that return grouped query-level aggregates, not document-level aggregates. The result should be sufficient to derive:
- total query count in a window
- top score per query
- result count per query
- optional best rank / average score for future v1.4 metrics

This keeps SQL and grouping semantics inside each backend instead of duplicating logic in sync and async facades.

### Pattern 2: Build pure helpers in the core layer
Implement shared helper builders in `corpulse/core.py` that consume grouped query aggregates and produce:
- scalar low-confidence rate
- low-confidence detail rows
- scalar zero-result rate
- optionally zero-result detail rows

Async code should reuse those pure builders after awaiting backend methods.

### Pattern 3: Ship tests at two levels
- backend/contract tests for new query aggregate shapes across storage backends
- core parity tests for sync and async analytics producing the same outputs from the same fixture data

## Risks and Pitfalls

### Pitfall 1: zero-result may be undercounted if empty queries are never logged
If wrappers or manual integrations only call `log_retrieval()` when there are results, a true zero-result query leaves no trace. The plan must avoid promising impossible observability.

### Pitfall 2: query hash removes raw text
Only `query_hash` is stored, not the raw query string. Detail methods therefore need to expose query identifiers or aggregate metadata, not the original natural-language query.

### Pitfall 3: backend contract expansion touches many tests
The storage contract is frozen in `tests/test_backend_contract.py`. Any new contract method must update that contract intentionally and keep all backend fakes/parity fixtures aligned.

## Validation Strategy

### Test layers
- `tests/test_backend_contract.py` for contract changes
- `tests/test_postgres_backend.py` and `tests/test_async_postgres_backend.py` for SQL-path parity
- `tests/test_async_core_integration.py` for sync/async parity over fake backends
- a new analytics-focused test module for low-confidence / zero-result helper behavior

### Suggested split
- Plan 21-01: backend query aggregation contract + concrete backend implementations + contract/backend tests
- Plan 21-02: sync/async analytics methods + TypedDict payloads + parity tests

## Sources

### Primary
- `corpulse/core.py`
- `corpulse/async_core.py`
- `corpulse/models.py`
- `corpulse/backends/base.py`
- `corpulse/backends/sqlite.py`
- `corpulse/backends/postgres.py`
- `corpulse/backends/postgres_async.py`
- `corpulse/backends/memory.py`
- `tests/test_backend_contract.py`
- `tests/test_async_core_integration.py`

## Metadata

- Research date: 2026-04-19
- Valid until: next phase boundary change
