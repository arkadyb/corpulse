---
phase: 18-indexing-pipeline-mvp
plan: 03
subsystem: pipelines
tags: [indexing, tests, resiliency]
requirements: [PIPE-05]
requires: [18-02]
provides: [indexing-pipeline-verified]
affects: [tests/test_indexing_pipeline.py]
tech-stack: [pytest-asyncio, unittest.mock, qdrant-client]
key-files: [tests/test_indexing_pipeline.py]
decisions:
  - "Use FakeParser, FakeChunker, and FakeEmbedder for deterministic pipeline testing without external dependencies."
  - "Mock asyncio.sleep to verify retry logic without artificial delays."
  - "Verify rollback via Qdrant point deletion on Corpulse registration failure."
metrics:
  duration: 450s
  completed_date: "2026-04-15"
---

# Phase 18 Plan 03: Indexing Pipeline MVP Summary

Comprehensive unit and integration tests for the `index_document` orchestration pipeline, verifying happy path, retry behavior, and consistency rollback.

## Key Changes

### Testing Infrastructure
- Created `tests/test_indexing_pipeline.py`.
- Implemented `FakeParser`, `FakeChunker`, and `FakeEmbedder` fakes that conform to the pipeline protocols.
- Integrated `AsyncMock` for mocking `AsyncQdrantClient` (via `client`) and `AsyncCorpulse`.

### Test Cases
- **Happy Path**: Verified that `index_document` correctly orchestrates the full flow from parsing to registration and returns an `IndexingResult` with the expected chunk count and metadata.
- **Retry Logic**: Verified that the pipeline retries embedding calls on failure with exponential backoff (mocked sleep) and eventually succeeds if the failures are transient.
- **Retry Failure**: Verified that the pipeline correctly propagates the exception after exhausting maximum retry attempts.
- **Rollback Consistency**: Verified that if document registration in Corpulse fails, the pipeline automatically deletes the orphaned points from Qdrant to ensure corpus consistency.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

1. **Check created files exist:**
   - [x] FOUND: tests/test_indexing_pipeline.py

2. **Check commits exist:**
   - [x] FOUND: 7093a91 (test(18-03): add pipeline fakes and happy path test)
   - [x] FOUND: eb63d23 (test(18-03): add retry and rollback tests for indexing pipeline)
