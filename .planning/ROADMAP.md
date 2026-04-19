# Roadmap: corpulse

## Milestones

- ✅ **v1.0 — Qdrant Wrapper + Packaging** - Phases 1-5 (shipped 2026-04-07)
- ✅ **v1.1 — Pluggable Storage Backends** - Phases 6-10 (shipped 2026-04-09, archive: `.planning/milestones/v1.1-ROADMAP.md`)
- ✅ **v1.2 — Full Async Parity** - Phases 11-14 (shipped 2026-04-12, archive: `.planning/milestones/v1.2-ROADMAP.md`)
- ✅ **v1.3 — Multi-Tenant Integrations** - Phases 15-20 (shipped 2026-04-15)
- 🚧 **v1.4 — Nearly-Free RAG Analytics** - Phase 21 planned

## Current Milestone: v1.4 — Nearly-Free RAG Analytics

**Goal:** Unlock three retrieval quality signals already latent in the stored data with no new schema and no new ingestion API surface.

**Current status:** Phase 21 is planned and ready for execution.

## Phases

v1.4 phase breakdown has started. Phase 21 is planned and ready for execution.

## Current Status

- Active milestone: `v1.4 — Nearly-Free RAG Analytics`
- Latest shipped milestone: `v1.3 — Multi-Tenant Integrations`
- Next workflow step: `/gsd-execute-phase 21`

### Phase 21: Low-Confidence / Zero-Result Rate analytics

**Goal**: Turn existing retrieval logs into low-confidence / zero-result analytics without adding schema or new ingestion APIs.
**Depends on**: Phase 20
**Requirements**: v1.4-01, v1.4-02, v1.4-03

Plans:

- [x] 21-01-PLAN.md — Extend backend query aggregation contract and implement parity across all storage backends
- [ ] 21-02-PLAN.md — Add sync/async low-confidence and zero-result analytics with parity tests

---
