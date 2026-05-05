# Phase 31 Validation - Session Analytics and Reuse Signals

## Requirements Coverage

| Requirement | Validation |
| --- | --- |
| SESS-01 | Session tests verify request count, turns per session, duration, follow-up rate, input token growth, and chat-history growth. |
| SESS-02 | Reuse tests verify repeated vector DB refs, content hashes, request-share calculations, deterministic ordering, and no cross-session merging. |

## Required Test Commands

Run these after implementation:

```bash
pytest tests/test_session_reports.py tests/test_workload_reports.py tests/test_trace_jsonl.py tests/test_trace_capture.py tests/test_backend_contract.py tests/test_docstrings.py -q
```

## Manual Verification

```python
from corpulse import Corpulse

c = Corpulse("sqlite:///tmp/corpulse.db")
print(c.session_report(window_days=7))
```

The report should return a structured dictionary with `summary`, `sessions`, and `context_reuse`.

## Gate Conditions

- Empty trace windows return a stable zero-count payload.
- Missing and blank session IDs are counted as unsessioned and excluded from session rows.
- Single-turn sessions have duration `0.0`.
- Multi-turn sessions contribute to follow-up rate.
- Reuse rows require the same ref/hash to appear in at least two distinct requests in the same session.
- Sync and async methods return equivalent payloads for the same trace set.
- Existing workload, JSONL, trace capture, backend contract, and docstring tests still pass.

## Non-Goals to Guard

- No replay execution.
- No cache recommendation scoring.
- No semantic similarity or LLM-as-judge behavior.
- No backend schema changes.
