---
gsd_state_version: 1.0
milestone: v1.9
milestone_name: PyPI Distribution and Release Readiness
status: executing
last_updated: "2026-05-15T07:45:00.000Z"
last_activity: 2026-05-15 -- Phase 34 plan 34-01 complete
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 3
  completed_plans: 1
  percent: 33
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-15)

**Core value:** RAG teams can point corpulse at their vector DB and immediately understand what's wrong with their corpus without manual audits.
**Current focus:** Phase 34: Optional Extras Install Verification

## Current Position

Phase: 34
Plan: 34-01
Status: Plan 34-01 complete
Last activity: 2026-05-15 -- Phase 34 plan 34-01 complete

## Pending Todos

None.

## Deferred Items

Items acknowledged and deferred at milestone close on 2026-04-22:

| Category | Item | Status |
|----------|------|--------|
| quick_task | 260410-mf8-add-asynccorpulse-analysis-parity-with-s | missing |
| quick_task | 260415-hfu-top-corpulse-library-gaps-from-showcase- | missing |
| quick_task | 260415-hyj-review-suggested-specs-1-6-for-implement | missing |

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
- Phase 24 completed on 2026-04-20; generation trace capture foundation is now shipped
- Milestone v1.7 started on 2026-04-22; generic integration wrapping is the next target
- Phase 25 completed on 2026-04-22; shared wrapper engine is now the reusable base for future integrations
- Phase 26 completed on 2026-04-22; Qdrant migration and extension-surface guidance closed milestone v1.7
- Milestone v1.8 started on 2026-05-02; workload observability and replay feasibility are the next target areas
- Phase 27 completed feasibility and Phase 28 delivered the trace capture foundation
- Phase 29 is the next work item and starts with JSONL import/export on top of the trace foundation
- Phase 29 context captured on 2026-05-04; JSONL import/export decisions are ready for planning
- Phase 29 planned on 2026-05-04 with four plans across three waves
- Phase 29 completed on 2026-05-04; Phase 30 is now the next work item
- Phase 30 planned on 2026-05-04 with four sequential plans
- Phase 31 planned on 2026-05-04 with four sequential plans
- Phase 31 completed on 2026-05-04; Phase 32 replay feasibility is now ready to plan
- Phase 32 planned on 2026-05-04 with four sequential plans
- Phase 32 completed on 2026-05-05; v1.8 workload observability and callable replay proof are ready for milestone closeout
- Milestone v1.8 archived on 2026-05-05; next step is fresh milestone definition
- Milestone v1.9 started on 2026-05-15; PyPI distribution and release readiness are the next target areas
- Phase 33 is the next work item and starts with package metadata, README rendering, version consistency, and build artifact readiness
- Phase 33 planned on 2026-05-15 with three sequential plans across metadata/versioning, artifact validation, and README/render checks
- Phase 33 plan 33-01 completed on 2026-05-15; package metadata is now single-sourced and enforced by tests
- Phase 33 plan 33-02 completed on 2026-05-15; release artifacts are now buildable and inspectable
- Phase 33 plan 33-03 completed on 2026-05-15; README install text and PyPI rendering are now release-ready
- Phase 33 completed on 2026-05-15; Phase 34 is next
- Phase 34 planned on 2026-05-15 with three sequential plans across base install isolation, optional extras install matrix, and actionable missing-extra guidance
- Phase 34 plan 34-01 completed on 2026-05-15; base wheel install isolation is now verified

## Accumulated Context

- v1.4 scope: three analytics methods over existing stored data — zero schema changes
- v1.5 scope: two analytics methods over existing stored data — MRR and User Acceptance Rate, still no schema changes
- v1.6 scope: capture-only foundation for generation-layer evaluation data, no scoring yet
- v1.7 scope: shared wrapping infrastructure for future DB integrations is complete, with Qdrant now migrated onto the shared engine
- v1.8 scope: RAGPulse-inspired workload traces, serving metrics, sessions, JSONL export/import, and replay feasibility
- v1.9 scope: PyPI publication readiness, optional extras verification, Trusted Publishing automation, and install documentation
- v1.9 should preserve base-install lightness; optional integrations must remain lazy and explicit extras should be verified from built artifacts
- First PyPI publication should prefer Trusted Publishing over long-lived PyPI API tokens
- Trace capture should preserve prompt/query text, retrieved context references, final answer text, and optional labels/judgments
- Poor-fit generation metrics (Faithfulness, Context Precision, Contradictory Information Density, Answer Relevance / Context Utilization) remain out of scope until trace capture exists
- Existing retrieval/engagement analytics and corpus-health reporting should remain unchanged while adding the new trace layer
- Workload trace capture should support privacy-preserving hashes and references without requiring raw prompt, context, or answer retention

## Decisions

<!-- Phase decisions are appended here by gsd-tools. -->

- [Phase 21]: Query aggregate SQL is ordered by query_hash to keep sync and async backend parity deterministic.
- [Phase 21]: Persist zero-result usage in a dedicated query_attempts table instead of overloading retrieval rows.
- [Phase 21]: Keep low-confidence analytics on retrieval aggregates and zero-result analytics on attempt aggregates.
- [Phase 21]: Record the attempt row in log_retrieval() before any retrieval inserts so empty searches are durable and first-class.
- [Milestone v1.7]: Generalize wrapper interception through a shared engine, but keep normalization recipes explicit per integration.
- [Phase 25]: The generic wrapper layer is dependency-agnostic and proves reuse on non-Qdrant clients before first-party migrations sit on top of it.
- [Phase 26]: Qdrant remains a first-class compatibility wrapper, but the advanced extension path is now the generic `wrap()` / `WrapMethod` API.
- [Milestone v1.8]: Prioritize workload observability and replay feasibility over a second vector DB adapter because the RAGPulse comparison exposed a larger product gap in request/serving behavior.
- [Phase 27]: Workload traces will start from an append-only MVP schema unless the feasibility record documents a blocker.

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

Last activity: 2026-05-05 — v1.8 milestone archived
Stopped at: v1.8 milestone archived; ready for next milestone
Resume file: None
