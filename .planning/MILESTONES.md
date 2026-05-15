# Milestones

## v1.9 PyPI Distribution and Release Readiness (Shipped: 2026-05-15)

**Phases completed:** 4 phases, 11 plans, 27 tasks

**Key accomplishments:**

- PyPI metadata now uses Hatchling dynamic versioning, with tests enforcing the single-source version contract and the required discoverability fields.
- Source and wheel artifacts now include the release files we need, and the package test suite verifies the built outputs when they exist.
- README installation instructions now lead with PyPI commands, and the built artifacts pass `twine check` with the new long-description content.
- A gated venv-based harness now proves the built wheel installs cleanly without optional dependencies and keeps the install tests opt-in for normal runs.
- The built wheel now installs all declared extras in isolated venvs, and the Qdrant wrapper surface resolves from the `corpulse[qdrant]` extra.
- Optional dependency failures now tell users exactly what to install, and the full phase verification suite passes against the rebuilt wheel.
- Exact post-publish PyPI smoke checks for `corpulse` and `corpulse[qdrant]`, with tests pinning the release checklist wording

**Known deferred items at close:** 3 old quick-task placeholders already tracked in `.planning/STATE.md`.

---

## v1.8 Workload Observability and Replay Feasibility (Shipped: 2026-05-05)

**Phases completed:** 6 phases, 21 plans, 61 tasks

**Key accomplishments:**

- Append-only workload trace schema decision with explicit privacy and replay boundaries
- First-class sync/async RAG request trace capture across supported backends
- Privacy-preserving workload trace JSONL import/export
- Workload, serving latency, and session analytics over captured/imported traces
- Replay design record defining callable replay as feasible and built-in endpoint replay as deferred
- Dependency-free sync callable replay helper with typed request/result payloads and Corpulse facade
- Async callable replay parity with shared semantics and public method docstring coverage
- Replay documentation and planning updates proving dependency-free callable replay across captured/imported traces

**Known deferred items at close:** 3 old quick-task placeholders already tracked in `.planning/STATE.md`.

---
