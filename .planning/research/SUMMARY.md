# Research Summary: corpulse v1.8 Workload Observability

**Created:** 2026-05-02
**Primary source:** `.planning/research/RAGPULSE-COMPARISON-FEATURES.md`

## Summary

The RAGPulse comparison shows that corpulse should not try to compete as a standalone workload dataset. The useful product move is to keep corpulse's corpus-health advantage and add an optional workload observability layer: first-class request traces, prompt component structure, serving latency metrics, session analytics, JSONL export/import, and replay-oriented schema design.

## Stack Additions

- No mandatory new runtime dependency is justified for the foundation.
- Storage work should extend the existing backend contracts for SQLite, Postgres, async Postgres, and in-memory test coverage.
- JSONL import/export can use Python standard-library serialization.
- Replay should remain behind a feasibility gate and should support user-provided callables before adding any endpoint-specific client dependency.

## Table Stakes

- Durable workload trace schema with `session_id`, timestamp, query/request identity, token counts, output token counts, optional timings, timeout/error state, and prompt component references.
- Component taxonomy that distinguishes system prompt, vector DB context, chat history, web search, user input, file attachment, tool result, and other context sources.
- Privacy-preserving trace operation through hashes and references rather than mandatory raw prompt/context retention.
- Reports for traffic volume, burstiness, token pressure, prompt composition, latency summaries, errors, and sessions.
- JSONL import/export with stable schema documentation.

## Differentiators

- Combine corpus-health signals with workload/serving behavior in one library.
- Make replay possible from operational traces without making replay the first implementation dependency.
- Preserve corpulse's low-instrumentation, library-first positioning while exposing richer observability for production RAG systems.

## Watch Outs

- Avoid turning the milestone into a full serving benchmark framework before the trace schema is stable.
- Keep existing retrieval, engagement, generation trace, report, cleanup, and wrapper APIs compatible.
- Do not require raw prompt or answer retention for useful analytics.
- Keep latency capture optional because many users will not have every stage timing.
- Treat replay as gated: implement only a minimal proof if schema and export semantics are solid.

## Recommended Build Order

1. Feasibility and schema decision record.
2. Storage-backed trace capture and prompt component models.
3. JSONL import/export.
4. Workload, latency, and session reports.
5. Replay design or minimal proof.
