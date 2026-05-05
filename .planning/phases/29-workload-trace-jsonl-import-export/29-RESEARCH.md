# Phase 29 Research: Workload Trace JSONL Import Export

## Research Complete

Phase 29 should implement JSONL portability as a standard-library feature layered on top of the Phase 28 workload trace model. The existing architecture already exposes the two operations needed for a portable round trip:

- `Corpulse.get_rag_request_traces(...)` / `AsyncCorpulse.get_rag_request_traces(...)` for export reads
- `StorageBackend.insert_rag_request_trace(...)` for import writes

The main implementation work is therefore a shared JSONL codec plus thin sync and async facade methods.

## Phase Requirements

- `IO-01`: Export workload traces as documented JSONL.
- `IO-02`: Import JSONL workload traces into supported storage backends.
- `IO-03`: Support privacy-preserving export without requiring raw prompt, context, or answer text.

## Existing Architecture Fit

### Trace Shape

`corpulse/models.py` already defines:

- `RagRequestComponent`
- `RagRequestTimings`
- `RagRequestTraceRow`

The export schema should serialize this trace shape directly and add one transport metadata field:

- `schema_version: "corpulse.rag_request_trace.v1"`

The importer should treat missing optional fields as `None` or `{}` / `[]` where that matches the existing model, while rejecting missing required analytics fields in strict mode.

### Backend Contract

`StorageBackend.insert_rag_request_trace(...)` already accepts all import-write fields except `trace_id`. That means import can preserve analytics-relevant data while allowing the destination backend to assign local `trace_id` values. Plans should not add destructive restore semantics or require backends to accept caller-provided primary keys.

### Sync and Async Facades

The established pattern is explicit public methods on `Corpulse` and `AsyncCorpulse`, with equivalent behavior and docstrings. JSONL import/export should follow that pattern:

- sync methods in `corpulse/core.py`
- async methods in `corpulse/async_core.py`
- shared serialization helpers in a new standard-library-only module

## Recommended API Direction

Use facade helpers with path or text stream inputs:

- `Corpulse.export_rag_request_traces_jsonl(destination, *, window_days=None, include_raw_text=False, include_component_metadata=False) -> int`
- `Corpulse.import_rag_request_traces_jsonl(source, *, strict=True) -> RagRequestTraceImportResult`
- `AsyncCorpulse.aexport_rag_request_traces_jsonl(...) -> int`
- `AsyncCorpulse.aimport_rag_request_traces_jsonl(...) -> RagRequestTraceImportResult`

`destination` and `source` should accept `str`, `Path`, or text IO objects. Standard library file I/O is enough; no async file dependency is needed.

## JSONL Schema

Each non-empty line should be one JSON object. Required transport field:

- `schema_version`

Required trace fields for strict import:

- `query_hash`
- `components`
- `timings`
- `timeout`
- `captured_at`

Optional trace fields:

- `trace_id`
- `request_id`
- `session_id`
- `query_text`
- `input_token_count`
- `output_token_count`
- `error`

`components` should be a JSON array of objects with:

- `type`
- `token_count`
- `refs`
- `content_hash`
- `metadata`

Privacy-first export should omit or null raw text fields by default:

- `query_text`
- component `metadata` when `include_component_metadata=False`

The Phase 28 trace shape has no raw answer field, so no answer-specific redaction is needed in Phase 29.

## Duplicate Handling

Destination backends assign their own `trace_id`, so import dedupe should not depend only on source `trace_id`. Use a deterministic identity fingerprint built from analytics-relevant fields:

- `request_id`
- `session_id`
- `query_hash`
- `input_token_count`
- `output_token_count`
- `components`
- `timings`
- `timeout`
- `error`
- `captured_at`

The importer should build fingerprints for existing destination traces before import and skip incoming records whose fingerprint already exists. This makes re-importing the same export idempotent without requiring destructive replacement.

## Validation Architecture

### Automated Validation

Use focused pytest coverage:

- shared codec tests for line-only JSONL, schema version, strict validation, permissive invalid-line reporting, privacy redaction, and deterministic duplicate fingerprints
- sync facade tests proving file/stream export and import round trips through `InMemoryBackend`
- async facade tests proving parity with the sync payloads through the existing fake async backend pattern
- docstring tests for the four new public facade methods
- compatibility tests proving existing trace capture tests still pass

### Verification Commands

Quick command:

```bash
pytest tests/test_trace_jsonl.py tests/test_docstrings.py -q
```

Full phase command:

```bash
pytest tests/test_trace_jsonl.py tests/test_trace_capture.py tests/test_backend_contract.py tests/test_docstrings.py -q
```

## Threat Model

Primary risks:

- accidental raw query or metadata export
- importing malformed traces that corrupt downstream analytics
- duplicate import inflating workload reports
- adding optional dependencies or backend-specific file behavior

Mitigations:

- privacy-first defaults with explicit raw/metadata opt-in flags
- strict validation by default
- structured import result with imported, skipped duplicate, and invalid counts
- deterministic duplicate fingerprinting
- standard-library JSON and file handling only

## Planning Guidance

Plan the phase in four slices:

1. Shared JSONL codec and result types.
2. Sync `Corpulse` import/export facade and sync tests.
3. Async `AsyncCorpulse` import/export facade and parity tests.
4. README/docstring updates and compatibility verification.

Do not add workload reports, session analytics, replay runners, benchmark result export, or destructive restore mode in this phase.
