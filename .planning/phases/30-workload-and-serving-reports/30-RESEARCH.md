# Phase 30 Research - Workload and Serving Reports

## Phase Goal

Add workload and latency analytics that explain traffic shape, token pressure, component composition, and serving behavior.

## Source Inputs

- Roadmap phase: 30 - Workload and Serving Reports
- Requirements: WORK-01, WORK-02, WORK-03, SERV-01, SERV-02
- Dependency: Phase 29 - JSONL Import/Export
- Codebase patterns: existing trace capture, JSONL workload import/export, sync/async facade parity, pure report helpers in `corpulse/core.py`

No phase `CONTEXT.md` exists for Phase 30. This plan uses the roadmap, requirements, and implemented Phase 29 trace/export surface as the source of truth.

## Existing Foundation

Phase 29 established a portable trace workload surface:

- `RagRequestTraceRow` records captured request metadata, token counts, timing data, component token budgets, status, timeout flag, and tags.
- `RagRequestComponent` captures named prompt/context components with type and token count.
- `RagRequestTimings` captures serving timing fields including TTFT, TPOT, total latency, retrieval, rerank, generation, and queue time.
- `Corpulse.get_rag_request_traces(...)` and `AsyncCorpulse.get_rag_request_traces(...)` expose traces by optional age window.
- JSONL import/export makes synthetic or captured workloads reusable for report tests.

The new reports should be computed from `RagRequestTraceRow` objects. No backend schema change is needed.

## Implementation Direction

Use pure helper functions in `corpulse/core.py` for aggregation and expose small sync/async facade methods:

- `Corpulse.workload_report(window_days=None, long_context_threshold=8000)`
- `Corpulse.serving_report(window_days=None)`
- `AsyncCorpulse.workload_report(window_days=None, long_context_threshold=8000)`
- `AsyncCorpulse.serving_report(window_days=None)`

This follows existing report patterns:

- Facade method reads rows from the backend.
- Pure helper transforms rows into a typed payload.
- Tests validate helper behavior and sync/async facade parity.
- Public methods include Args docstrings to satisfy docstring tests.

## Workload Report Semantics

The workload report should remain descriptive and inference-free. It should summarize:

- Request volume in the selected window.
- Capture span using first and last `captured_at` timestamps.
- Throughput as requests per hour across the observed span.
- Burst pressure as peak requests per minute.
- Input and output token distributions.
- Long-context pressure using a configurable input-token threshold.
- Component composition by component type.

Token distribution should include count, total, average, p50, p95, and max. For empty inputs, counts and totals should be zero and percentile values should be null.

Component composition should aggregate by existing component type values:

- `system_prompt`
- `vector_db_context`
- `chat_history`
- `web_search`
- `user_input`
- `file_attachment`
- `tool_result`
- `other`

Unknown or missing types should be grouped as `other` rather than raising.

## Serving Report Semantics

The serving report should summarize the observed serving behavior directly from trace timing/status fields:

- Request count.
- Timeout count and timeout rate.
- Error count and error rate.
- TTFT distribution.
- TPOT distribution.
- Total latency distribution.
- Stage latency distributions for retrieval, rerank, generation, and queue time.
- Slow-request contributors based on the largest measured stage per trace.

The helper should ignore missing timing values for each distribution instead of failing the whole report. A trace with no timings still contributes to request, error, and timeout counts.

Slow contributors should be deterministic and non-inferential:

- For each trace, inspect known stage timing fields.
- Pick the stage with the largest non-null duration.
- Count stage wins and average their winning durations.
- Sort by count descending, average duration descending, then stage name.

## Validation Architecture

Nyquist validation should focus on requirements coverage rather than implementation mechanics:

- WORK-01: Tests include request volume, observed throughput, and burst-window calculations over multiple timestamps.
- WORK-02: Tests include input/output token distributions and long-context threshold behavior.
- WORK-03: Tests include every canonical component type and aggregation into token/request shares.
- SERV-01: Tests include TTFT, TPOT, total latency, and stage latency distributions.
- SERV-02: Tests include timeout rate, error rate, and slow contributor ordering.

Regression scope should include:

- Existing trace capture tests.
- Phase 29 JSONL import/export tests.
- Backend contract tests.
- Public docstring tests.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Percentile semantics are ambiguous | Use nearest-rank percentile and document it in helper tests. |
| Timestamp span can be zero for one request | Return request count as peak minute and compute throughput over one hour minimum denominator to avoid division by zero. |
| Component token totals may be zero | Return zero shares when denominator is zero. |
| Async and sync methods drift | Build both facades around the same pure helpers and test parity. |
| Reports overreach into evaluation | Keep all outputs descriptive and derived only from trace fields. |

## Out of Scope

- Session analytics such as turns per session, duration, reuse, or overlap. Those belong to Phase 31.
- Replay/harness execution. That belongs to Phase 32.
- Model-quality evaluation or LLM-as-judge behavior.
- New backend tables or trace schema changes.
