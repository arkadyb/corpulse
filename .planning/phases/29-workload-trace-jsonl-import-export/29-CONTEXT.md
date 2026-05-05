# Phase 29: Workload Trace JSONL Import Export - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 29 makes the Phase 28 workload trace foundation portable. It should add stable JSONL export/import for `rag_request_traces` so users can move traces between corpulse backends, share privacy-preserving benchmark files, and prepare for later workload analytics and replay. This phase does not add reports, session analytics, replay runners, benchmark execution, or new trace-capture fields beyond what is needed to serialize and restore the existing workload trace shape.

</domain>

<decisions>
## Implementation Decisions

### Export Shape
- **D-01:** Use line-only JSONL as the canonical export format: each non-empty line is one workload trace object. Do not require a wrapper object, header line, or sidecar metadata file for Phase 29.
- **D-02:** Include an explicit per-record schema/version field so future importers can detect incompatible files without requiring file-level metadata.
- **D-03:** Export records should preserve the existing `RagRequestTraceRow` fields needed for analytics and replay readiness: request/session identity, query hash, optional query text, input/output token counts, components, timings, timeout/error state, and captured timestamp.
- **D-04:** The JSONL schema must be documented in README/API docs with a small complete example and a privacy-preserving example.

### Import Policy
- **D-05:** Import should be append-oriented by default. Importing JSONL adds traces to the selected backend rather than clearing existing data.
- **D-06:** Provide duplicate protection by default when stable identity is present. Prefer `trace_id` as the primary dedupe key; if unavailable, use a deterministic fallback from `request_id`, `session_id`, `query_hash`, and `captured_at` only if the existing model supports doing so without weakening correctness.
- **D-07:** Re-importing the same export should not create duplicate analytics rows under normal usage.
- **D-08:** Replacement or destructive restore semantics are out of scope for Phase 29.

### Privacy Boundary
- **D-09:** Export defaults should be privacy-first. Raw query/component/answer text must remain optional and should be omitted unless the caller explicitly asks for raw content to be included.
- **D-10:** Hashes, references, token counts, component types, timings, timeout/error state, and timestamps are sufficient for the default export path.
- **D-11:** If raw content export is supported, the API and docs must make the opt-in explicit so users do not accidentally create sensitive benchmark files.

### Public API Shape
- **D-12:** Add user-facing sync and async facade helpers for file-based JSONL workflows. Planning should choose exact names that match existing corpulse style, but the intended shape is similar to `Corpulse.export_rag_request_traces_jsonl(...)`, `Corpulse.import_rag_request_traces_jsonl(...)`, and async equivalents.
- **D-13:** Prefer accepting filesystem paths and file-like text streams where practical. Path-based usage should be easy for users; stream support is useful for tests, piping, and future integrations.
- **D-14:** Backend-level primitives may be added if needed to keep sync/async parity clean, but the documented primary API should be on `Corpulse` and `AsyncCorpulse`.

### Validation Guarantees
- **D-15:** Import should be strict by default: invalid JSON, unsupported schema version, or missing required analytics fields should fail clearly.
- **D-16:** Add an explicit permissive mode only if it can report skipped/invalid lines without silently corrupting analysis. Permissive mode may skip malformed lines and coerce harmless optional fields, but it must not silently accept broken required identity, timestamp, component, or token-count data.
- **D-17:** Import should return or expose a structured result with counts such as imported, skipped duplicates, and invalid/skipped records. Exceptions alone are not enough for batch workflows.
- **D-18:** Round-trip tests must prove exported then imported traces preserve analytics-relevant fields, including privacy-preserving exports without raw text.

### the agent's Discretion
Downstream agents may decide exact helper names, result object shape, schema version literal, and whether JSONL serialization lives in a new module or existing core/backend modules. Those choices should follow existing corpulse public API style, keep optional dependencies out, and preserve sync/async parity.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope
- `.planning/ROADMAP.md` - Defines Phase 29 goal, dependencies, success criteria, and later-phase boundaries.
- `.planning/REQUIREMENTS.md` - Defines `IO-01`, `IO-02`, and `IO-03`, plus out-of-scope constraints around raw retention and replay.
- `.planning/PROJECT.md` - Defines the v1.8 milestone goal and product boundary for workload observability.

### Prior Decisions
- `.planning/phases/27-workload-trace-feasibility-and-schema-contract/27-FEASIBILITY.md` - Locks append-only workload traces, privacy-preserving raw-content optionality, JSONL export/import as Phase 29, and replay as gated later work.
- `.planning/phases/27-workload-trace-feasibility-and-schema-contract/27-PATTERNS.md` - Notes that stable JSONL export shape should precede replay behavior.
- `.planning/phases/28-workload-trace-capture-foundation/28-RESEARCH.md` - Summarizes implemented workload trace model, backend contract, and API surfaces.
- `.planning/phases/28-workload-trace-capture-foundation/28-VERIFICATION.md` - Confirms Phase 28 capture foundation and compatibility checks.
- `.planning/phases/28-workload-trace-capture-foundation/28-03-SUMMARY.md` - Confirms public sync and async workload trace APIs.

### Source Inspiration
- `.planning/research/RAGPULSE-COMPARISON-FEATURES.md` - Explains why JSONL import/export exists: portable workload traces for offline analysis, benchmark sharing, and later replay.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `corpulse.models.RagRequestTraceRow` - Existing typed trace shape to serialize.
- `corpulse.models.RagRequestComponent` and `corpulse.models.RagRequestTimings` - Existing JSON-friendly nested structures for components and timings.
- `StorageBackend.rag_request_traces(since)` - Existing backend read contract for traces.
- Backend insert/read implementations in memory, SQLite, Postgres, and async Postgres - Existing persistence paths that import/export should round-trip through.
- `Corpulse.get_rag_request_traces(...)` and `AsyncCorpulse.get_rag_request_traces(...)` - Existing facade read APIs that export can build on.

### Established Patterns
- corpulse favors explicit facade methods over forcing users to touch backend internals.
- Optional dependencies must remain lazy; JSONL import/export should use the Python standard library.
- Sync and async public APIs should preserve equivalent behavior and test coverage.
- Backends already store nested structures as JSON-compatible payloads, so export/import should avoid ad hoc string formats.

### Integration Points
- Public sync API: `corpulse/core.py`
- Public async API: `corpulse/async_core.py`
- Backend contract: `corpulse/backends/base.py`
- Backend implementations: `corpulse/backends/memory.py`, `corpulse/backends/sqlite.py`, `corpulse/backends/postgres.py`, `corpulse/backends/postgres_async.py`
- Tests: `tests/test_trace_capture.py`, `tests/test_backend_contract.py`, plus focused JSONL import/export tests to add in Phase 29.
- Docs: `README.md` and docstring coverage in `tests/test_docstrings.py`

</code_context>

<specifics>
## Specific Ideas

Recommended canonical line shape:

```json
{"schema_version":"corpulse.rag_request_trace.v1","trace_id":"t1","request_id":"req-1","session_id":"s1","query_hash":"abc","input_token_count":2180,"output_token_count":220,"components":[{"type":"vector_db","refs":[{"doc_id":"policy-1"}],"token_count":1800,"content_hash":"h1"}],"timings":{"ttft_ms":210,"tpot_ms":18,"generation_ms":1850},"timeout":false,"error":null,"captured_at":1710000000.0}
```

Recommended privacy-preserving export behavior:

```json
{"schema_version":"corpulse.rag_request_trace.v1","trace_id":"t1","session_id":"s1","query_hash":"abc","components":[{"type":"vector_db","refs":[{"doc_id":"policy-1"}],"token_count":1800,"content_hash":"h1"}],"timings":{"ttft_ms":210},"captured_at":1710000000.0}
```

Recommended user-facing behavior:

- Export line-only JSONL by default.
- Omit raw text by default.
- Import append-only with duplicate skipping.
- Fail clearly by default on invalid required data.
- Return import/export counts for batch visibility.

</specifics>

<deferred>
## Deferred Ideas

- File-level metadata wrappers or sidecar manifest files belong in a future version only if plain JSONL proves insufficient.
- Destructive replace/restore import belongs outside Phase 29.
- Full replay runners, timestamp scaling, OpenAI-compatible endpoint replay, benchmark result export, and serving comparison helpers remain Phase 32 or future milestone work.
- Workload, serving, and session analytics remain Phases 30 and 31.

</deferred>

---

*Phase: 29-Workload Trace JSONL Import Export*
*Context gathered: 2026-05-04*
