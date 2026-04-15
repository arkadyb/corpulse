---
phase: 18-indexing-pipeline-mvp
plan: 02
subsystem: pipelines
tags: [indexing, resilience, qdrant, corpulse]
requires: [PIPE-01, PIPE-02, PIPE-03]
provides: [resilient-indexing-pipeline]
affects: [corpulse/pipelines/indexing.py]
tech-stack: [asyncio, qdrant-client, numpy]
key-files: [corpulse/pipelines/indexing.py]
decisions:
  - "Used exponential backoff retries for embedding calls to handle transient provider failures."
  - "Implemented rollback logic to delete Qdrant points if Corpulse registration fails, ensuring consistency."
  - "Used `inspect.isawaitable` to handle both sync and async Qdrant client methods transparently."
metrics:
  duration: 300
  completed_date: "2026-04-15"
---

# Phase 18 Plan 02: Indexing Pipeline MVP Summary

## One-liner
Implemented resilient `index_document` orchestration with exponential backoff retries for embeddings and automated rollback for Qdrant points.

## Key Changes
- **Orchestration Flow**: `index_document` now coordinates `Parser`, `Chunker`, `Embedder`, and Qdrant/Corpulse APIs.
- **Resilience**: Added a retry loop with exponential backoff (2, 4, 8 seconds) for the embedding step.
- **Consistency (Rollback)**: Wrapped Corpulse registration in a `try...except` block that triggers deletion of points from Qdrant if registration fails.
- **Deterministic IDs**: Integrated `corpulse.integrations.qdrant.chunk_id` for stable UUIDv5 point IDs.
- **Mean Embedding**: Automatically calculates and stores the mean embedding of all chunks during registration.
- **Flexibility**: Added support for named vectors via the `vector_name` parameter.

## Deviations from Plan
None - plan executed exactly as written.

## Threat Flags
None.

## Known Stubs
None.

## Self-Check: PASSED
- [x] `index_document` implements all steps of the orchestration flow.
- [x] Retry logic is present and uses exponential backoff.
- [x] Rollback logic correctly calls `delete_document_points` on failure.
- [x] Commit 2d6e91a: feat(18-02): implement resilient indexing pipeline orchestration
