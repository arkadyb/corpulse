# Phase 32 Validation - Replay Feasibility and Minimal Proof

## Requirements Coverage

| Requirement | Validation |
| --- | --- |
| REPLAY-01 | Design record tests/checks verify endpoint replay boundary, timestamp scaling, privacy implications, and benchmark export boundaries are documented. |
| REPLAY-02 | Replay tests verify imported/captured traces can be replayed through sync and async user-provided callables without model-client dependencies. |

## Required Test Commands

Executed on 2026-05-05:

```bash
pytest tests/test_replay.py tests/test_docstrings.py -q
# 14 passed

pytest tests/test_replay.py tests/test_trace_jsonl.py tests/test_trace_capture.py tests/test_backend_contract.py tests/test_docstrings.py -q
# 46 passed

rg "openai|httpx|requests|aiohttp" corpulse/replay.py
# exit 1, no matches

rg "openai|requests|aiohttp" pyproject.toml
# exit 1, no matches
```

## Gate Conditions

- `32-REPLAY-DESIGN.md` states that built-in OpenAI-compatible HTTP replay is deferred unless callers provide their own adapter and raw prompt/message reconstruction.
- Replay helpers sort traces by `(captured_at, trace_id)`.
- Replay helpers do not sleep when `time_scale is None`.
- Replay helpers compute scaled delays when `time_scale > 0`.
- Replay helpers reject `time_scale <= 0`.
- Replay helpers do not store handler return values.
- Sync and async public facades fetch traces through existing trace APIs.
- No new third-party dependency is added.

## Manual Verification

```python
from corpulse import Corpulse

corp = Corpulse()

def handler(request):
    print(request["request_id"], request["query_hash"])

report = corp.replay_rag_request_traces(handler)
print(report["summary"])
```

The callable should be invoked once per trace and the report should contain `summary` and `results`.

## Non-Goals to Guard

- No OpenAI SDK integration.
- No built-in HTTP endpoint execution.
- No streaming/SSE replay.
- No benchmark result export.
- No replay result persistence.
- No LLM-as-judge behavior.
