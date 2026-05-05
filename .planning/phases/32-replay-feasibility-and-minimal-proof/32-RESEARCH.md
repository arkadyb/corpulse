# Phase 32 Research - Replay Feasibility and Minimal Proof

## Phase Goal

Determine whether replay belongs in v1.8 implementation and, if feasible, add the smallest replay proof on top of exported traces.

## Source Inputs

- Roadmap phase: 32 - Replay Feasibility and Minimal Proof
- Requirements: REPLAY-01, REPLAY-02
- Explicit dependency: Phase 29 - Workload Trace JSONL Import Export
- Supporting prior work: Phase 28 trace capture, Phase 30 workload/serving reports, Phase 31 session analytics
- Feasibility boundary: `.planning/phases/27-workload-trace-feasibility-and-schema-contract/27-FEASIBILITY.md`

No Phase 32 CONTEXT.md exists. Planning uses roadmap, requirements, prior phase artifacts, and the already completed trace/report implementation as source of truth.

## External API Context

Official OpenAI documentation checked on 2026-05-04:

- Chat Completions API reference: https://platform.openai.com/docs/api-reference/chat/create-chat-completion
- Conversation state guide: https://platform.openai.com/docs/guides/conversation-state
- Streaming responses guide: https://platform.openai.com/docs/guides/streaming-responses

Relevant planning conclusions:

- Chat Completions replay requires callers to supply a `messages` list. Current corpulse workload traces store component metadata, refs, hashes, query text, token counts, timings, timeout, and error fields, but they do not store a canonical OpenAI `messages` payload.
- OpenAI's current conversation-state guidance prefers Responses/Conversations for managed state and documents manual state management for Chat Completions. That makes "OpenAI-compatible endpoint replay" a broader adapter design problem, not a safe core-library MVP.
- Streaming replay over SSE is also adapter-specific. corpulse can time and invoke a callable, but it should not implement an HTTP/SSE client in v1.8.

## Feasibility Decision

Minimal callable replay is feasible now.

OpenAI-compatible endpoint replay is not feasible as a first-class v1.8 implementation without changing the trace schema or adding a caller-provided adapter. The current trace schema is intentionally privacy-first and does not guarantee raw prompt, full message arrays, tool payloads, or response bodies. A core OpenAI client would also add a network/client dependency that conflicts with the milestone boundary.

Phase 32 should therefore:

1. Write a replay design record that explains the endpoint replay boundary, timestamp scaling, privacy implications, and benchmark export boundary.
2. Implement a dependency-free replay proof that invokes a user-provided callable for each trace.
3. Support timestamp scaling through trace `captured_at` deltas without forcing real-time sleeps by default.
4. Expose sync and async facades that fetch traces using existing `get_rag_request_traces(...)` methods.
5. Avoid HTTP clients, OpenAI SDK dependencies, semantic evaluation, LLM-as-judge, and benchmark result export.

## Existing Foundation

The current codebase already has the pieces needed for callable replay:

- `RagRequestTraceRow` in `corpulse/models.py`
- JSONL codec and duplicate fingerprinting in `corpulse/workload_io.py`
- Sync trace reads through `Corpulse.get_rag_request_traces(...)`
- Async trace reads through `AsyncCorpulse.get_rag_request_traces(...)`
- Import/export tests in `tests/test_trace_jsonl.py`
- Fake async trace backend in `tests/test_trace_capture.py`

Replay should not add backend methods. It can read traces through existing public APIs and operate in memory.

## Recommended API Direction

Add a small replay module plus thin facades:

- `corpulse/replay.py`
- `replay_rag_request_traces(traces, handler, *, time_scale=None, max_delay_seconds=None, stop_on_error=False, sleep=time.sleep, clock=time.monotonic) -> ReplayReportPayload`
- `async_replay_rag_request_traces(traces, handler, *, time_scale=None, max_delay_seconds=None, stop_on_error=False, sleep=asyncio.sleep, clock=time.monotonic) -> ReplayReportPayload`
- `Corpulse.replay_rag_request_traces(handler, window_days=None, time_scale=None, max_delay_seconds=None, stop_on_error=False) -> ReplayReportPayload`
- `AsyncCorpulse.areplay_rag_request_traces(handler, window_days=None, time_scale=None, max_delay_seconds=None, stop_on_error=False) -> ReplayReportPayload`

The handler receives a `ReplayRequest` envelope, not a raw HTTP request. The envelope should contain:

- `sequence_index`
- `trace_id`
- `request_id`
- `session_id`
- `query_text`
- `query_hash`
- `input_token_count`
- `output_token_count`
- `components`
- `timings`
- `timeout`
- `error`
- `captured_at`
- `scheduled_delay_seconds`

This keeps replay usable for endpoint adapters, local simulators, or tests without coupling corpulse to a specific model API.

## Timestamp Scaling

Sort traces by `(captured_at, trace_id)`.

For each trace after the first, compute:

- `captured_delta_seconds = max(current.captured_at - previous.captured_at, 0.0)`
- if `time_scale is None`, `scheduled_delay_seconds = 0.0` and no sleep occurs
- if `time_scale > 0`, `scheduled_delay_seconds = captured_delta_seconds / time_scale`
- if `max_delay_seconds is not None`, cap the scheduled delay to `max_delay_seconds`

Reject `time_scale <= 0` with `ValueError`.

This lets users replay immediately by default, replay at real time with `time_scale=1.0`, replay faster with larger values, or cap long gaps.

## Result Boundary

The replay report should summarize invocation success without storing raw model outputs:

- `ReplaySummary`: trace count, replayed count, success/failure counts, skipped count, total scheduled delay, total runtime
- `ReplayResult`: sequence index, trace identity, scheduled delay, status, error string, duration

Do not include handler return values in the structured payload. If a caller wants raw responses, the user-provided handler can persist them outside corpulse. This avoids turning corpulse into a benchmark result store in v1.8.

## Validation Architecture

Automated validation should cover:

- replay ordering by `(captured_at, trace_id)`
- callable receives `ReplayRequest` envelopes with trace fields and scheduled delay
- default replay does not sleep
- timestamp scaling calls injected sleep with expected delays
- `max_delay_seconds` caps long gaps
- handler exceptions are captured as failed replay results
- sync facade fetches traces through existing backend APIs
- async facade awaits an async handler and matches sync helper semantics
- docstrings require Args sections for new public methods

Recommended commands:

```bash
pytest tests/test_replay.py tests/test_trace_jsonl.py tests/test_docstrings.py -q
pytest tests/test_replay.py tests/test_trace_jsonl.py tests/test_trace_capture.py tests/test_backend_contract.py tests/test_docstrings.py -q
```

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Endpoint replay overpromises current trace fidelity | Write a design record that clearly defers direct OpenAI-compatible HTTP replay unless callers provide raw prompt/message reconstruction. |
| Replay accidentally sleeps for long production gaps | Default `time_scale=None` means no sleep; provide `max_delay_seconds` for capped timing. |
| Handler responses leak raw model output into corpulse reports | Do not store handler return values in `ReplayReportPayload`. |
| New network/client dependency enters core library | Use only standard library and user-provided callables. |
| Async and sync replay diverge | Put shared envelope/result semantics in `corpulse/replay.py` and test parity. |

## Out of Scope

- OpenAI SDK integration.
- Built-in HTTP endpoint clients.
- SSE streaming replay.
- Benchmark result export.
- Full traffic/concurrency scheduler.
- LLM-as-judge or quality evaluation.
- Persisting replay results in corpulse storage.

