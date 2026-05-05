# Phase 31 Research - Session Analytics and Reuse Signals

## Phase Goal

Add session-level analytics for multi-turn RAG workloads and repeated context behavior.

## Source Inputs

- Roadmap phase: 31 - Session Analytics and Reuse Signals
- Requirements: SESS-01, SESS-02
- Dependency: Phase 30 - Workload and Serving Reports
- Existing trace foundation: `RagRequestTraceRow` with `session_id`, `components`, token counts, timings, status, and `captured_at`

No phase `CONTEXT.md` exists for Phase 31. This plan uses roadmap, requirements, and the completed Phase 30 trace/report implementation as source of truth.

## Existing Foundation

Phase 28 added append-only RAG request traces and backend support. Phase 29 added JSONL portability. Phase 30 added report-style typed payloads and pure helpers over `RagRequestTraceRow`:

- typed payloads in `corpulse/models.py`
- pure report builders in `corpulse/core.py`
- sync public methods on `Corpulse`
- async public methods on `AsyncCorpulse`
- helper and facade tests in `tests/test_workload_reports.py`

Phase 31 should follow the same pattern: compute everything from already stored trace rows, expose structured dictionaries, and keep sync/async logic shared through pure helpers.

## Analytics Semantics

Session analytics should group only traces with a non-empty `session_id`. Traces with `session_id` missing, `None`, or blank should not be collapsed into a fake session. They should be counted as `unsessioned_request_count` so sparse instrumentation is visible and predictable.

For each real session, order traces by `(captured_at, trace_id)` and derive:

- request count
- first and last captured timestamp
- duration in seconds
- whether the session is single-turn or multi-turn
- input token growth from first to last request where token counts exist
- chat history token growth from first to last request where `chat_history` component tokens exist

Aggregate summary should include:

- total request count
- session count
- unsessioned request count
- single-turn session count
- multi-turn session count
- average turns per session
- max turns per session
- follow-up rate as multi-turn sessions / session count
- average session duration seconds
- max session duration seconds

## Reuse Semantics

Context reuse should identify repeated external context within a session. It should be deterministic and derived from component references and hashes, not from raw text or semantic similarity.

Recommended component types for reuse:

- `vector_db`
- `web_search`
- `file_attachment`
- `tool_result`
- `other`

Excluded component types:

- `system_prompt` because repeated system prompts are usually boilerplate
- `user_input` because repeated user text is not context reuse
- `chat_history` because history growth is reported separately

Stable reuse keys:

1. If a component has `refs`, create one key per ref using deterministic JSON with sorted keys.
2. Else if a component has `content_hash`, use the content hash.
3. Ignore components without refs and without content hash.

For each `(session_id, component_type, reuse_key)`, count the number of distinct requests in the session where the key appears. Include only keys present in two or more requests. Report:

- session ID
- component type
- reuse key
- first seen timestamp
- request count
- reuse count (`request_count - 1`)
- request share (`request_count / session_request_count`)

This covers repeated retrieval overlap when vector DB component refs include document or chunk references, while still supporting web/tool/file reuse through the same mechanism.

## API Direction

Expose a single report method with both summary and reuse detail:

- `Corpulse.session_report(window_days=None)`
- `AsyncCorpulse.session_report(window_days=None)`

Payload structure:

- `summary`: aggregate session metrics
- `sessions`: per-session details
- `context_reuse`: repeated context/retrieval overlap rows

This keeps Phase 31 small and composable. Future cache-specific recommendation APIs remain out of scope.

## Validation Architecture

Nyquist validation should focus on requirement coverage:

- SESS-01: Tests cover single-turn sessions, multi-turn sessions, session duration, turns per session, follow-up rate, input token growth, and chat-history growth.
- SESS-02: Tests cover repeated vector DB refs, repeated content hashes, reuse ordering, same-ref reuse within a single session, and no cross-session merging.

Missing session ID behavior must be tested:

- `None` session IDs are counted as unsessioned.
- Blank session IDs are counted as unsessioned.
- Unsessioned traces do not create session detail rows.
- Empty trace windows return stable zero-count payloads.

Regression scope should include:

- `tests/test_session_reports.py`
- `tests/test_workload_reports.py`
- `tests/test_trace_jsonl.py`
- `tests/test_trace_capture.py`
- `tests/test_backend_contract.py`
- `tests/test_docstrings.py`

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Session ordering ambiguity | Sort by `(captured_at, trace_id)` for deterministic results. |
| Missing session IDs distort metrics | Count them separately and exclude them from session aggregates. |
| Reuse detection becomes semantic inference | Use only refs and content hashes, never text similarity or LLM judgment. |
| Repeated components in one request inflate reuse | Count distinct request IDs per reuse key, not component occurrences. |
| Phase overlaps with cache recommendations | Report raw reuse signals only; no recommendations or optimization scoring. |

## Out of Scope

- Replay execution or benchmark scheduling.
- Cache recommendation APIs.
- Semantic similarity between contexts.
- LLM-as-judge or quality evaluation.
- New storage schema or backend query methods.
