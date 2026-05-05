# Phase 30 Patterns - Workload and Serving Reports

## Closest Existing Patterns

### Core Report Helpers

`corpulse/core.py` already keeps report assembly in pure helper functions:

- `_build_report_rows(...)`
- `_build_report_summary(...)`
- `_build_cleanup_payload(...)`
- `_build_low_confidence_queries(...)`
- `_build_zero_result_queries(...)`
- `_build_query_rate(...)`

Phase 30 should follow this pattern with `_build_workload_report(...)` and `_build_serving_report(...)`.

### Sync Facade

`Corpulse.report(...)` fetches backend rows and delegates transformation to helper functions. Phase 30 should add small facade methods that fetch trace rows with `get_rag_request_traces(...)` and delegate aggregation to pure helpers.

### Async Facade

`corpulse/async_core.py` imports helper functions from `corpulse/core.py` and mirrors sync methods using async backend calls. Phase 30 should mirror the sync method names and return payload shapes from the same helpers.

### Typed Payloads

`corpulse/models.py` contains `TypedDict` payload contracts for public data structures. Phase 30 report payloads should be added there instead of returning untyped nested dicts.

### Tests

Existing tests use in-memory fake backends and direct model rows to validate behavior without external services. Phase 30 tests should construct `RagRequestTraceRow` values directly for helper-level tests, then use fake sync/async backends for facade parity.

## Naming Conventions

Use public method names that match the report categories in the roadmap:

- `workload_report`
- `serving_report`

Use model names that make payload roles explicit:

- `TokenDistribution`
- `WorkloadTrafficSummary`
- `WorkloadTokenSummary`
- `WorkloadComponentSummary`
- `WorkloadReportPayload`
- `LatencyDistribution`
- `ServingSlowContributor`
- `ServingReportPayload`

## Design Constraints

- Do not add new dependencies.
- Do not add a backend schema migration.
- Do not infer semantic quality or correctness.
- Do not call an LLM or evaluator.
- Do not duplicate sync/async aggregation logic.
- Keep empty-input report payloads stable and typed.

## Suggested File Map

| File | Purpose |
| --- | --- |
| `corpulse/models.py` | Add typed report payload contracts. |
| `corpulse/core.py` | Add pure aggregation helpers and sync public methods. |
| `corpulse/async_core.py` | Add async public methods using shared helpers. |
| `tests/test_workload_reports.py` | Add workload, serving, and sync/async parity tests. |
| `tests/test_docstrings.py` | Extend expectations if public method enumeration is explicit. |
| `README.md` | Document how to call the reports and what they return. |

## Compatibility Notes

The new report APIs should not change existing trace capture, report, cleanup, or JSONL behavior. Existing Phase 29 JSONL exports should be usable as imported workloads for these reports through `import_rag_request_traces_jsonl(...)` followed by report calls.
