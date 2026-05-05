# Phase 29 Pattern Map

## Files To Modify Or Create

| File | Role | Closest Existing Analog | Pattern To Follow |
|------|------|-------------------------|-------------------|
| `corpulse/workload_io.py` | New shared JSONL codec and import result helpers | `corpulse/core.py` report helpers and `corpulse/backends/sqlite.py` JSON handling | Standard-library-only helpers, typed payloads, deterministic serialization |
| `corpulse/models.py` | Add import/export result type | Existing `TypedDict` API models | Keep public result shape typed and simple |
| `corpulse/core.py` | Sync public facade methods | `get_rag_request_traces`, `to_dataframe`, `report` | Explicit methods on `Corpulse`, no optional dependency import |
| `corpulse/async_core.py` | Async public facade methods | async `get_rag_request_traces`, async report/dataframe parity methods | Match sync behavior with `await` only around backend calls |
| `tests/test_trace_jsonl.py` | New JSONL codec and facade coverage | `tests/test_trace_capture.py` | In-memory/fake async tests with exact expected dictionaries |
| `tests/test_docstrings.py` | Public API docstring coverage | Existing method name lists | Add four new public methods |
| `README.md` | User-facing schema and examples | Existing "Workload Trace Capture" section | Concise examples with privacy-first default and raw opt-in note |

## Reusable Code Patterns

### Public facade method placement

Existing methods keep user-facing behavior on `Corpulse` and `AsyncCorpulse`, not backend classes. Phase 29 should add the documented import/export methods near `get_rag_request_traces(...)` or the trace-capture methods so the API remains discoverable.

### JSON-friendly nested payloads

SQLite and Postgres already serialize `components`, `timings`, retrieved context refs, and evaluation labels as JSON-compatible values. The JSONL codec should use `json.dumps(..., sort_keys=True)` for deterministic output and `json.loads(...)` for parse validation.

### Async parity

`AsyncCorpulse` mirrors sync methods while awaiting backend calls. JSONL file reading/writing can stay synchronous because this library does not have an async file dependency and Phase 29 should not add one.

### Tests

`tests/test_trace_capture.py` already has:

- sync trace round trips through `InMemoryBackend`
- async trace parity through a fake async backend
- exact expected payload comparisons

Use a new `tests/test_trace_jsonl.py` for focused Phase 29 behavior and keep existing trace capture tests unchanged.

## Constraints

- Do not require raw query text for export/import.
- Do not add a wrapper/header line to JSONL files.
- Do not make import destructive.
- Do not require backends to preserve imported source `trace_id`.
- Do not add pandas, aiofiles, pydantic, or model-client dependencies.
