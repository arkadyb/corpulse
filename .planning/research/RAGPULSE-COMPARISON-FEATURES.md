# RAGPulse Comparison Feature Backlog

**Project:** corpulse
**Compared with:** flashserve/RAGPulse
**Compared at:** 2026-05-02
**RAGPulse commit inspected:** `3672232d45d749fdcf45dbc38cc77e5264af4a32`

## Summary

RAGPulse is not a direct competitor library to corpulse. It is a real-world RAG workload trace dataset plus replay harness for serving-system evaluation. The useful gap for corpulse is therefore not document-health analytics, where corpulse is already stronger, but workload observability and replay.

To become clearly more advanced, corpulse should keep its corpus-health core and add an optional workload/serving layer that captures request composition, latency, sessions, traffic shape, and replay/export workflows.

## Feature Gaps Found

### 1. Workload Trace Schema

RAGPulse models each request as a timestamped workload record with:

- `timestamp`
- `input_length`
- `output_length`
- `session_id`
- component references for `sys_prompt`, `passages_ids`, `history`, `web_search`, and `user_input`

corpulse currently has generation trace capture, but it does not have a first-class RAG request trace model with session identity, token accounting, component breakdown, or replayable request metadata.

**Candidate corpulse feature:** `log_rag_request()` with structured request/session fields.

### 2. Serving Latency Metrics

RAGPulse measures serving metrics such as:

- Time to first token (`TTFT`)
- Time per output token (`TPOT`)
- Average `TTFT`
- Average `TPOT`

corpulse currently tracks retrieval events, engagements, document state, and generation traces, but not serving latency or stage timings.

**Candidate corpulse feature:** serving metrics capture for `ttft_ms`, `tpot_ms`, `total_latency_ms`, `retrieval_latency_ms`, `rerank_latency_ms`, `generation_latency_ms`, `queue_latency_ms`, timeout state, and error state.

### 3. Workload Replay

RAGPulse can replay captured traces against an OpenAI-compatible endpoint with timestamp scaling.

corpulse has instrumentation wrappers and demos, but no replay runner for stored traces.

**Candidate corpulse feature:** `corpulse.workload.replay` module that can replay stored request traces against OpenAI-compatible APIs, local model servers, or user-provided callables.

### 4. Traffic Shape Analytics

RAGPulse's trace data enables analysis of:

- Throughput over time
- Burst windows
- Input token distribution
- Output token distribution
- Component proportions across requests

corpulse reports corpus-health status, but it does not yet analyze traffic volume, burstiness, token pressure, or workload composition.

**Candidate corpulse feature:** workload reports for QPS, request bursts, token histograms, input/output length CDFs, context composition, and long-context pressure.

### 5. Prompt Component Breakdown

RAGPulse separates system prompt, retrieved passages, chat history, web search, and user input.

corpulse currently treats prompt/generation traces as mostly opaque text plus retrieved context references.

**Candidate corpulse feature:** structured prompt component capture with component type, token count, source IDs, and optional content hash.

### 6. Session Analytics

RAGPulse records `session_id`, making multi-turn workload analysis possible.

corpulse currently hashes queries but does not model conversations or sessions as first-class analytics objects.

**Candidate corpulse feature:** session-level analytics for turns per session, follow-up rate, repeated retrieval overlap, history growth, session duration, and session-level token cost.

### 7. External Context Tracking

RAGPulse explicitly tracks web search context separately from vector database passages.

corpulse focuses on corpus documents and retrieved context refs, but does not distinguish local corpus retrieval from web search or other external context sources.

**Candidate corpulse feature:** context source taxonomy such as `vector_db`, `web_search`, `chat_history`, `file_attachment`, `tool_result`, and `system_prompt`.

### 8. Benchmark Export Format

RAGPulse is useful because its trace format can be replayed and shared as a benchmark.

corpulse stores operational analytics but does not expose a standard export format for benchmark comparison or synthetic replay.

**Candidate corpulse feature:** import/export support for JSONL workload traces, with a stable schema and privacy-preserving content hashing.

### 9. Cacheability And Reuse Metrics

RAGPulse motivates optimization of caching and scheduling under real correlated RAG traffic.

corpulse does not currently estimate repeated prompt prefixes, repeated context usage, repeated queries, or likely KV-cache reuse opportunities.

**Candidate corpulse feature:** cacheability report covering prompt prefix reuse, passage reuse, session locality, query repetition, and repeated component IDs.

### 10. Serving-System Evaluation Reports

RAGPulse's examples report serving behavior, especially token streaming performance.

corpulse has report and cleanup APIs, but no report that combines corpus health with serving health.

**Candidate corpulse feature:** `serving_report()` that summarizes latency, throughput, token volume, errors, and slow-request contributors alongside corpus-health signals.

## Suggested Implementation Priority

### P1: Foundation

- Add workload trace models and storage tables.
- Add `log_rag_request()` / `alog_rag_request()` APIs.
- Capture session ID, timestamps, component references, token counts, and optional timings.
- Add JSONL import/export for the trace schema.

### P2: Analytics

- Add workload summary report.
- Add session analytics.
- Add prompt component breakdown.
- Add latency summary metrics and percentiles.
- Add FastAPI endpoints for workload reports.

### P3: Replay And Benchmarking

- Add OpenAI-compatible replay runner.
- Add timestamp scaling and concurrency controls.
- Add benchmark result export.
- Add comparison helpers for before/after serving experiments.

### P4: Advanced Optimization Signals

- Add cacheability and context reuse reports.
- Add long-context pressure analysis.
- Add correlation between corpus-health issues and serving cost.
- Add recommendations such as "reduce repeated low-engagement context" or "cache high-reuse prompt prefix."

## Proposed API Sketch

```python
corp.log_rag_request(
    session_id="session-123",
    query="how do I enroll?",
    components=[
        {"type": "system_prompt", "token_count": 840, "content_hash": "sys-a"},
        {"type": "vector_db", "refs": [{"doc_id": "policy-1"}], "token_count": 1800},
        {"type": "chat_history", "token_count": 320},
        {"type": "user_input", "token_count": 18},
    ],
    output_token_count=220,
    timings={
        "retrieval_ms": 42,
        "generation_ms": 1850,
        "ttft_ms": 210,
        "tpot_ms": 18,
    },
)
```

## Product Positioning

After these additions, corpulse can be positioned as:

- Corpus health analytics: what documents help, hurt, or go stale.
- Workload observability: how RAG traffic behaves over time.
- Serving diagnostics: where latency and token cost come from.
- Replay and benchmarking: how production traces perform against different serving stacks.

This would make corpulse broader than RAGPulse while preserving its current advantage as a reusable library instead of a standalone trace dataset.
