# Phase 28 Plan 03 Summary

## Outcome

Added the public sync and async workload trace APIs:

- `corpulse/core.py`
- `corpulse/async_core.py`
- `tests/test_trace_capture.py`

`Corpulse.log_rag_request()` and `AsyncCorpulse.alog_rag_request()` now capture request/session IDs, optional raw query text, request components, token counts, timings, timeout state, and error state. Query hashing is preserved when raw query text is present.

## Verification

Executed checks:

- `pytest tests/test_trace_capture.py -q`

All checks passed.

## Deviations from Plan

None.

