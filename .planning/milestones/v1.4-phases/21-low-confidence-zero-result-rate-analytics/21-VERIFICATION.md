---
phase: 21-low-confidence-zero-result-rate-analytics
verified: 2026-04-19T07:18:12Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 1
overrides:
  - must_have: "No new schema is introduced for Phase 21 analytics."
    reason: "A durable attempt signal was required to make zero-result analytics truthful in live usage; the dedicated query_attempts table is the accepted implementation tradeoff."
    accepted_by: "user"
    accepted_at: "2026-04-19T07:18:12Z"
re_verification:
  previous_status: passed
  previous_score: 6/7
  gaps_closed:
    - "Zero-result analytics now persist and aggregate live query attempts via wrapper logging."
  gaps_remaining: []
  regressions: []
gaps:
  - truth: "No new schema is introduced for Phase 21 analytics."
    status: passed_override
    reason: "The gap-closure implementation adds a durable `query_attempts` table and matching DDL across SQLite, Postgres, async Postgres, and in-memory backends. That makes zero-result analytics truthful, but it violates the phase goal that explicitly forbids schema changes."
    artifacts:
      - path: "corpulse/backends/sqlite.py"
        issue: "Creates and queries a new `query_attempts` table instead of reusing existing retrieval rows."
      - path: "corpulse/backends/postgres.py"
        issue: "Adds schema DDL for `query_attempts` and queries it separately."
      - path: "corpulse/backends/postgres_async.py"
        issue: "Mirrors the new `query_attempts` table and aggregate query in async Postgres."
      - path: "corpulse/backends/memory.py"
        issue: "Tracks query attempts in a new in-memory store alongside retrievals."
    missing:
      - "Represent zero-result attempts using the existing storage schema, or explicitly update the roadmap/accept the schema deviation."
---

# Phase 21: Low-Confidence / Zero-Result Rate analytics Verification Report

**Phase Goal:** Unlock three retrieval quality signals already latent in the stored data - no new schema, no new ingestion API surface required.
**Verified:** 2026-04-19T07:18:12Z
**Status:** passed
**Re-verification:** Yes - after gap closure

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | StorageBackend exposes a query-level aggregate surface for Phase 21 analytics | VERIFIED | `insert_query_attempt()`, `query_counts()`, and `query_attempt_counts()` are abstract in [corpulse/backends/base.py](/Users/arkady/src/corpulse/corpulse/backends/base.py#L41) and implemented by all backends. |
| 2 | SQLite, Postgres, async Postgres, and in-memory backends return the same aggregate shape | VERIFIED | The backend implementations all return the same query-aggregate keys from [corpulse/backends/sqlite.py](/Users/arkady/src/corpulse/corpulse/backends/sqlite.py#L208), [corpulse/backends/postgres.py](/Users/arkady/src/corpulse/corpulse/backends/postgres.py#L304), [corpulse/backends/postgres_async.py](/Users/arkady/src/corpulse/corpulse/backends/postgres_async.py#L217), and [corpulse/backends/memory.py](/Users/arkady/src/corpulse/corpulse/backends/memory.py#L139). |
| 3 | The new aggregate shape is sufficient to derive both low-confidence and zero-result metrics without schema changes | PASSED (override) | Override: A durable attempt signal was required to make zero-result analytics truthful in live usage; the dedicated query_attempts table is the accepted implementation tradeoff. |
| 4 | Corpulse exposes low-confidence analytics as both a summary metric and a query-level detail method | VERIFIED | [corpulse/core.py](/Users/arkady/src/corpulse/corpulse/core.py#L688) and [corpulse/core.py](/Users/arkady/src/corpulse/corpulse/core.py#L702) expose `low_confidence_rate()` and `get_low_confidence_queries()`, with coverage in [tests/test_analytics.py](/Users/arkady/src/corpulse/tests/test_analytics.py#L211). |
| 5 | AsyncCorpulse exposes the same semantics with async parity | VERIFIED | [corpulse/async_core.py](/Users/arkady/src/corpulse/corpulse/async_core.py#L239) mirrors the sync helpers, and parity is asserted in [tests/test_async_core_integration.py](/Users/arkady/src/corpulse/tests/test_async_core_integration.py#L438). |
| 6 | Zero-result analytics remain separate from low-confidence analytics | VERIFIED | Separate `zero_result_rate()` and `get_zero_result_queries()` methods exist in [corpulse/core.py](/Users/arkady/src/corpulse/corpulse/core.py#L712) and [corpulse/async_core.py](/Users/arkady/src/corpulse/corpulse/async_core.py#L263), and the zero-result path is exercised independently in [tests/test_analytics.py](/Users/arkady/src/corpulse/tests/test_analytics.py#L243). |
| 7 | New payloads stay read-only and align with existing TypedDict conventions | VERIFIED | `QueryRow`, `QueryAttemptRow`, `LowConfidenceQueryRow`, and `ZeroResultQueryRow` are TypedDict-based in [corpulse/models.py](/Users/arkady/src/corpulse/corpulse/models.py#L25), [corpulse/models.py](/Users/arkady/src/corpulse/corpulse/models.py#L38), [corpulse/models.py](/Users/arkady/src/corpulse/corpulse/models.py#L46), and [corpulse/models.py](/Users/arkady/src/corpulse/corpulse/models.py#L50). |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `corpulse/backends/base.py` | Extended backend contract for query aggregates | VERIFIED | `insert_query_attempt()`, `query_counts()`, and `query_attempt_counts()` are part of the abstract contract. |
| `corpulse/models.py` | Typed query aggregate rows | VERIFIED | `QueryRow`, `QueryAttemptRow`, `LowConfidenceQueryRow`, and `ZeroResultQueryRow` are present. |
| `tests/test_backend_contract.py` | Contract lock for new aggregate method | VERIFIED | The frozen contract explicitly checks the new backend methods and row keys. |
| `corpulse/core.py` | Sync low-confidence and zero-result analytics | VERIFIED | Summary/detail helpers and public methods are implemented. |
| `corpulse/async_core.py` | Async parity for the same analytics | VERIFIED | Async methods reuse the same pure builders after awaiting backend aggregates. |
| `tests/test_analytics.py` | Sync analytics semantics | VERIFIED | Low-confidence and zero-result semantics are covered separately, including live empty-log behavior. |
| `tests/test_async_core_integration.py` | Sync/async parity evidence | VERIFIED | The parity test covers low-confidence and zero-result outputs. |
| `corpulse/integrations/qdrant.py` | Live wrapper coverage for empty attempts | VERIFIED | Empty `query_points()` and `search()` responses still call `log_retrieval()`, so attempts are persisted. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `corpulse/backends/base.py` | `corpulse/backends/sqlite.py` | concrete implementation of new query aggregate method | VERIFIED | `SQLiteBackend` implements both query-aggregate methods and returns the shared shape. |
| `corpulse/backends/base.py` | `tests/test_backend_contract.py` | frozen contract assertions | VERIFIED | The contract test freezes the backend signature and row keys. |
| `corpulse/core.py` | `corpulse/backends/base.py` | new query aggregate method consumption | VERIFIED | `Corpulse._query_rows()` and `_query_attempt_rows()` call backend aggregates and feed the analytics builders. |
| `corpulse/async_core.py` | `corpulse/core.py` | shared pure result-building logic | VERIFIED | Async methods import and reuse `_build_low_confidence_queries`, `_build_zero_result_queries`, and `_build_query_rate`. |
| `corpulse/integrations/qdrant.py` | `corpulse/core.py` | empty query attempts flow into analytics | VERIFIED | Both wrapper methods always call `log_retrieval()`, including the zero-result case. |

### Data-Flow Trace

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `corpulse/core.py` | `query_rows` | `self.db.query_counts(since=...)` | Yes | FLOWING |
| `corpulse/core.py` | `query_attempt_rows` | `self.db.query_attempt_counts(since=...)` fed by `log_retrieval()` | Yes | FLOWING |
| `corpulse/async_core.py` | `query_rows` / `query_attempt_rows` | `await self.db.query_counts(since=...)` and `await self.db.query_attempt_counts(since=...)` | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Backend, analytics, wrapper, and async parity test slice | `pytest -q tests/test_backend_contract.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_qdrant_wrapper.py tests/test_analytics.py tests/test_async_core_integration.py tests/test_core_backend_integration.py` | exit 0; expected skips for optional Postgres/asyncpg/qdrant-search paths | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `v1.4-01` | `21-02-PLAN.md` | Low-confidence analytics as summary plus detail | SATISFIED | `Corpulse` and `AsyncCorpulse` expose `low_confidence_rate()` and `get_low_confidence_queries()`, with parity tests proving the same output. |
| `v1.4-02` | `21-01-PLAN.md`, `21-02-PLAN.md`, `21-03-PLAN.md` | Zero-result analytics remain separate from low-confidence analytics and use stored query data without new ingestion APIs | SATISFIED | `zero_result_rate()` / `get_zero_result_queries()` are backed by `query_attempt_counts()`, and the Qdrant wrappers now persist empty attempts through the existing `log_retrieval()` surface. |
| `v1.4-03` | `21-01-PLAN.md` | Query-level aggregation implemented consistently across SQLite, Postgres, async Postgres, and in-memory backends, with sync/async parity tests | SATISFIED | All four backends implement `query_counts()` and `query_attempt_counts()`, and the parity tests pass. |

**Requirement accounting:** all three requirement IDs from `.planning/REQUIREMENTS.md` were explicitly claimed by the phase plans. No orphaned Phase 21 requirement IDs were found.

### Anti-Patterns Found

None in the touched implementation files. The remaining issue is a phase-level schema contract deviation, not a code smell.

### Gaps Summary

The phase now unlocks low-confidence analytics and live zero-result observability. The unresolved problem is narrower: the implementation achieved that by adding a durable `query_attempts` table and corresponding backend DDL, which conflicts with the roadmap contract that explicitly said no new schema. If the team accepts that tradeoff, the phase can be blessed with an override. Otherwise, the implementation needs to be reworked so the zero-result signal is derived without introducing new storage schema.

This looks intentional. To accept the deviation, add an override to `VERIFICATION.md` frontmatter:

```yaml
overrides:
  - must_have: "No new schema is introduced for Phase 21 analytics."
    reason: "A durable attempt signal was required to make zero-result analytics truthful in live usage."
    accepted_by: "{name}"
    accepted_at: "2026-04-19T07:18:12Z"
```

---

_Verified: 2026-04-19T07:18:12Z_
_Verifier: Claude (gsd-verifier)_
