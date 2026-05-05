---
phase: 27
phase_slug: workload-trace-feasibility-and-schema-contract
created: 2026-05-02
---

# Validation Strategy: Phase 27

## Scope

Phase 27 validates planning and feasibility artifacts only. It does not validate source-code behavior because implementation begins in Phase 28.

## Required Evidence

- `.planning/phases/27-workload-trace-feasibility-and-schema-contract/27-FEASIBILITY.md` exists.
- The feasibility document includes the exact headings:
  - `## Schema Options`
  - `## Recommended MVP Schema`
  - `## Backend Compatibility`
  - `## Privacy Model`
  - `## Capability Classification`
  - `## Replay Gate`
- The feasibility document references:
  - `StorageBackend`
  - `SQLiteBackend`
  - `PostgresBackend`
  - `AsyncPostgresBackend`
  - `InMemoryBackend`
  - `Corpulse.log_rag_request()`
  - `AsyncCorpulse.alog_rag_request()`
- The capability classification contains:
  - `Implement Now`
  - `Defer`
  - `Out of Scope`
- The recommended MVP schema mentions:
  - `session_id`
  - `request_id`
  - `components`
  - `input_token_count`
  - `output_token_count`
  - `timings`
  - `timeout`
  - `error`
  - `captured_at`
  - `JSONL`

## Verification Commands

```bash
test -f .planning/phases/27-workload-trace-feasibility-and-schema-contract/27-FEASIBILITY.md
rg "## Schema Options|## Recommended MVP Schema|## Backend Compatibility|## Privacy Model|## Capability Classification|## Replay Gate" .planning/phases/27-workload-trace-feasibility-and-schema-contract/27-FEASIBILITY.md
rg "StorageBackend|SQLiteBackend|PostgresBackend|AsyncPostgresBackend|InMemoryBackend|Corpulse\\.log_rag_request\\(\\)|AsyncCorpulse\\.alog_rag_request\\(\\)" .planning/phases/27-workload-trace-feasibility-and-schema-contract/27-FEASIBILITY.md
rg "Implement Now|Defer|Out of Scope" .planning/phases/27-workload-trace-feasibility-and-schema-contract/27-FEASIBILITY.md
rg "session_id|request_id|components|input_token_count|output_token_count|timings|timeout|error|captured_at|JSONL" .planning/phases/27-workload-trace-feasibility-and-schema-contract/27-FEASIBILITY.md
```

## Pass Criteria

All commands above exit 0, and the feasibility document makes a clear recommendation for Phase 28 and Phase 32.
