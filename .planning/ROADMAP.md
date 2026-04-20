# Roadmap: corpulse

## Milestones

- ✅ **v1.0 — Qdrant Wrapper + Packaging** - Phases 1-5 (shipped 2026-04-07)
- ✅ **v1.1 — Pluggable Storage Backends** - Phases 6-10 (shipped 2026-04-09, archive: `.planning/milestones/v1.1-ROADMAP.md`)
- ✅ **v1.2 — Full Async Parity** - Phases 11-14 (shipped 2026-04-12, archive: `.planning/milestones/v1.2-ROADMAP.md`)
- ✅ **v1.3 — Multi-Tenant Integrations** - Phases 15-20 (shipped 2026-04-15)
- ✅ **v1.4 — Nearly-Free RAG Analytics** - Phase 21 (completed 2026-04-19)
- ✅ **v1.5 — Retrieval Ordering + Acceptance Analytics** - completed 2026-04-20

## Current Milestone: v1.5 — Retrieval Ordering + Acceptance Analytics

**Goal:** Add the remaining low-change retrieval quality metrics already supported by the current retrieval and engagement tables.

**Current status:** Complete. Phase 22 and Phase 23 both shipped; milestone closeout is next.

## Phases

v1.5 phase breakdown:

### Phase 22: Mean Reciprocal Rank analytics

**Goal**: Expose `mean_reciprocal_rank()` over existing retrieval rows and engagement events with sync/async parity.
**Depends on**: Phase 21
**Plans**: 1 plan

Plans:

- [x] 22-01-PLAN.md — Extend query aggregation helpers and implement MRR analytics with parity coverage

### Phase 23: User Acceptance Rate analytics

**Goal**: Expose `acceptance_rate()` over the existing engagement table using a documented accepted-event convention.
**Depends on**: Phase 22
**Plans**: 1 plan

Plans:

- [x] 23-01-PLAN.md — Formalize accepted-event conventions and implement acceptance rate analytics with parity coverage

## Current Status

- Active milestone: `v1.5 — Retrieval Ordering + Acceptance Analytics` (complete)
- Latest shipped milestone: `v1.5 — Retrieval Ordering + Acceptance Analytics`
- Next workflow step: complete milestone v1.5 / plan v1.6

---
