# Milestone v1.6 - Project Summary

**Generated:** 2026-04-20
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

corpulse is a Python library for tracking and analyzing RAG corpus health. It helps RAG teams identify ghost documents, duplicates, stale embeddings, low-engagement content, and now generation-trace capture data that can be used for future answer-quality metrics.

v1.6 does not add scoring. It adds the smallest useful capture layer so downstream services can record:
- prompt or query text
- retrieved context references
- final answer text
- optional evaluation labels

This is meant to support a server that uses corpulse as a backend analytics layer. The server can now write generation traces and read them back without affecting existing retrieval/engagement analytics.

## 2. Architecture & Technical Decisions

- **Decision:** Keep generation traces in a separate append-only table.
  - **Why:** Document deletion must not rewrite evaluation history.
  - **Phase:** 24
- **Decision:** Add trace support as an additive backend contract.
  - **Why:** Existing retrieval and engagement APIs must stay unchanged.
  - **Phase:** 24
- **Decision:** Serialize list fields as JSON in SQL backends, but keep native lists in memory.
  - **Why:** Keeps sync/async parity across SQLite, Postgres, and in-memory backends.
  - **Phase:** 24
- **Decision:** Order trace reads by `captured_at` and row id.
  - **Why:** Deterministic ordering makes downstream metrics stable.
  - **Phase:** 24
- **Decision:** Keep v1.6 capture-only.
  - **Why:** Generation scoring is intentionally deferred to a later milestone.
  - **Phase:** 24

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 24 | Generation trace capture foundation | complete | Append-only trace capture APIs and backend storage with sync/async parity |

## 4. Requirements Coverage

- ✅ `v1.6-01`: Additive trace-capture API exists on `Corpulse` and `AsyncCorpulse`
- ✅ `v1.6-02`: Trace storage/retrieval works across backends with deterministic ordering
- ✅ `v1.6-03`: Existing analytics, reporting, and storage contracts stayed unchanged

Audit verdict:
- `v1.6` audit passed

## 5. Key Decisions Log

- Phase 24 introduced a new `GenerationTraceRow` contract for trace capture records.
- Both sync and async facades now expose `log_generation_trace()` and `get_generation_traces()`.
- SQL backends use a separate append-only table so trace history survives document deletion.
- The milestone remains capture-only; no generation scoring logic is present yet.

## 6. Tech Debt & Deferred Items

No active technical debt was recorded for v1.6 closeout.

Deferred to a future milestone:
- Generation scoring
- Faithfulness / hallucination evaluation
- Context precision / judgment-based retrieval metrics
- Context utilization / answer relevance scoring

## 7. Getting Started

- **Run the project:** install dependencies and use the existing test suite. The key regression coverage for v1.6 is in `tests/test_trace_capture.py`.
- **Key directories:** `corpulse/` for library code, `tests/` for regression coverage, `.planning/phases/24-generation-trace-capture-foundation/` for phase artifacts.
- **Tests:** `pytest tests/test_trace_capture.py tests/test_backend_contract.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_docstrings.py`
- **Where to look first:** `corpulse/core.py`, `corpulse/async_core.py`, and `corpulse/backends/` for the new capture APIs and storage contract.

---

## Stats

- **Timeline:** 2026-04-20 → 2026-04-20
- **Phases:** 1 / 1
- **Commits:** 1 milestone closeout commit
- **Files changed:** see milestone commit `13c042f`
- **Contributors:** 1

