---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: — Multi-Tenant Integrations
status: completed
stopped_at: Completed 20-01-PLAN.md
last_updated: "2026-04-15T06:20:24.010Z"
last_activity: 2026-04-15 — Centralized models in models.py and refactored backend imports
progress:
  total_phases: 6
  completed_phases: 5
  total_plans: 13
  completed_plans: 12
  percent: 92
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** RAG teams can point corpulse at their vector DB and immediately understand corpus health without manual instrumentation
**Current focus:** Phase 18 — Indexing Pipeline MVP

## Current Position

Phase: 20 — FastAPI Optional Integration
Plan: 01 / 02
Status: In Progress
Last activity: 2026-04-15 — Added optional 'fastapi' extra and implemented get_corpulse_router factory in corpulse.fastapi

Progress bar: [█████████░] 91%

## Pending Todos

- None - Phase 18 complete.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260410-mf8 | Add AsyncCorpulse analysis parity with sync Corpulse for corpus analysis methods | 2026-04-10 | 01d5842 | [260410-mf8-add-asynccorpulse-analysis-parity-with-s](./quick/260410-mf8-add-asynccorpulse-analysis-parity-with-s/) |
| 260415-hfu | Top Corpulse Library Gaps (from showcase work): ship #1 Async Qdrant wrapper fix and #3 public delete_document API immediately | 2026-04-15 | 84b321d | [260415-hfu-top-corpulse-library-gaps-from-showcase-](./quick/260415-hfu-top-corpulse-library-gaps-from-showcase-/) |
| 260415-hyj | Review suggested specs 1-6 for implementation effort, rationale, dependencies, and recommended execution order | 2026-04-15 | 8742c4e | [260415-hyj-review-suggested-specs-1-6-for-implement](./quick/260415-hyj-review-suggested-specs-1-6-for-implement/) |

## Roadmap Evolution

- Phase 5 added: Address review findings in corpus health and Qdrant wrapper
- Milestone v1.1 archived on 2026-04-09; roadmap collapsed to archive links
- Milestone v1.2 roadmap created on 2026-04-10; Phases 11-14 defined
- Milestone v1.3 roadmap created on 2026-04-15; Phases 15-20 defined

## Decisions

- [Phase 11]: Pin sync report and cleanup_report stdout baselines before helper extraction.
- [Phase 11]: Use a frozen InMemoryBackend fixture for byte-for-byte report regression tests.
- [Phase 11]: Keep the new helper layer pure by accepting only pre-fetched lists, maps, and IDs rather than backend objects or formatter dependencies. — This keeps the payload builders reusable for the later async consumer without coupling them to sync-only backend calls or formatting.
- [Phase 11]: Represent the low-engagement divergence test with a tiny epsilon because Python evaluates 3 / 20 as exactly 0.15, which would not exercise the raw-vs-rounded split described in research. — The epsilon keeps the synthetic fixture aligned with the plan intent while preserving the existing helper behavior exactly.
- [Phase 11]: Reused the Plan 01 golden strings as permanent regression gates for sync formatter rewiring.
- [Phase 11]: Kept cleanup_report double-fetch behavior while moving section math into _build_cleanup_payload.
- [Phase 14]: Document AsyncCorpulse as a structured-return API with explicit sync parity notes rather than stdout-oriented wording.
- [Phase 14]: Use an inline AsyncInMemoryBackend adapter in the async demo so the example runs without external services.
- [Phase 16]: Preserve the exact legacy default DDL string shape in `build_schema_sql()` so backend initialization remains byte-for-byte compatible.
- [Phase 16]: Prefix-only tenancy must namespace index names as well as table names to avoid shared-schema collisions.
- [Phase 16]: Both Postgres backends now resolve every SQL identifier through an instance _t(...) helper that combines validated schema and table-prefix state.
- [Phase 16]: AsyncPostgresBackend.create() now builds schema statements from build_schema_sql(...) directly so async DDL cannot drift from sync behavior.
- [Phase 16]: Keep fake SQL-path isolation tests alongside live coverage so tenant separation is still proven when CORPULSE_POSTGRES_TEST_CONNINFO is absent.
- [Phase 16]: Generate unique schema names per live test run to avoid cross-test collisions while reusing a single Postgres database.
- [Phase 17-qdrant-tenant-helpers]: Relaxed payload_schema assertion in in-memory Qdrant tests due to local mode limitations (indexes have no effect).
- [Phase 18]: Use typing.Protocol for Parser, Chunker, and Embedder
- [Phase 18]: Used exponential backoff retries for embedding calls to handle transient provider failures.
- [Phase 18]: Implemented rollback logic to delete Qdrant points if Corpulse registration fails, ensuring consistency.
- [Phase 18]: Use FakeParser, FakeChunker, and FakeEmbedder for deterministic pipeline testing without external dependencies.
- [Phase 18]: Mock asyncio.sleep to verify retry logic without artificial delays.
- [Phase 18]: Verify rollback via Qdrant point deletion on Corpulse registration failure.
- [Phase 19]: Centralized all TypedDict models in corpulse/models.py and migrated backend row types to it while keeping re-exports for compatibility.
- [Phase 20]: Added optional 'fastapi' extra and implemented get_corpulse_router factory in corpulse.fastapi

## Performance Metrics

| Phase | Plan | Duration (s) | Tasks | Files |
|-------|------|--------------|-------|-------|
| 15 | 01 | <1 | 3 | 6 |
| 16 | 01 | 1 min | 3 | 2 |
| 16 | 02 | 5 min | 2 | 4 |
| 16 | 03 | 8 min | 2 | 2 |
| 17 | 01 | 5 min | 2 | 1 |
| Phase 17-qdrant-tenant-helpers P02 | 300 | 2 tasks | 1 files |
| Phase 18 P01 | 300 | 2 tasks | 1 files |
| Phase 18 P02 | 300 | 3 tasks | 1 files |
| Phase 18 P03 | 450 | 2 tasks | 1 files |
| Phase 19 P01 | 900 | 2 tasks | 6 files |
| Phase 19 P02 | 1200 | 3 tasks | 3 files |
| Phase 20 P01 | 600 | 2 tasks | 2 files |

## Session Continuity

Last activity: 2026-04-15 - Completed 16-03 postgres tenancy verification plan
Stopped at: Completed 20-01-PLAN.md
Resume file: None
