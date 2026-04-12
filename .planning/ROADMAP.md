# Roadmap: corpulse

## Milestones

- ✅ **v1.0 — Qdrant Wrapper + Packaging** - Phases 1-5 (shipped 2026-04-07)
- ✅ **v1.1 — Pluggable Storage Backends** - Phases 6-10 (shipped 2026-04-09, archive: `.planning/milestones/v1.1-ROADMAP.md`)
- 🔄 **v1.2 — Full Async Parity** - Phases 11-14 (in progress)

## Current Status

- Active milestone: `v1.2 — Full Async Parity`
- Phase 12 is next.
- Next workflow step: `/gsd-execute-phase 12`

---

## v1.2 — Full Async Parity

### Phases

- [x] **Phase 11: Shared Report Helpers** - Extract structured-payload builders into `corpulse/core.py` and refactor sync `report`/`cleanup_report` to consume them via a thin formatter (completed 2026-04-10)
- [x] **Phase 12: Async Parity Methods + Unit Tests** - Implement `AsyncCorpulse.to_dataframe()`, `report()`, `cleanup_report()` on top of shared helpers and prove parity with deterministic async tests (completed 2026-04-10)
- [x] **Phase 13: Live Async Integration Tests** - Gate live asyncpg coverage over the new parity surface behind `CORPULSE_POSTGRES_TEST_CONNINFO` (completed 2026-04-12)
- [ ] **Phase 14: Docs and Examples** - README async section, API-quality docstrings, and a runnable `examples/` script

### Phase Details

#### Phase 11: Shared Report Helpers

**Goal**: Structured-payload builder functions for the report table and cleanup-report sections live in `corpulse/core.py`, consumed by sync and async paths from the same code; sync printed output is byte-for-byte unchanged.
**Depends on**: Phase 10
**Requirements**: REPORT-HELPERS-01, REPORT-HELPERS-02
**Success Criteria** (what must be TRUE):
  1. `pytest` passes on the existing suite with no regressions — sync `Corpulse.report()` and `cleanup_report()` produce identical stdout to their pre-refactor state.
  2. `corpulse/core.py` contains pure helper functions that return structured dicts for the report table rows and each cleanup-report section (inspectable without instantiating `Corpulse`).
  3. `Corpulse.report()` and `Corpulse.cleanup_report()` contain no duplicated data-assembly logic — each delegates to the shared helpers and passes the result through a thin formatter.
  4. Public signatures of `Corpulse.report(window_days)` and `Corpulse.cleanup_report()` are unchanged.
**Plans**: 3 plans
Plans:
- [ ] `11-01-characterization-tests-PLAN.md` — Capture deterministic fixture baselines and pin pre-refactor stdout for `report()` and `cleanup_report()`
- [ ] `11-02-helper-extraction-PLAN.md` — Add unit tests for shared payload contracts and implement the pure helper builders in `corpulse/core.py`
- [ ] `11-03-sync-formatter-refactor-PLAN.md` — Rewire sync formatter methods through shared helpers and prove stdout and fallback behavior are unchanged

#### Phase 12: Async Parity Methods + Unit Tests

**Goal**: `AsyncCorpulse` exposes `to_dataframe()`, `report()`, and `cleanup_report()` backed by the Phase 11 shared helpers, and deterministic async tests prove their output is at parity with sync for the same backend fixture.
**Depends on**: Phase 11
**Requirements**: ASYNC-PAR-01, ASYNC-PAR-02, ASYNC-PAR-03, ASYNC-TEST-01, ASYNC-TEST-02
**Success Criteria** (what must be TRUE):
  1. `AsyncCorpulse.to_dataframe(window_days)` returns a pandas DataFrame with identical column set, row ordering, and status classification as `Corpulse.to_dataframe()` when both operate on the same backend fixture — proven by a deterministic async test.
  2. `AsyncCorpulse.report(window_days)` returns a dict whose health summary, top-K rows, and totals match the structured payload underlying sync `report()` output for the same fixture — proven by a deterministic async test.
  3. `AsyncCorpulse.cleanup_report()` returns a dict whose sections (ghosts, obsolete, stale, suspects), counts, and top-5 examples match the structured payload underlying sync `cleanup_report()` output for the same fixture — proven by a deterministic async test.
  4. Calling `AsyncCorpulse.to_dataframe()` without pandas installed raises `RuntimeError` with a clear install hint — verified by a test.
  5. `pytest tests/test_async_core_integration.py -q` passes with no failures or errors (skipped live tests are acceptable).
**Plans**: 2 plans
Plans:
- [ ] `12-01-PLAN.md` — Extract the shared report-fixture seam and land `AsyncCorpulse.to_dataframe()` parity plus pandas-guard coverage
- [ ] `12-02-PLAN.md` — Implement `AsyncCorpulse.report()` and `cleanup_report()` as shared-helper payload wrappers with deterministic parity tests
**UI hint**: no

#### Phase 13: Live Async Integration Tests

**Goal**: Running `pytest` with `CORPULSE_POSTGRES_TEST_CONNINFO` set exercises `to_dataframe`, `report`, and `cleanup_report` end-to-end against a real Postgres instance via `asyncpg`.
**Depends on**: Phase 12
**Requirements**: ASYNC-TEST-03
**Success Criteria** (what must be TRUE):
  1. With `CORPULSE_POSTGRES_TEST_CONNINFO` set, `pytest tests/test_async_core_integration.py -q` runs the live integration tests for `to_dataframe`, `report`, and `cleanup_report` without skip and without error.
  2. Without `CORPULSE_POSTGRES_TEST_CONNINFO` set, the same live tests are skipped cleanly — the non-live suite still passes in full.
  3. The live tests ingest fixture data, call all three new parity methods, and assert on the shape and key values of the returned payloads — not merely that the calls complete without exception.
**Plans**: 1 plans
Plans:
- [ ] `13-01-PLAN.md` — Add canonical live seed helpers and env-gated asyncpg round-trip assertions for `to_dataframe()`, `report()`, and `cleanup_report()` with sequential verification

#### Phase 14: Docs and Examples

**Goal**: A developer reading the README can understand and use `AsyncCorpulse` as a first-class path; all new `AsyncCorpulse` methods have API-reference-quality docstrings; a runnable script under `examples/` demonstrates the full ingest → analysis → report flow.
**Depends on**: Phase 13
**Requirements**: ASYNC-DOC-01, ASYNC-DOC-02, ASYNC-DOC-03
**Success Criteria** (what must be TRUE):
  1. The README contains a dedicated "Async usage" section showing `AsyncCorpulse` over `AsyncPostgresBackend` with concrete code snippets covering ingestion, analysis, and the structured report methods.
  2. Docstrings on `AsyncCorpulse.to_dataframe()`, `report()`, and `cleanup_report()` document args, return type and structure, exceptions raised, and a parity note vs the sync counterpart.
  3. `python examples/<async_script>.py` runs to completion without error using `InMemoryBackend` (no external dependencies required for the default path).
  4. The `examples/` script output includes visible proof of the report payload (e.g. printing the returned dict) so a reader can see what structured output looks like.
**Plans**: TBD
**UI hint**: no

### Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 11. Shared Report Helpers | 3/3 | Complete    | 2026-04-10 |
| 12. Async Parity Methods + Unit Tests | 2/2 | Complete    | 2026-04-10 |
| 13. Live Async Integration Tests | 1/1 | Complete    | 2026-04-12 |
| 14. Docs and Examples | 0/? | Not started | - |
