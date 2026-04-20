---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: — Retrieval Ordering + Acceptance Analytics
status: ready_for_planning
stopped_at: Phase 22 completed; Phase 23 ready for planning
last_updated: "2026-04-20T01:27:17.237Z"
last_activity: 2026-04-20
progress:
  total_phases: 2
  completed_phases: 1
  total_plans: 1
  completed_plans: 1
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-20)

**Core value:** RAG teams can point corpulse at their vector DB and immediately understand corpus health without manual instrumentation
**Current focus:** Phase 23 — User Acceptance Rate analytics

## Current Position

Phase: 23 (user-acceptance-rate-analytics) — NOT STARTED
Plan: —
Status: Ready to plan
Last activity: 2026-04-20

## Pending Todos

None.

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
- Milestone v1.3 completed on 2026-04-15
- Milestone v1.4 started on 2026-04-18; roadmap reconciled on 2026-04-19
- Phase 21 added: Low-Confidence / Zero-Result Rate analytics
- Phase 21 planned on 2026-04-19 with two execution plans
- Milestone v1.5 started on 2026-04-20; MRR and User Acceptance Rate became the next target metrics
- Phase 22 planned on 2026-04-20; mean reciprocal rank is the next execution target
- Phase 22 completed on 2026-04-20; Phase 23 is now the next work item

## Accumulated Context

- v1.4 scope: three analytics methods over existing stored data — zero schema changes
- v1.5 scope: two analytics methods over existing stored data — MRR and User Acceptance Rate, still no schema changes
- Low-Confidence Rate, MRR, User Acceptance Rate all computable from current retrieval + engagement tables
- Phase 22 scope: document-level proxy MRR using existing retrieval averages joined with engagement counts
- Phase 23 scope: document-level acceptance rate over existing engagement events with a documented accepted-event convention
- Poor-fit generation metrics (Faithfulness, Context Precision, etc.) documented as Out of Scope with rationale in PROJECT.md
- Future milestones planned: v1.5 (Knowledge Gaps + Token Cost), v1.6 (Chunking Fragmentation, Vector Distribution Shift, Latency)

## Decisions

<!-- Phase decisions are appended here by gsd-tools. -->

- [Phase 21]: Query aggregate SQL is ordered by query_hash to keep sync and async backend parity deterministic.
- [Phase 21]: Persist zero-result usage in a dedicated query_attempts table instead of overloading retrieval rows.
- [Phase 21]: Keep low-confidence analytics on retrieval aggregates and zero-result analytics on attempt aggregates.
- [Phase 21]: Record the attempt row in log_retrieval() before any retrieval inserts so empty searches are durable and first-class.

## Performance Metrics

| Phase | Plan | Duration (s) | Tasks | Files |
|-------|------|--------------|-------|-------|
| 15 | 01 | <1 | 3 | 6 |
| 16 | 01 | 1 min | 3 | 2 |
| 16 | 02 | 5 min | 2 | 4 |
| 16 | 03 | 8 min | 2 | 2 |
| 17 | 01 | 5 min | 2 | 1 |
| 17 | 02 | 5 min | 2 | 1 |
| 18 | 01 | 10 min | 2 | 1 |
| 18 | 02 | 5 min | 3 | 1 |
| 18 | 03 | 8 min | 2 | 1 |
| 19 | 01 | 15 min | 2 | 6 |
| 19 | 02 | 20 min | 3 | 3 |
| 20 | 01 | 10 min | 2 | 2 |
| 20 | 02 | 5 min | 1 | 1 |
| Phase 21 P01 | 4min | 2 tasks | 9 files |
| Phase 21 P03 | 8min | 2 tasks | 18 files |

## Session Continuity

Last activity: 2026-04-20 — Completed Phase 22 mean reciprocal rank analytics
Stopped at: Phase 23 ready for planning
Resume file: None
