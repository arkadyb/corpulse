from __future__ import annotations

import pytest

from corpulse import AsyncCorpulse, Corpulse
from corpulse.backends import InMemoryBackend
from corpulse.replay import (
    async_replay_rag_request_traces,
    replay_rag_request_traces,
)
from tests.test_trace_capture import FakeAsyncTraceBackend


def make_trace(
    trace_id: int,
    *,
    captured_at: float,
    request_id: str | None = None,
    session_id: str | None = None,
    query_text: str | None = None,
    query_hash: str | None = None,
    input_token_count: int | None = None,
    output_token_count: int | None = None,
    components: list[dict] | None = None,
    timings: dict | None = None,
    timeout: bool = False,
    error: str | None = None,
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


def test_replay_orders_traces_and_invokes_callable_with_envelopes():
    traces = [
        make_trace(3, captured_at=20.0, request_id="req-3"),
        make_trace(
            1,
            captured_at=10.0,
            request_id="req-1",
            session_id="session-a",
            query_text="hello",
            query_hash="query-hash",
            input_token_count=12,
            output_token_count=4,
            components=[{"type": "user_input", "token_count": 12, "refs": None, "content_hash": "abc"}],
            timings={"total_latency_ms": 42.0},
        ),
        make_trace(2, captured_at=20.0, request_id="req-2"),
    ]
    received = []

    report = replay_rag_request_traces(
        traces,
        lambda request: received.append(request),
        clock=lambda: 100.0,
    )

    assert [request["trace_id"] for request in received] == [1, 2, 3]
    assert [request["sequence_index"] for request in received] == [0, 1, 2]
    assert received[0]["query_hash"] == "query-hash"
    assert received[0]["components"] == [
        {"type": "user_input", "token_count": 12, "refs": None, "content_hash": "abc"}
    ]
    assert received[0]["timings"] == {"total_latency_ms": 42.0}
    assert received[0]["scheduled_delay_seconds"] == 0.0
    assert report["summary"] == {
        "trace_count": 3,
        "replayed_count": 3,
        "succeeded_count": 3,
        "failed_count": 0,
        "skipped_count": 0,
        "total_scheduled_delay_seconds": 0.0,
        "total_runtime_seconds": 0.0,
    }


def test_replay_default_does_not_sleep():
    traces = [
        make_trace(1, captured_at=10.0),
        make_trace(2, captured_at=999.0),
    ]

    replay_rag_request_traces(
        traces,
        lambda request: None,
        sleep=lambda delay: pytest.fail(f"unexpected sleep {delay}"),
        clock=lambda: 0.0,
    )


def test_replay_time_scale_and_max_delay_use_injected_sleep():
    traces = [
        make_trace(1, captured_at=0.0),
        make_trace(2, captured_at=10.0),
        make_trace(3, captured_at=50.0),
    ]
    delays = []

    report = replay_rag_request_traces(
        traces,
        lambda request: None,
        time_scale=10.0,
        max_delay_seconds=2.0,
        sleep=delays.append,
        clock=lambda: 0.0,
    )

    assert delays == [1.0, 2.0]
    assert [result["scheduled_delay_seconds"] for result in report["results"]] == [0.0, 1.0, 2.0]
    assert report["summary"]["total_scheduled_delay_seconds"] == 3.0


def test_replay_rejects_non_positive_time_scale():
    traces = [make_trace(1, captured_at=0.0)]

    with pytest.raises(ValueError, match="time_scale must be greater than 0"):
        replay_rag_request_traces(
            traces,
            lambda request: None,
            time_scale=0.0,
        )


def test_replay_records_handler_errors_without_storing_output():
    traces = [
        make_trace(1, captured_at=0.0, request_id="ok"),
        make_trace(2, captured_at=1.0, request_id="fail"),
    ]

    def handler(request):
        if request["request_id"] == "fail":
            raise RuntimeError("boom")
        return {"raw_response": "not retained"}

    report = replay_rag_request_traces(traces, handler, clock=lambda: 0.0)

    assert report["summary"]["succeeded_count"] == 1
    assert report["summary"]["failed_count"] == 1
    assert report["results"][1]["ok"] is False
    assert report["results"][1]["error"] == "boom"
    assert "raw_response" not in report["results"][0]
    assert "handler_result" not in report["results"][0]


def test_replay_stop_on_error_skips_remaining_traces():
    traces = [
        make_trace(1, captured_at=0.0),
        make_trace(2, captured_at=1.0),
        make_trace(3, captured_at=2.0),
    ]
    received = []

    def handler(request):
        received.append(request["trace_id"])
        raise RuntimeError("stop")

    report = replay_rag_request_traces(
        traces,
        handler,
        stop_on_error=True,
        clock=lambda: 0.0,
    )

    assert received == [1]
    assert report["summary"]["trace_count"] == 3
    assert report["summary"]["replayed_count"] == 1
    assert report["summary"]["failed_count"] == 1
    assert report["summary"]["skipped_count"] == 2


def test_sync_replay_facade_fetches_backend_traces(monkeypatch):
    backend = InMemoryBackend()
    corpulse = Corpulse(backend=backend)
    seen = []

    monkeypatch.setattr("corpulse.core._now", lambda: 100.0)
    monkeypatch.setattr("corpulse.core._days_ago", lambda days: 0.0)

    corpulse.log_rag_request(request_id="req-1", query="first")
    corpulse.log_rag_request(request_id="req-2", query="second")

    report = corpulse.replay_rag_request_traces(
        lambda request: seen.append(request["request_id"]),
        window_days=30,
    )

    assert seen == ["req-1", "req-2"]
    assert report["summary"]["trace_count"] == 2
    assert report["summary"]["replayed_count"] == 2


async def test_async_replay_awaits_callable_and_matches_sync_summary():
    traces = [
        make_trace(2, captured_at=20.0),
        make_trace(1, captured_at=10.0),
    ]
    sync_seen = []
    async_seen = []

    sync_report = replay_rag_request_traces(
        traces,
        lambda request: sync_seen.append(request["trace_id"]),
        clock=lambda: 0.0,
    )

    async def handler(request):
        async_seen.append(request["trace_id"])

    async_report = await async_replay_rag_request_traces(
        traces,
        handler,
        clock=lambda: 0.0,
    )

    assert sync_seen == [1, 2]
    assert async_seen == [1, 2]
    assert async_report["summary"] == sync_report["summary"]


async def test_async_replay_time_scale_uses_injected_sleep():
    traces = [
        make_trace(1, captured_at=0.0),
        make_trace(2, captured_at=8.0),
    ]
    delays = []

    async def sleep(delay):
        delays.append(delay)

    async def handler(request):
        return None

    report = await async_replay_rag_request_traces(
        traces,
        handler,
        time_scale=4.0,
        sleep=sleep,
        clock=lambda: 0.0,
    )

    assert delays == [2.0]
    assert report["summary"]["total_scheduled_delay_seconds"] == 2.0


async def test_async_replay_facade_fetches_backend_traces(monkeypatch):
    backend = FakeAsyncTraceBackend()
    async_corpulse = AsyncCorpulse(backend=backend)
    seen = []

    monkeypatch.setattr("corpulse.async_core._now", lambda: 100.0)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 0.0)

    await async_corpulse.alog_rag_request(request_id="req-1", query="first")
    await async_corpulse.alog_rag_request(request_id="req-2", query="second")

    async def handler(request):
        seen.append(request["request_id"])

    report = await async_corpulse.areplay_rag_request_traces(
        handler,
        window_days=30,
    )

    assert seen == ["req-1", "req-2"]
    assert report["summary"]["trace_count"] == 2
    assert report["summary"]["replayed_count"] == 2
