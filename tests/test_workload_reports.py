from __future__ import annotations

import asyncio

import pytest

from corpulse import AsyncCorpulse, Corpulse
from corpulse.backends import InMemoryBackend
from corpulse.core import _build_serving_report, _build_workload_report, _hash_query
from tests.test_trace_capture import FakeAsyncTraceBackend


def make_trace(
    trace_id: int,
    *,
    captured_at: float,
    input_token_count: int | None = None,
    output_token_count: int | None = None,
    components: list[dict] | None = None,
    timings: dict | None = None,
    timeout: bool = False,
    error: str | None = None,
    request_id: str | None = None,
    session_id: str | None = None,
    query_text: str | None = None,
    query_hash: str | None = None,
):
    return {
        "trace_id": trace_id,
        "request_id": request_id,
        "session_id": session_id,
        "query_text": query_text,
        "query_hash": query_hash,
        "input_token_count": input_token_count,
        "output_token_count": output_token_count,
        "components": components or [],
        "timings": timings or {},
        "timeout": timeout,
        "error": error,
        "captured_at": captured_at,
    }


def test_empty_workload_and_serving_reports_are_zeroed():
    workload = _build_workload_report([], window_days=14)
    serving = _build_serving_report([])

    assert workload["traffic"] == {
        "request_count": 0,
        "window_days": 14,
        "first_captured_at": None,
        "last_captured_at": None,
        "requests_per_hour": 0.0,
        "peak_requests_per_minute": 0,
    }
    assert workload["tokens"] == {
        "input_tokens": {"count": 0, "total": 0, "avg": 0.0, "p50": None, "p95": None, "max": None},
        "output_tokens": {"count": 0, "total": 0, "avg": 0.0, "p50": None, "p95": None, "max": None},
        "long_context_threshold": 8000,
        "long_context_count": 0,
        "long_context_rate": 0.0,
    }
    assert [row["component_type"] for row in workload["components"]] == [
        "system_prompt",
        "vector_db",
        "chat_history",
        "web_search",
        "user_input",
        "file_attachment",
        "tool_result",
        "other",
    ]
    for row in workload["components"]:
        assert row["request_count"] == 0
        assert row["token_count"] == 0
        assert row["request_share"] == 0.0
        assert row["token_share"] == 0.0

    assert serving["request_count"] == 0
    assert serving["timeout_count"] == 0
    assert serving["timeout_rate"] == 0.0
    assert serving["error_count"] == 0
    assert serving["error_rate"] == 0.0
    assert serving["ttft_ms"] == {"count": 0, "avg_ms": 0.0, "p50_ms": None, "p95_ms": None, "max_ms": None}
    assert serving["tpot_ms"] == {"count": 0, "avg_ms": 0.0, "p50_ms": None, "p95_ms": None, "max_ms": None}
    assert serving["total_latency_ms"] == {"count": 0, "avg_ms": 0.0, "p50_ms": None, "p95_ms": None, "max_ms": None}
    for row in serving["stage_latencies"].values():
        assert row == {"count": 0, "avg_ms": 0.0, "p50_ms": None, "p95_ms": None, "max_ms": None}
    assert serving["slow_request_contributors"] == []


def test_workload_report_helper_summarizes_traffic_tokens_and_components():
    traces = [
        make_trace(
            1,
            captured_at=1000.0,
            input_token_count=120,
            output_token_count=10,
            components=[
                {"type": "system_prompt", "token_count": 10},
                {"type": "vector_db", "token_count": 40},
                {"type": "mystery", "token_count": 5},
            ],
        ),
        make_trace(
            2,
            captured_at=1010.0,
            input_token_count=900,
            output_token_count=20,
            components=[
                {"type": "vector_db_context", "token_count": 60},
                {"type": "chat_history", "token_count": 15},
            ],
        ),
        make_trace(
            3,
            captured_at=8200.0,
            output_token_count=30,
            components=[
                {"type": "tool_result", "token_count": 12},
                {"type": "file_attachment", "token_count": 8},
                {"type": "web_search", "token_count": 4},
                {"type": None, "token_count": None},
            ],
        ),
    ]

    report = _build_workload_report(traces, window_days=7, long_context_threshold=800)

    assert report["traffic"] == {
        "request_count": 3,
        "window_days": 7,
        "first_captured_at": 1000.0,
        "last_captured_at": 8200.0,
        "requests_per_hour": 1.5,
        "peak_requests_per_minute": 2,
    }
    assert report["tokens"]["input_tokens"] == {
        "count": 2,
        "total": 1020,
        "avg": 510.0,
        "p50": 120.0,
        "p95": 900.0,
        "max": 900.0,
    }
    assert report["tokens"]["output_tokens"] == {
        "count": 3,
        "total": 60,
        "avg": 20.0,
        "p50": 20.0,
        "p95": 30.0,
        "max": 30.0,
    }
    assert report["tokens"]["long_context_threshold"] == 800
    assert report["tokens"]["long_context_count"] == 1
    assert report["tokens"]["long_context_rate"] == 0.33

    rows = {row["component_type"]: row for row in report["components"]}
    assert rows["system_prompt"] == {
        "component_type": "system_prompt",
        "request_count": 1,
        "token_count": 10,
        "request_share": pytest.approx(1 / 3, rel=0, abs=0.0001),
        "token_share": pytest.approx(10 / 154, rel=0, abs=0.0001),
    }
    assert rows["vector_db"] == {
        "component_type": "vector_db",
        "request_count": 2,
        "token_count": 100,
        "request_share": pytest.approx(2 / 3, rel=0, abs=0.0001),
        "token_share": pytest.approx(100 / 154, rel=0, abs=0.0001),
    }
    assert rows["chat_history"]["request_count"] == 1
    assert rows["chat_history"]["token_count"] == 15
    assert rows["other"]["request_count"] == 2
    assert rows["other"]["token_count"] == 5
    assert rows["user_input"]["request_count"] == 0
    assert rows["user_input"]["token_count"] == 0


def test_serving_report_helper_summarizes_latency_and_slow_contributors():
    traces = [
        make_trace(
            1,
            captured_at=1000.0,
            timings={
                "ttft_ms": 100.0,
                "tpot_ms": 10.0,
                "retrieval_ms": 30.0,
                "rerank_ms": 5.0,
                "generation_ms": 60.0,
                "queue_ms": 70.0,
                "total_latency_ms": 200.0,
            },
            timeout=False,
            error=None,
        ),
        make_trace(
            2,
            captured_at=1100.0,
            timings={
                "ttft_ms": 200.0,
                "tpot_ms": 12.0,
                "retrieval_ms": 120.0,
                "rerank_ms": 7.0,
                "generation_ms": 100.0,
                "queue_ms": 20.0,
                "total_latency_ms": 400.0,
            },
            timeout=True,
            error="timeout",
        ),
        make_trace(
            3,
            captured_at=1200.0,
            timings={
                "ttft_ms": 150.0,
                "tpot_ms": 15.0,
                "retrieval_ms": 50.0,
                "rerank_ms": 110.0,
                "generation_ms": 90.0,
                "total_latency_ms": 320.0,
            },
            timeout=False,
            error="boom",
        ),
        make_trace(
            4,
            captured_at=1300.0,
            timings={},
            timeout=False,
            error=None,
        ),
    ]

    report = _build_serving_report(traces)

    assert report["request_count"] == 4
    assert report["timeout_count"] == 1
    assert report["timeout_rate"] == 0.25
    assert report["error_count"] == 2
    assert report["error_rate"] == 0.5
    assert report["ttft_ms"] == {
        "count": 3,
        "avg_ms": 150.0,
        "p50_ms": 150.0,
        "p95_ms": 200.0,
        "max_ms": 200.0,
    }
    assert report["tpot_ms"] == {
        "count": 3,
        "avg_ms": 12.33,
        "p50_ms": 12.0,
        "p95_ms": 15.0,
        "max_ms": 15.0,
    }
    assert report["total_latency_ms"] == {
        "count": 3,
        "avg_ms": 306.67,
        "p50_ms": 320.0,
        "p95_ms": 400.0,
        "max_ms": 400.0,
    }
    assert report["stage_latencies"]["retrieval_ms"] == {
        "count": 3,
        "avg_ms": 66.67,
        "p50_ms": 50.0,
        "p95_ms": 120.0,
        "max_ms": 120.0,
    }
    assert report["stage_latencies"]["rerank_ms"] == {
        "count": 3,
        "avg_ms": 40.67,
        "p50_ms": 7.0,
        "p95_ms": 110.0,
        "max_ms": 110.0,
    }
    assert report["stage_latencies"]["generation_ms"] == {
        "count": 3,
        "avg_ms": 83.33,
        "p50_ms": 90.0,
        "p95_ms": 100.0,
        "max_ms": 100.0,
    }
    assert report["stage_latencies"]["queue_ms"] == {
        "count": 2,
        "avg_ms": 45.0,
        "p50_ms": 20.0,
        "p95_ms": 70.0,
        "max_ms": 70.0,
    }
    assert report["slow_request_contributors"] == [
        {"stage": "retrieval_ms", "count": 1, "avg_ms": 120.0},
        {"stage": "rerank_ms", "count": 1, "avg_ms": 110.0},
        {"stage": "queue_ms", "count": 1, "avg_ms": 70.0},
    ]


def test_sync_and_async_report_facades_match_shared_helpers(monkeypatch):
    sync_backend = InMemoryBackend()
    async_backend = FakeAsyncTraceBackend()
    sync_corp = Corpulse(backend=sync_backend)
    async_corp = AsyncCorpulse(backend=async_backend)

    workload_traces = [
        make_trace(
            1,
            request_id="req-1",
            session_id="session-1",
            query_text="q-1",
            query_hash=_hash_query("q-1"),
            captured_at=1000.0,
            input_token_count=120,
            output_token_count=10,
            components=[
                {"type": "system_prompt", "token_count": 10},
                {"type": "vector_db", "token_count": 40},
            ],
            timings={
                "ttft_ms": 100.0,
                "tpot_ms": 10.0,
                "retrieval_ms": 30.0,
                "rerank_ms": 5.0,
                "generation_ms": 60.0,
                "queue_ms": 70.0,
                "total_latency_ms": 200.0,
            },
            error=None,
        ),
        make_trace(
            2,
            request_id="req-2",
            session_id="session-2",
            query_text="q-2",
            query_hash=_hash_query("q-2"),
            captured_at=1010.0,
            input_token_count=900,
            output_token_count=20,
            components=[
                {"type": "vector_db_context", "token_count": 60},
                {"type": "chat_history", "token_count": 15},
            ],
            timings={
                "ttft_ms": 200.0,
                "tpot_ms": 12.0,
                "retrieval_ms": 120.0,
                "rerank_ms": 7.0,
                "generation_ms": 100.0,
                "queue_ms": 20.0,
                "total_latency_ms": 400.0,
            },
            timeout=True,
            error="timeout",
        ),
        make_trace(
            3,
            request_id="req-3",
            session_id="session-3",
            query_text="q-3",
            query_hash=_hash_query("q-3"),
            captured_at=8200.0,
            input_token_count=None,
            output_token_count=30,
            components=[
                {"type": "tool_result", "token_count": 12},
                {"type": "file_attachment", "token_count": 8},
                {"type": "web_search", "token_count": 4},
                {"type": None, "token_count": None},
            ],
            timings={
                "ttft_ms": 150.0,
                "tpot_ms": 15.0,
                "retrieval_ms": 50.0,
                "rerank_ms": 110.0,
                "generation_ms": 90.0,
                "total_latency_ms": 320.0,
            },
            error="boom",
        ),
    ]
    expected_workload = _build_workload_report(workload_traces, window_days=30)
    expected_serving = _build_serving_report(workload_traces)

    sync_times = iter([1000.0, 1010.0, 8200.0])
    async_times = iter([1000.0, 1010.0, 8200.0])
    monkeypatch.setattr("corpulse.core._now", lambda: next(sync_times))
    monkeypatch.setattr("corpulse.async_core._now", lambda: next(async_times))
    monkeypatch.setattr("corpulse.core._days_ago", lambda days: 0.0)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 0.0)

    for trace in workload_traces:
        sync_corp.log_rag_request(
            session_id=trace["session_id"],
            query=trace["query_text"],
            request_id=trace["request_id"],
            components=trace["components"],
            input_token_count=trace["input_token_count"],
            output_token_count=trace["output_token_count"],
            timings=trace["timings"],
            timeout=trace["timeout"],
            error=trace["error"],
        )

    async def load_async_traces() -> None:
        for trace in workload_traces:
            await async_corp.alog_rag_request(
                session_id=trace["session_id"],
                query=trace["query_text"],
                request_id=trace["request_id"],
                components=trace["components"],
                input_token_count=trace["input_token_count"],
                output_token_count=trace["output_token_count"],
                timings=trace["timings"],
                timeout=trace["timeout"],
                error=trace["error"],
            )

    asyncio.run(load_async_traces())

    assert sync_corp.get_rag_request_traces(window_days=30) == workload_traces
    assert sync_corp.workload_report(window_days=30) == expected_workload
    assert sync_corp.serving_report(window_days=30) == expected_serving

    async def read_async_reports():
        traces = await async_corp.get_rag_request_traces(window_days=30)
        workload_report = await async_corp.workload_report(window_days=30)
        serving_report = await async_corp.serving_report(window_days=30)
        return traces, workload_report, serving_report

    async_traces, async_workload, async_serving = asyncio.run(read_async_reports())

    assert async_traces == workload_traces
    assert async_workload == expected_workload
    assert async_serving == expected_serving
    assert async_backend.calls.count(("rag_request_traces", (0.0,))) >= 2
