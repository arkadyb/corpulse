---
phase: 23-user-acceptance-rate-analytics
plan: 01
subsystem: api
tags: [acceptance-rate, analytics, engagement, async, sqlite, postgres, testing]
requires:
  - phase: 22-mean-reciprocal-rank-analytics
    provides: retrieval-order proxy pattern, shared helper conventions, and sync/async parity patterns
provides:
  - Proxy `acceptance_rate()` on `Corpulse` and `AsyncCorpulse`
  - Shared pure helper for accepted-row share over event-type engagement aggregates
  - Additive backend contract for grouped engagement event counts
  - Backend smoke coverage proving the metric works across shipped storage backends
affects: [README, analytics API, async facade, backend parity tests, next milestone planning]
tech-stack:
  added: [none]
  patterns: [shared pure metric helper, sync/async parity on existing aggregates, deterministic accepted-event convention]
key-files:
  created:
    - .planning/phases/23-user-acceptance-rate-analytics/23-01-SUMMARY.md
  modified:
    - corpulse/models.py
    - corpulse/backends/base.py
    - corpulse/backends/sqlite.py
    - corpulse/backends/postgres.py
    - corpulse/backends/postgres_async.py
    - corpulse/backends/memory.py
    - corpulse/core.py
    - corpulse/async_core.py
    - corpulse/backends/__init__.py
    - tests/report_fixtures.py
    - tests/test_analytics.py
    - tests/test_async_core_integration.py
    - tests/test_backend_contract.py
    - tests/test_postgres_backend.py
    - tests/test_async_postgres_backend.py
    - README.md
requirements-completed: [v1.5-02, v1.5-03]

# Metrics
duration: 0min
completed: 2026-04-20
---

# Phase 23: User Acceptance Rate analytics Summary

**Accepted engagement-row share over existing event-type aggregates, shipped with sync/async parity and backend smoke coverage**

## Accomplishments
- Added `engagement_event_counts(since)` to the backend contract and implemented it across SQLite, Postgres, async Postgres, and in-memory backends.
- Added a shared `_build_acceptance_rate()` helper and public `acceptance_rate()` methods on both `Corpulse` and `AsyncCorpulse`.
- Froze the accepted-event convention in one place with a normalized allowlist and documented it in the README.
- Updated the canonical fixtures and tests so the acceptance metric is covered by empty, ignored-label, mixed-label, and parity cases.

## Test Results
- `pytest tests/test_analytics.py tests/test_async_core_integration.py tests/test_backend_contract.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py`
- Result: `109 passed, 8 skipped`

## Key Decisions
- Acceptance rate is a row-level metric, not a user-id or session metric, because the existing schema does not store user identity.
- The backend surface remains additive: `engagement_counts()` stays document-level for existing analytics, while acceptance rate uses a new event-type aggregate.
- The accepted-event convention is fixed for v1.5 and normalized once in shared code so sync and async consumers cannot drift.

## Files Changed
- `corpulse/models.py`
- `corpulse/backends/base.py`
- `corpulse/backends/sqlite.py`
- `corpulse/backends/postgres.py`
- `corpulse/backends/postgres_async.py`
- `corpulse/backends/memory.py`
- `corpulse/backends/__init__.py`
- `corpulse/core.py`
- `corpulse/async_core.py`
- `tests/report_fixtures.py`
- `tests/test_analytics.py`
- `tests/test_async_core_integration.py`
- `tests/test_backend_contract.py`
- `tests/test_postgres_backend.py`
- `tests/test_async_postgres_backend.py`
- `README.md`

## Deviations from Plan
- None. The phase stayed within the existing schema and ingestion surface.

## Next Phase Readiness
- Phase 23 is complete.
- v1.5 now has both target metrics shipped and is ready for milestone closeout.

---
*Phase: 23-user-acceptance-rate-analytics*
*Completed: 2026-04-20*
