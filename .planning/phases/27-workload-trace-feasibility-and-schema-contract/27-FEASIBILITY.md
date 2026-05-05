# Phase 27 Feasibility Record: Workload Trace Schema and Scope

## Decision Summary

corpulse should add workload observability with a first-class, append-only RAG request trace model rather than extending generation traces or normalizing the initial design into multiple tables. The MVP should stay additive, preserve current retrieval and generation behavior, and keep raw prompt/context/answer retention optional so the feature remains privacy-preserving and backend-neutral.

The v1.8 scope is feasible on the current architecture because the codebase already has:

- explicit backend contracts in `corpulse/backends/base.py`
- sync and async parity in `corpulse/core.py` and `corpulse/async_core.py`
- JSON-friendly storage patterns in SQLite and Postgres backends
- append-only trace precedent in `generation_traces`
- deterministic backend contract coverage in `tests/test_trace_capture.py`

## Schema Options

### Option A: Single append-only `rag_request_traces` table

Store one row per request and serialize components, timings, and optional metadata as JSON. This is the best MVP because it keeps the schema simple, supports sync/async parity, fits all current backends, and leaves room to add analytic projections later if traffic volume or query patterns demand them.

Pros:

- smallest backend contract surface
- easiest sync/async parity
- easiest JSONL export/import
- easiest privacy-preserving operation
- easiest migration path from current generation trace patterns

Cons:

- JSON fields require careful documentation
- some analytics may later want projections or summary tables

### Option B: Normalized request/components/timings tables

Split request metadata, prompt components, and stage timings into separate tables from the start. This is possible, but it adds unnecessary complexity for the first milestone and increases backend work across SQLite, Postgres, async Postgres, and in-memory test coverage.

Pros:

- more relational structure
- easier direct SQL aggregation for some reports

Cons:

- larger schema and backend contract surface
- more migration overhead
- more code paths to keep in sync
- weaker fit for privacy-preserving JSONL export

### Option C: Extend `generation_traces`

Reuse the existing generation trace table and overload it with session, timing, and component metadata. This is not recommended because generation traces already mean something specific in corpulse: append-only evaluation capture for prompts, retrieved context refs, and final answers. Overloading that table would blur the product boundary and make future analytics harder to reason about.

Pros:

- lowest immediate schema churn

Cons:

- conflates generation evaluation with workload observability
- makes exports and analytics ambiguous
- creates a long-term naming and migration problem

## Recommended MVP Schema

Recommend **Option A**.

The MVP schema should use these exact field names:

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

Recommended shape:

- `trace_id`: internal primary key
- `request_id`: optional caller-provided request identifier
- `session_id`: optional session or conversation identifier
- `query_text`: optional raw user query text
- `query_hash`: stable query hash for privacy-preserving lookup
- `input_token_count`: total input tokens for the request
- `output_token_count`: total output tokens for the response
- `components`: JSON array of structured prompt/context components
- `timings`: JSON object of optional stage timings such as `ttft_ms`, `tpot_ms`, `retrieval_ms`, `rerank_ms`, `generation_ms`, `queue_ms`, and `total_latency_ms`
- `timeout`: boolean flag for timed-out requests
- `error`: optional error string or machine-readable code
- `captured_at`: unix timestamp

This schema is broad enough to support traffic analytics, latency summaries, sessions, and replay export without forcing raw content retention.

## Backend Compatibility

### `StorageBackend`

Phase 27 should add the new workload trace methods explicitly to the storage contract rather than hiding them behind generic metadata helpers. The existing backend interface already makes this pattern clear for retrievals, query attempts, engagement, and generation traces.

### `SQLiteBackend`

SQLite can store the MVP schema cleanly by serializing `components` and `timings` to `TEXT` as JSON, matching the existing generation trace approach. That keeps local development simple and avoids backend-specific special casing.

### `PostgresBackend`

Postgres can use the same append-only model with `TEXT` or `JSONB` for component/timing payloads, but the first implementation should stay aligned with the existing `build_schema_sql()` and tenant-safe naming conventions. The schema should not assume extra extensions.

### `AsyncPostgresBackend`

Async Postgres should mirror sync Postgres exactly. The MVP design is feasible because the data model does not require any async-only behavior.

### `InMemoryBackend`

The in-memory backend should preserve contract tests with a list-based append-only trace store and deterministic ordering on reads, just as it does for generation traces and query aggregates today.

## Privacy Model

The trace layer must be useful without mandatory raw text retention.

Approved privacy-preserving inputs:

- `query_hash`
- `session_id`
- component `content_hash`
- component `refs`
- token counts
- timing values
- timeout/error flags

Optional raw fields:

- `query_text`
- component content bodies
- raw answer text

The feasibility decision is to keep raw text optional, not required. This allows JSONL export, benchmark sharing, and offline analysis without turning corpulse into a data-retention product.

## API Boundary

The MVP should expose workload capture through:

- `Corpulse.log_rag_request()`
- `AsyncCorpulse.alog_rag_request()`

Those APIs should accept structured components and timings, but they should not require a replay client, a dashboard, or a quality-evaluation framework.

The boundary should also preserve current APIs:

- retrieval logging remains intact
- engagement logging remains intact
- generation trace logging remains intact
- report and cleanup behavior remains intact

## Capability Classification

| Capability | Classification | Reason | Target |
|------------|----------------|--------|--------|
| Workload trace schema | Implement Now | This is the foundational model for the rest of v1.8. | Phase 28 |
| `log_rag_request()` / `alog_rag_request()` | Implement Now | Required to capture traces on sync and async paths. | Phase 28 |
| Prompt component taxonomy | Implement Now | Needed to separate system prompt, retrieved context, history, and external sources. | Phase 28 |
| JSONL export/import | Implement Now | Required for offline analysis and replay-ready sharing. | Phase 29 |
| Workload traffic reports | Implement Now | Needed to explain request volume, bursts, and token pressure. | Phase 30 |
| Serving latency reports | Implement Now | Needed to expose TTFT/TPOT and stage timing behavior. | Phase 30 |
| Session analytics | Implement Now | Needed to make multi-turn workloads and reuse visible. | Phase 31 |
| Callable-based replay proof | Defer | Feasible, but should wait until trace export is stable. | Phase 32 |
| OpenAI-compatible endpoint replay | Defer | Useful, but too broad for the initial replay gate. | Phase 32+ |
| Cacheability recommendations | Defer | Nice optimization signal, but not required to validate the workload model. | Future milestone |
| Web dashboard | Out of Scope | corpulse remains library-first; presentation belongs elsewhere. | Never in core library |
| LLM-as-judge quality metrics | Out of Scope | These are generation-evaluation metrics, not workload-observability features. | Separate eval tooling |

## Replay Gate

Replay is feasible only as a gated follow-on to the trace/export foundation.

Decision:

- Phase 32 may implement a minimal callable-based replay proof if export is stable.
- Phase 32 should not promise a full serving benchmark harness.
- OpenAI-compatible endpoint replay stays deferred until the replay proof and export semantics are proven.

Replay must respect the same privacy boundary as capture:

- no requirement for raw prompt retention
- no requirement for raw answer retention
- no accidental production endpoint execution

## Phase 28 Contract

Phase 28 should implement the capture surface only after this feasibility record is accepted:

- `rag_request_traces` append-only storage
- structured components and timings
- sync/async parity
- backend contract coverage for SQLite, Postgres, async Postgres, and in-memory
- no change to retrieval, engagement, generation trace, report, or cleanup contracts

## Phase 32 Contract

Phase 32 should treat replay as bounded by this record:

- acceptable: callable-based replay proof
- acceptable: timestamp scaling if needed for the proof
- acceptable: export-driven playback for stored traces
- not acceptable: a full benchmark suite before trace export is stable
- not acceptable: mandatory client library dependencies for replay feasibility

## Verification Checklist

- Option A is selected and justified.
- The recommended schema names the exact required fields.
- Backend compatibility is explicitly discussed for `StorageBackend`, `SQLiteBackend`, `PostgresBackend`, `AsyncPostgresBackend`, and `InMemoryBackend`.
- The privacy model makes raw content optional.
- The capability table contains `Implement Now`, `Defer`, and `Out of Scope`.
- Replay is gated and does not over-commit Phase 32.
