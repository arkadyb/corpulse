---
phase: 17-qdrant-tenant-helpers
plan: 01
subsystem: integrations
tags: [qdrant, multi-tenancy, helpers]
requires: [QDRT-HELP-01, QDRT-HELP-02, QDRT-HELP-03, QDRT-HELP-04, QDRT-HELP-05]
provides: [collection_name_for_user, chunk_id, delete_document_points, ensure_collection]
tech-stack: [qdrant-client, uuid, re]
key-files: [corpulse/integrations/qdrant.py]
metrics:
  duration: 5 min
  completed_date: "2026-04-15"
---

# Phase 17 Plan 01: Qdrant Tenant Helpers Summary

Implemented four reusable Qdrant helper functions in `corpulse.integrations.qdrant` to support common multi-tenant operations: deterministic collection naming, stable chunk ID generation, document-level point deletion, and idempotent collection setup.

## Key Changes

### Deterministic Naming & IDs
- **`collection_name_for_user(user_id, base="corpulse")`**: Sanitizes user IDs to `[a-z0-9_]` and prefixes them with a base string. (QDRT-HELP-01)
- **`chunk_id(doc_id, chunk_index)`**: Generates stable UUIDv5 strings using a fixed `corpulse.ai` namespace, ensuring re-indexing consistency. (QDRT-HELP-02)

### Client Helpers (Sync & Async)
- **`delete_document_points(client, collection_name, doc_id, ...)`**: Supports deleting points by document ID using either direct point IDs or payload filters. Works seamlessly with both sync and async Qdrant clients. (QDRT-HELP-03)
- **`ensure_collection(client, collection_name, vectors_config, ...)`**: Idempotently creates collections and payload indexes. Detects client type and returns a coroutine for async clients to maintain a single unified API entry point. (QDRT-HELP-04)

### Infrastructure
- All Qdrant-specific models are imported lazily inside functions, ensuring the module remains importable without `qdrant-client` installed. (QDRT-HELP-05)

## Verification Results

### Automated Tests
- Verified `collection_name_for_user` and `chunk_id` output via CLI.
- Verified presence and importability of all 4 functions.
- Verified client detection logic for sync/async branching.

```bash
python3 -c "from corpulse.integrations.qdrant import collection_name_for_user, chunk_id; print(collection_name_for_user('User-123!')); print(chunk_id('doc1', 0))"
# Output: corpulse_user_123
# Output: 617fd494-f536-5ad4-9e0f-cfe17240c580
```

## Deviations from Plan

- **Task 1 Pre-completed**: `collection_name_for_user` and `chunk_id` were already present in the codebase (likely from a previous quick fix or uncommitted experiment). Verified they matched plan requirements and kept them as-is.

## Self-Check: PASSED
- [x] All 4 functions implemented/verified.
- [x] Lazy imports preserved.
- [x] Sync/Async both supported.
- [x] Commits made for changes.
