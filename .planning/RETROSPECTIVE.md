# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.8 — Workload Observability and Replay Feasibility

**Shipped:** 2026-05-05
**Phases:** 6 | **Plans:** 21 | **Sessions:** multiple GSD execution sessions

### What Was Built

- Append-only RAG request trace schema with privacy-first fields for sessions, components, tokens, timings, errors, and content hashes.
- Sync and async `log_rag_request()` APIs across memory, SQLite, Postgres, and async Postgres backends.
- JSONL import/export for captured workload traces with privacy-preserving defaults.
- Workload, serving latency, and session analytics over captured or imported traces.
- Dependency-free sync and async callable replay helpers with explicit endpoint-replay boundaries.

### What Worked

- Feasibility-first planning kept the workload schema small and avoided adding inference or endpoint-client dependencies.
- Reusing existing backend contract tests made cross-backend trace support straightforward to validate.
- Keeping JSONL and replay as trace consumers clarified the trace schema's portability requirements early.
- Public report APIs stayed dictionary-based, matching existing `AsyncCorpulse.report()` semantics.

### What Was Inefficient

- Several older summaries did not expose consistent task metadata, so milestone stats needed correction from the plan files.
- Phase-level verification coverage was uneven before Phase 32; final closeout had to rely on plan summaries plus targeted regression suites.
- Planning artifacts accumulated heavily across Phases 27-32 and should be archived promptly after milestone close.

### Patterns Established

- Privacy-first workload traces: raw query text and component metadata remain optional, while hashes and refs keep analytics useful.
- Shared pure helpers: sync and async public APIs delegate to pure aggregation/replay helpers where possible.
- Dependency-light replay: core corpulse exposes callable replay rather than shipping endpoint-specific clients.
- Regression suites should pair new feature tests with trace capture, JSONL, backend contract, and docstring coverage.

### Key Lessons

1. Treat replay as a consumer of trace data, not as a reason to overfit the trace schema to one endpoint protocol.
2. Store enough structure for analytics and portability, but keep raw prompt/context retention under caller control.
3. Public async parity is cheapest when sync semantics are captured in shared pure helpers first.
4. Milestone summaries should consistently include task counts, key files, and one-liners so closeout automation can compute accurate stats.

### Cost Observations

- Model mix: not recorded in planning artifacts.
- Sessions: multiple manual GSD sessions across planning, execution, and closeout.
- Notable: Sequential inline execution avoided subagent coordination overhead for Phase 32, but required careful manual summary and verification artifact creation.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.7 | multiple | 25-26 | Generic integration wrapping replaced one-off adapter boilerplate. |
| v1.8 | multiple | 27-32 | Feasibility-gated workload observability expanded corpulse beyond corpus health without adding inference dependencies. |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.8 | Replay, JSONL, trace capture, backend contract, workload/session reports, docstrings | 18/18 requirements complete | Callable replay, workload/session aggregations, JSONL codec |

### Top Lessons (Verified Across Milestones)

1. Keep optional integrations and advanced workflows thin around a stable core API.
2. Use structured payloads and backend contracts to preserve sync/async parity.
3. Gate ambiguous product expansions with feasibility records before committing storage or dependency changes.
