# Phase 31 Patterns - Session Analytics and Reuse Signals

## Closest Existing Patterns

### Phase 30 Report Helpers

`corpulse/core.py` now contains pure workload and serving helpers:

- `_build_workload_report(...)`
- `_build_serving_report(...)`
- `_build_token_distribution(...)`
- `_build_latency_distribution(...)`
- `_normalize_component_type(...)`

Phase 31 should add `_build_session_report(...)` beside these helpers and reuse `_normalize_component_type(...)` for component taxonomy consistency.

### Typed Payloads

`corpulse/models.py` groups report payload TypedDicts with existing API models. Phase 31 should add `SessionSummary`, `SessionDetail`, `ContextReuseItem`, and `SessionReportPayload` in the same report section.

### Public Facades

Phase 30 added:

- `Corpulse.workload_report(...)`
- `Corpulse.serving_report(...)`
- `AsyncCorpulse.workload_report(...)`
- `AsyncCorpulse.serving_report(...)`

Phase 31 should mirror this with `session_report(...)` on both sync and async clients. The async method should import and call the shared helper, not duplicate aggregation logic.

### Tests

`tests/test_workload_reports.py` constructs trace rows directly for pure-helper tests and uses `InMemoryBackend` plus `FakeAsyncTraceBackend` for sync/async parity. Phase 31 should create `tests/test_session_reports.py` using the same approach.

## Suggested File Map

| File | Purpose |
| --- | --- |
| `corpulse/models.py` | Add session report payload contracts. |
| `corpulse/core.py` | Add session grouping, history growth, context reuse, and sync method. |
| `corpulse/async_core.py` | Add async session report method using shared helper. |
| `tests/test_session_reports.py` | Add helper, missing-session, reuse, and sync/async parity tests. |
| `tests/test_docstrings.py` | Add `session_report` to public Args docstring expectations. |
| `README.md` | Document session report usage and payload categories. |

## Naming Conventions

Use:

- `SessionSummary`
- `SessionDetail`
- `ContextReuseItem`
- `SessionReportPayload`
- `_build_session_report`
- `session_report`

Avoid:

- `session_analysis` because existing APIs use `*_report` for structured report surfaces.
- `reuse_recommendations` because Phase 31 should not make optimization recommendations.

## Design Constraints

- Do not add database tables or backend methods.
- Do not mutate trace data.
- Do not infer context equivalence from raw text.
- Do not merge missing session IDs into one pseudo-session.
- Do not implement cache recommendations from future `CACHE-*` requirements.
- Do not add a second public API unless implementation proves one report payload is insufficient.
