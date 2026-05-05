# Phase 32 Patterns - Replay Feasibility and Minimal Proof

## Closest Existing Patterns

### JSONL Trace Foundation

`corpulse/workload_io.py` is the closest shared module pattern. It defines pure helpers over `RagRequestTraceRow` without backend coupling or optional dependencies. Phase 32 should create `corpulse/replay.py` with the same standard-library-only style.

### Report Payload TypedDicts

`corpulse/models.py` groups typed report payloads together:

- `WorkloadReportPayload`
- `ServingReportPayload`
- `SessionReportPayload`

Replay should add:

- `ReplayRequest`
- `ReplayResult`
- `ReplaySummary`
- `ReplayReportPayload`

near those report models.

### Sync/Async Facades

Phase 29 and Phase 31 established the facade pattern:

- public sync methods on `Corpulse`
- public async methods on `AsyncCorpulse`
- shared helper logic in a reusable module or `corpulse/core.py`
- docstrings with `Args:`
- parity tests with `InMemoryBackend` and `FakeAsyncTraceBackend`

Phase 32 should follow this exactly for replay.

### Tests

Use a new `tests/test_replay.py` file. Reuse local trace helper style from:

- `tests/test_trace_jsonl.py`
- `tests/test_workload_reports.py`
- `tests/test_session_reports.py`

Use injected sleep and clock callables in helper-level tests so replay timing is deterministic and the test suite never waits in real time.

## Suggested File Map

| File | Purpose |
| --- | --- |
| `.planning/phases/32-replay-feasibility-and-minimal-proof/32-REPLAY-DESIGN.md` | Human-readable feasibility decision and replay boundary. |
| `corpulse/models.py` | Add replay payload TypedDicts. |
| `corpulse/replay.py` | Add dependency-free sync and async replay helpers. |
| `corpulse/core.py` | Add `Corpulse.replay_rag_request_traces(...)`. |
| `corpulse/async_core.py` | Add `AsyncCorpulse.areplay_rag_request_traces(...)`. |
| `tests/test_replay.py` | Add helper, sync facade, and async facade tests. |
| `tests/test_docstrings.py` | Add replay public methods to Args docstring checks. |
| `README.md` | Document callable replay proof and endpoint replay boundary. |

## Naming Conventions

Use:

- `ReplayRequest`
- `ReplayResult`
- `ReplaySummary`
- `ReplayReportPayload`
- `replay_rag_request_traces`
- `async_replay_rag_request_traces`
- `areplay_rag_request_traces`

Avoid:

- `benchmark_report`, because benchmark result export is not in v1.8.
- `openai_replay`, because core should not include an endpoint-specific client.
- `traffic_replay`, because this phase is a minimal proof, not a full scheduler.

## Design Constraints

- Do not add database tables or backend methods.
- Do not add `openai`, `httpx`, `requests`, or async file dependencies.
- Do not sleep by default.
- Do not store handler return values in replay reports.
- Do not require raw query text or component metadata.
- Do not mutate traces during replay.
- Do not implement LLM-as-judge or answer quality metrics.

