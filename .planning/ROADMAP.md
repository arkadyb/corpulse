# Roadmap: corpulse

## Milestones

- ✅ **v1.0 — Qdrant Wrapper + Packaging** — Phases 1-5 (shipped 2026-04-07)
- ✅ **v1.1 — Pluggable Storage Backends** — Phases 6-10 (shipped 2026-04-09, archive: `.planning/milestones/v1.1-ROADMAP.md`)
- ✅ **v1.2 — Full Async Parity** — Phases 11-14 (shipped 2026-04-12, archive: `.planning/milestones/v1.2-ROADMAP.md`)
- ✅ **v1.3 — Multi-Tenant Integrations** — Phases 15-20 (shipped 2026-04-15)
- ✅ **v1.4 — Nearly-Free RAG Analytics** — Phase 21 (completed 2026-04-19)
- ✅ **v1.5 — Retrieval Ordering + Acceptance Analytics** — completed 2026-04-20
- ✅ **v1.6 — Generation Trace Capture** — completed 2026-04-20, archive: `.planning/milestones/v1.6-ROADMAP.md`
- ✅ **v1.7 — Generic Integration Wrapping** — Phases 25-26 (completed 2026-04-22, archive: `.planning/milestones/v1.7-ROADMAP.md`)
- ✅ **v1.8 — Workload Observability and Replay Feasibility** — Phases 27-32 (shipped 2026-05-05, archive: `.planning/milestones/v1.8-ROADMAP.md`)
- ◆ **v1.9 — PyPI Distribution and Release Readiness** — Phases 33-36 (active)

## Current Status

- Latest shipped milestone: `v1.8 — Workload Observability and Replay Feasibility`
- Active milestone: `v1.9 — PyPI Distribution and Release Readiness`
- Next workflow step: `$gsd-execute-phase 33`

## Phases

### Phase 33: Package Metadata and Build Readiness

**Goal:** Make the package metadata, README, versioning, and build artifacts ready for PyPI.

**Requirements:** PKG-01, PKG-02, PKG-03

**Success Criteria:**
1. `pyproject.toml` contains PyPI-ready metadata, URLs, classifiers, and license-file configuration.
2. Runtime version and package metadata version have a single-source or verified consistency path.
3. `python -m build` produces an sdist and wheel containing the intended package files, README, and license.
4. Package metadata and README render cleanly for PyPI.

### Phase 34: Optional Extras Install Verification

**Goal:** Prove base and optional-extra installs behave correctly from built artifacts without bloating the core install.

**Requirements:** PKG-04, EXTRA-01, EXTRA-02, EXTRA-03, EXTRA-04

**Success Criteria:**
1. A clean environment can install the base artifact and import `corpulse` without optional dependencies.
2. A clean environment can install `corpulse[qdrant]` from the built artifact and import/instantiate the Qdrant wrapper surface.
3. Existing optional extras install cleanly or have documented constraints.
4. Optional integration failures produce actionable `pip install corpulse[...]` guidance.

### Phase 35: Trusted Publishing Release Automation

**Goal:** Add GitHub Actions release automation that builds once and publishes through PyPI Trusted Publishing.

**Requirements:** REL-01, REL-02, REL-03, REL-04

**Success Criteria:**
1. CI builds and stores source and wheel artifacts after tests pass.
2. TestPyPI publishing uses `pypa/gh-action-pypi-publish@release/v1` with OIDC Trusted Publishing.
3. PyPI publishing is tag-gated and uses OIDC Trusted Publishing, not a long-lived PyPI token.
4. The PyPI publish job uses a protected environment or equivalent explicit release gate.

### Phase 36: User Install Docs and Release Validation

**Goal:** Make PyPI install instructions the user-facing path and validate the first release end to end.

**Requirements:** DOC-01, DOC-02, DOC-03, VAL-01, VAL-02

**Success Criteria:**
1. README/docs show `pip install corpulse` as the primary installation command.
2. README/docs show `pip install corpulse[qdrant]` as the primary Qdrant integration command.
3. Release checklist documents version bump, build, TestPyPI validation, PyPI publish, and post-publish smoke checks.
4. Published PyPI package installs in a clean environment.
5. Published `corpulse[qdrant]` extra installs in a clean environment and exposes the Qdrant wrapper surface.

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
| --- | --- | --- | --- | --- |
| 33. Package Metadata and Build Readiness | v1.9 | 2/3 | In Progress | 2026-05-15 |
| 34. Optional Extras Install Verification | v1.9 | 0/0 | Not Started | — |
| 35. Trusted Publishing Release Automation | v1.9 | 0/0 | Not Started | — |
| 36. User Install Docs and Release Validation | v1.9 | 0/0 | Not Started | — |

## Coverage

v1.9 maps 17/17 requirements to phases in `.planning/REQUIREMENTS.md`.

| Requirement | Phase |
|-------------|-------|
| PKG-01 | Phase 33 |
| PKG-02 | Phase 33 |
| PKG-03 | Phase 33 |
| PKG-04 | Phase 34 |
| EXTRA-01 | Phase 34 |
| EXTRA-02 | Phase 34 |
| EXTRA-03 | Phase 34 |
| EXTRA-04 | Phase 34 |
| REL-01 | Phase 35 |
| REL-02 | Phase 35 |
| REL-03 | Phase 35 |
| REL-04 | Phase 35 |
| DOC-01 | Phase 36 |
| DOC-02 | Phase 36 |
| DOC-03 | Phase 36 |
| VAL-01 | Phase 36 |
| VAL-02 | Phase 36 |

---
*Last updated: 2026-05-15 after milestone v1.9 roadmap creation*
