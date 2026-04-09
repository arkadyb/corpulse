# Roadmap: corpulse

## Milestones

- ✅ **v1.0 — Qdrant Wrapper + Packaging** - Phases 1-5 (shipped 2026-04-07)
- 🚧 **v1.1 — Pluggable Storage Backends** - Phases 6-10 (in progress)

## Phases

<details>
<summary>✅ v1.0 — Qdrant Wrapper + Packaging (Phases 1-5) — SHIPPED 2026-04-07</summary>

### Phase 1: Package Foundation
**Goal**: The library is installable via pip from GitHub with the correct optional dependency structure
**Depends on**: Nothing (first phase)
**Requirements**: PKG-01, PKG-02, PKG-03, PKG-04, PKG-05
**Success Criteria** (what must be TRUE):
  1. `pip install git+https://github.com/.../corpulse` succeeds on a clean Python 3.10+ environment
  2. `import corpulse` succeeds without qdrant-client installed
  3. `pip install "corpulse[qdrant] @ git+https://github.com/.../corpulse.git"` installs qdrant-client as an optional dependency
  4. Source files live under `corpulse/` package directory (not flat at repo root)
**Plans**: 1/1 plans complete

Plans:
- [x] 01-01-PLAN.md — Restructure into corpulse/ package with pyproject.toml and smoke tests

### Phase 2: Core Tests and Bug Fixes
**Goal**: The existing analytics engine is covered by tests and free of known reliability bugs before the wrapper is layered on
**Depends on**: Phase 1
**Requirements**: TEST-01, FIX-01, FIX-02
**Success Criteria** (what must be TRUE):
  1. `pytest tests/` runs and all tests pass for ghost, duplicate, obsolete, stale, and suspect analytics
  2. SQLite does not raise `database is locked` errors under concurrent writes
  3. `corpus_health()` computes duplicate detection only once (not twice) per call
**Plans**: 1/1 plans complete

Plans:
- [x] 02-01-PLAN.md — Fix WAL mode and double get_duplicates bugs, write analytics test suite

### Phase 3: Qdrant Wrapper
**Goal**: A team using Qdrant can wrap their client in one line and get automatic corpus health tracking — no manual log_retrieval() calls required
**Depends on**: Phase 2
**Requirements**: QDRT-01, QDRT-02, QDRT-03, QDRT-04, QDRT-05, QDRT-06, QDRT-07, QDRT-08, QDRT-09, QDRT-10, TEST-02, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):
  1. Wrapping a QdrantClient with QdrantCorpulseClient intercepts query_points() and search() calls and records retrievals automatically
  2. The wrapped client returns the original Qdrant response objects unchanged — caller code requires no modification
  3. Non-intercepted methods work identically to the unwrapped client via transparent delegation
  4. AsyncQdrantCorpulseClient wraps AsyncQdrantClient with identical interception behavior for async codebases
  5. The qdrant-client package is only required when the wrapper is actually instantiated (not at import time)
**Plans**: 2/2 plans complete

Plans:
- [x] 03-01-PLAN.md — Create integrations package with sync and async Qdrant wrapper classes
- [x] 03-02-PLAN.md — Write comprehensive test suite for both sync and async wrappers

### Phase 4: Documentation
**Goal**: A developer landing on the repo can understand what corpulse does, install it, and start using it — both with and without the Qdrant wrapper
**Depends on**: Phase 3
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05
**Success Criteria** (what must be TRUE):
  1. README shows the exact pip install command, including the [qdrant] extra
  2. README includes a working before/after example: manual log_retrieval() versus QdrantCorpulseClient
  3. README states clearly that corpulse measures corpus health, not answer quality
  4. All public methods have docstrings that describe parameters and return values
**Plans**: 2/2 plans complete

Plans:
- [x] 04-01-PLAN.md — Rewrite README.md with verified install commands, usage examples, and scope statement
- [x] 04-02-PLAN.md — Add complete Google-style docstrings to all public Memento methods with automated test

### Phase 5: Address Review Findings
**Goal**: corpus_health() and the Qdrant wrappers behave predictably against empty corpora, overlapping noise categories, and the current qdrant-client API
**Depends on**: Phase 4
**Requirements**: RVW-CH-01, RVW-CH-02, RVW-QD-01, RVW-QD-02
**Success Criteria** (what must be TRUE):
  1. corpus_health() returns the same response keys for empty and populated corpora
  2. noise_estimate counts unique noisy documents once even when categories overlap
  3. Sync and async Qdrant wrappers match the installed client's behavior without fabricating compatibility
  4. Named-vector capture stores the requested vector and preserves boolean with_vectors=True behavior
**Plans**: 3/3 plans complete

Plans:
- [x] 05-01-PLAN.md — Bootstrap test environment and add regression coverage for corpus_health and Qdrant wrapper findings
- [x] 05-02-PLAN.md — Fix corpus_health schema stability and unique noisy-doc noise estimation
- [x] 05-03-PLAN.md — Reconcile Qdrant wrapper upstream behavior and named-vector capture

</details>

---

### 🚧 v1.1 — Pluggable Storage Backends (In Progress)

**Milestone Goal:** Make the persistence layer pluggable so corpulse can use PostgreSQL (or other backends) in production services, while keeping SQLite as the zero-configuration default.

#### Phase 6: Storage Foundation
**Goal**: The StorageBackend abstraction exists, SQLiteBackend preserves the 41-test regression baseline, InMemoryBackend enables test writing, and Corpulse accepts an explicit backend argument
**Depends on**: Phase 5
**Requirements**: ABS-01, ABS-02, ABS-03, ABS-04, BACK-01, BACK-02, BACK-03, BACK-06, INT-01
**Success Criteria** (what must be TRUE):
  1. `Corpulse()` with no arguments works exactly as before — SQLite default, all 41 existing tests pass
  2. `Corpulse(backend=SQLiteBackend("path/to/db"))` behaves identically to the default
  3. `Corpulse(backend=InMemoryBackend())` records retrievals and produces analytics from in-memory state with no file I/O
  4. Any native DB exception raised inside a backend surfaces as `StorageBackendError` at the caller boundary
  5. All backends support `with Corpulse(...) as c:` context manager and explicit `.close()`
**Plans**: 2/3 plans complete

Plans:
- [x] 06-01-PLAN.md — Freeze the backend contract and add shared backend contract/core integration test scaffolding
- [x] 06-02-PLAN.md — Refactor DB into SQLiteBackend, keep db.py compatibility, and wire Corpulse backend injection
- [x] 06-03-PLAN.md — Implement InMemoryBackend and finish shared parity coverage

#### Phase 7: PostgresBackend (Sync)
**Goal**: A service using PostgreSQL can point corpulse at it and get the same corpus health analytics as SQLite — schema created automatically, no migrations needed
**Depends on**: Phase 6
**Requirements**: BACK-04, INT-02
**Success Criteria** (what must be TRUE):
  1. `pip install "corpulse[postgres]"` installs psycopg>=3.2 as an optional dependency
  2. `Corpulse(backend=PostgresBackend(conninfo="..."))` auto-creates the schema on first connection and records retrievals
  3. The shared parametrized test fixture passes for PostgresBackend (same assertions as SQLite and InMemory)
  4. psycopg is only imported when PostgresBackend is instantiated — not at `import corpulse` time
**Plans**: 1/1 plans complete

Plans:
- [x] 07-01-PLAN.md — Implement PostgresBackend with psycopg3, schema auto-init, BYTEA handling, and add [postgres] extra

#### Phase 8: AsyncPostgresBackend
**Goal**: An async service (FastAPI, etc.) can use corpulse with PostgreSQL without blocking the event loop — async pool, async initialize(), and optional extras for both Postgres backends
**Depends on**: Phase 7
**Requirements**: BACK-05, INT-02, INT-03
**Success Criteria** (what must be TRUE):
  1. `pip install "corpulse[postgres-async]"` installs asyncpg>=0.29 as an optional dependency
  2. `Corpulse(backend=await AsyncPostgresBackend.create(dsn="..."))` works in async context with a connection pool
  3. The shared parametrized test fixture passes for AsyncPostgresBackend
  4. Both PostgresBackend and AsyncPostgresBackend support connection pooling with configurable pool size
  5. asyncpg is only imported when AsyncPostgresBackend is instantiated — not at `import corpulse` time
**Plans**: 1/1 plans complete

Plans:
- [x] 08-01-PLAN.md — Implement AsyncPostgresBackend with asyncpg, async pool, async initialize(), and add [postgres-async] extra

#### Phase 9: Harden Sync Postgres Backend
**Goal**: The sync Postgres backend meets the milestone pooling requirement and has current verification evidence that proves the production Postgres path is actually complete
**Depends on**: Phase 8
**Requirements**: BACK-04, INT-03
**Gap Closure**: Closes milestone audit gaps for stale Phase 7 evidence and missing sync pooling support
**Success Criteria** (what must be TRUE):
  1. `Corpulse(backend=PostgresBackend(conninfo="..."))` still auto-creates the schema and passes the shared backend parity suite
  2. `PostgresBackend` uses configurable connection pooling rather than a single long-lived psycopg connection
  3. Pooling behavior is covered by automated tests or equivalent deterministic verification artifacts
  4. Phase 7/9 verification artifacts provide milestone-grade evidence that the sync Postgres path is complete
**Plans**: 0/2 plans complete

Plans:
- [ ] 09-01-PLAN.md — Refactor PostgresBackend to use configurable sync pooling and update parity coverage
- [ ] 09-02-PLAN.md — Refresh Phase 7/9 verification artifacts and close BACK-04/INT-03 traceability

#### Phase 10: Make Async Backend Usable From Corpulse
**Goal**: The async Postgres backend is reachable through a supported Corpulse integration path, with verification artifacts that prove async usage works end to end
**Depends on**: Phase 9
**Requirements**: BACK-05
**Gap Closure**: Closes milestone audit gaps for async facade incompatibility, missing Phase 8 verification, and broken async backend injection flow
**Success Criteria** (what must be TRUE):
  1. Corpulse exposes a supported async integration path for `AsyncPostgresBackend.create(...)` that matches the documented milestone contract
  2. The shared backend contract or equivalent async integration suite passes against `AsyncPostgresBackend`
  3. Phase 8/10 verification artifacts prove the async backend path works in a real async usage flow
  4. Requirement traceability and milestone evidence show `BACK-05` closed by verified implementation rather than code-only claims
**Plans**: 0/0 plans complete

Plans:
- None yet

## Progress

**Execution Order:**
Phases execute in numeric order: 6 → 7 → 8 → 9 → 10

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Package Foundation | v1.0 | 1/1 | Complete | 2026-04-02 |
| 2. Core Tests and Bug Fixes | v1.0 | 1/1 | Complete | 2026-04-04 |
| 3. Qdrant Wrapper | v1.0 | 2/2 | Complete | 2026-04-07 |
| 4. Documentation | v1.0 | 2/2 | Complete | 2026-04-07 |
| 5. Address Review Findings | v1.0 | 3/3 | Complete | 2026-04-07 |
| 6. Storage Foundation | v1.1 | 3/3 | Complete | 2026-04-08 |
| 7. PostgresBackend (Sync) | v1.1 | 1/1 | In progress | - |
| 8. AsyncPostgresBackend | v1.1 | 1/1 | In progress | - |
| 9. Harden Sync Postgres Backend | v1.1 | 0/0 | Planned | - |
| 10. Make Async Backend Usable From Corpulse | v1.1 | 0/0 | Planned | - |
