# Milestones

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
