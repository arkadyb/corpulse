# Phase 30 Validation - Workload and Serving Reports

## Requirements Coverage

| Requirement | Validation |
| --- | --- |
| WORK-01 | Workload tests verify request count, observed capture span, requests per hour, and peak requests per minute. |
| WORK-02 | Workload tests verify input/output token distributions and configurable long-context threshold behavior. |
| WORK-03 | Workload tests verify component aggregation by canonical component type, request share, token share, and `other` fallback. |
| SERV-01 | Serving tests verify TTFT, TPOT, total latency, and stage latency percentile summaries. |
| SERV-02 | Serving tests verify timeout rate, error rate, and deterministic slow contributor summaries. |

## Required Test Commands

Run these after implementation:

```bash
pytest tests/test_workload_reports.py tests/test_trace_jsonl.py tests/test_trace_capture.py tests/test_backend_contract.py tests/test_docstrings.py -q
```

## Manual Verification

Create a small imported or captured trace set and verify:

```python
from corpulse import Corpulse

c = Corpulse("sqlite:///tmp/corpulse.db")
print(c.workload_report(window_days=7))
print(c.serving_report(window_days=7))
```

The reports should return deterministic dictionaries, not printed prose, model judgment, or externally generated analysis.

## Gate Conditions

- All five phase requirements are covered by at least one automated test.
- Empty trace windows return stable zero-count payloads.
- Sync and async public APIs return equivalent payload shapes.
- Existing trace JSONL import/export tests still pass.
- Public methods have Args docstrings.

## Non-Goals to Guard

- No session-level reporting fields.
- No replay execution.
- No quality scoring.
- No LLM-as-judge dependency.
