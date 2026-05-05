# Phase 32 Replay Design: Feasibility and Minimal Proof

## Decision Summary

Callable replay is feasible in Phase 32.

Built-in OpenAI-compatible HTTP replay is deferred.

The current workload trace foundation is strong enough to read captured or JSONL-imported `RagRequestTraceRow` values in deterministic order and invoke a user-provided callable for each trace. That proves the replay boundary without adding a model-client dependency, network behavior, benchmark store, or schema change.

Direct endpoint replay remains outside the v1.8 implementation because the trace schema is privacy-first and analytics-oriented. It records query text when supplied, query hashes, component refs, content hashes, token counts, timings, timeout/error state, and timestamps. It does not guarantee the full raw prompt/message payload needed to reconstruct an endpoint request.

## Current Trace Inputs

Replay can consume the existing `RagRequestTraceRow` fields:

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

The same shape is available from captured traces and from JSONL imports. Destination backends assign local `trace_id` values, so replay should treat `trace_id` as an ordering and reporting field rather than a portable identity.

## OpenAI-Compatible Endpoint Replay Boundary

Built-in OpenAI-compatible endpoint replay is deferred because the current `RagRequestTraceRow` schema does not guarantee a canonical `messages` payload, raw component content, tool payloads, streamed chunks, or response bodies.

OpenAI-compatible replay needs an adapter that can build a valid request for the target endpoint. For Chat Completions, that generally means reconstructing a `messages` list and any endpoint-specific options. For Responses or managed conversation state, it may require a different state model. The current corpulse trace model intentionally avoids requiring those raw payloads.

Phase 32 should therefore expose replay as a callable contract. Users who have raw prompts, OpenAI-compatible messages, endpoint configuration, or service-specific request builders can implement that behavior inside the supplied callable.

## Callable Replay Proof

The Phase 32 implementation should provide dependency-free sync and async replay helpers that:

- sort traces by `(captured_at, trace_id)`
- build a `ReplayRequest` envelope for each trace
- call a user-provided sync or async handler once per replayed trace
- summarize success, failure, skipped rows, scheduled delay, and runtime
- ignore handler return values
- record handler exceptions as failed replay rows
- optionally stop after the first handler error

The callable receives structured trace data, not a raw HTTP request. This keeps core corpulse useful for local simulators, endpoint adapters, and tests without committing to an endpoint protocol.

## Timestamp Scaling

Default replay has no sleeping.

`time_scale=1.0` means real-time captured deltas.

`time_scale>1.0` means faster replay.

`max_delay_seconds` caps long gaps.

For each trace after the first, replay should compute the captured delta from the previous ordered trace:

```text
captured_delta_seconds = max(current.captured_at - previous.captured_at, 0.0)
scheduled_delay_seconds = captured_delta_seconds / time_scale
```

If `time_scale is None`, `scheduled_delay_seconds` is `0.0` and no sleep occurs. If `time_scale <= 0`, replay should raise a `ValueError`.

## Privacy Implications

Replay must preserve the same privacy boundary as workload trace capture and JSONL export.

Raw query text and component metadata may be absent because privacy-first export can omit them. Component refs and content hashes may identify source material without containing the raw content. Replay code must not assume that raw prompts, context passages, answer text, or endpoint payloads exist.

The replay report should not store handler return values. If a caller needs raw model outputs, benchmark responses, or audit artifacts, the supplied callable can persist those outside corpulse under the caller's retention policy.

## Benchmark Result Export Boundary

Phase 32 does not persist replay results or export benchmark summaries.

The replay payload should be limited to operational proof fields such as trace count, replayed count, success/failure counts, skipped count, scheduled delay, runtime, and per-trace error status. Rich benchmark result export belongs to future `REPLAY-03` work after the minimal proof is validated.

## Phase 32 Implementation Scope

Implement now:

- typed replay payloads in `corpulse/models.py`
- dependency-free replay helpers in `corpulse/replay.py`
- sync `Corpulse.replay_rag_request_traces(...)`
- async `AsyncCorpulse.areplay_rag_request_traces(...)`
- deterministic tests for ordering, timing, errors, sync facade, and async facade
- README documentation explaining the callable boundary

Do not implement now:

- built-in OpenAI SDK integration
- built-in HTTP endpoint execution
- streaming/SSE replay
- benchmark export
- replay result persistence
- new backend methods or schema

## Deferred Work

Future replay work can add endpoint adapters, concurrency controls, richer scheduling, benchmark summaries, and before/after comparison exports once the callable proof is stable.

OpenAI-compatible endpoint replay should stay adapter-driven unless corpulse later stores or receives enough raw request material to reconstruct endpoint payloads safely.

## Verification Checklist

- Callable replay is feasible in Phase 32.
- Built-in OpenAI-compatible HTTP replay is deferred.
- Endpoint replay boundary names missing canonical messages, raw component content, tool payloads, streamed chunks, and response bodies.
- Timestamp scaling defines default no-sleep behavior, `time_scale=1.0`, `time_scale>1.0`, and `max_delay_seconds`.
- Privacy section states that raw prompt, context, answer, and endpoint payloads may be absent.
- Benchmark section states that Phase 32 does not persist replay results or export benchmark summaries.
