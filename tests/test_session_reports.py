from __future__ import annotations

import asyncio

from corpulse import AsyncCorpulse, Corpulse
from corpulse.backends import InMemoryBackend
from corpulse.core import _build_session_report, _hash_query
from tests.test_trace_capture import FakeAsyncTraceBackend


def make_trace(
    trace_id: int,
    *,
    captured_at: float,
    session_id: str | None = None,
    input_token_count: int | None = None,
    output_token_count: int | None = None,
    components: list[dict] | None = None,
    timings: dict | None = None,
    request_id: str | None = None,
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
        "timeout": False,
        "error": None,
        "captured_at": captured_at,
    }


def test_empty_session_report_is_zeroed():
    report = _build_session_report([])

    assert report == {
        "summary": {
            "request_count": 0,
            "session_count": 0,
            "unsessioned_request_count": 0,
            "single_turn_session_count": 0,
            "multi_turn_session_count": 0,
            "avg_turns_per_session": 0.0,
            "max_turns_per_session": 0,
            "follow_up_rate": 0.0,
            "avg_session_duration_seconds": 0.0,
            "max_session_duration_seconds": 0.0,
        },
        "sessions": [],
        "context_reuse": [],
    }


def test_session_report_summarizes_turns_duration_and_growth():
    traces = [
        make_trace(
            2,
            session_id="session-a",
            captured_at=130.0,
            input_token_count=200,
            components=[{"type": "chat_history", "token_count": 3}, {"type": "chat_history", "token_count": 2}],
        ),
        make_trace(
            1,
            session_id="session-a",
            captured_at=100.0,
            input_token_count=100,
            components=[{"type": "chat_history", "token_count": 4}],
        ),
        make_trace(
            4,
            session_id="session-b",
            captured_at=105.0,
            input_token_count=50,
            components=[],
        ),
        make_trace(
            3,
            session_id="session-a",
            captured_at=160.0,
            input_token_count=300,
            components=[{"type": "chat_history", "token_count": 10}],
        ),
    ]

    report = _build_session_report(traces)

    assert report["summary"] == {
        "request_count": 4,
        "session_count": 2,
        "unsessioned_request_count": 0,
        "single_turn_session_count": 1,
        "multi_turn_session_count": 1,
        "avg_turns_per_session": 2.0,
        "max_turns_per_session": 3,
        "follow_up_rate": 0.5,
        "avg_session_duration_seconds": 30.0,
        "max_session_duration_seconds": 60.0,
    }
    assert report["sessions"][0] == {
        "session_id": "session-a",
        "request_count": 3,
        "first_captured_at": 100.0,
        "last_captured_at": 160.0,
        "duration_seconds": 60.0,
        "input_tokens_first": 100,
        "input_tokens_last": 300,
        "input_token_growth": 200,
        "chat_history_tokens_first": 4,
        "chat_history_tokens_last": 10,
        "chat_history_token_growth": 6,
    }
    assert report["sessions"][1]["session_id"] == "session-b"
    assert report["sessions"][1]["duration_seconds"] == 0.0


def test_session_report_counts_missing_session_ids_as_unsessioned():
    traces = [
        make_trace(1, session_id=None, captured_at=100.0),
        make_trace(2, session_id="", captured_at=101.0),
        make_trace(3, session_id="   ", captured_at=102.0),
        make_trace(4, session_id="session-a", captured_at=103.0),
    ]

    report = _build_session_report(traces)

    assert report["summary"]["request_count"] == 4
    assert report["summary"]["session_count"] == 1
    assert report["summary"]["unsessioned_request_count"] == 3
    assert [session["session_id"] for session in report["sessions"]] == ["session-a"]


def test_session_report_detects_repeated_context_refs_within_session():
    repeated_ref = {"doc_id": "doc-1", "chunk_id": "c1"}
    excluded_ref = {"doc_id": "ignored"}
    traces = [
        make_trace(
            1,
            session_id="session-a",
            captured_at=10.0,
            components=[
                {"type": "vector_db", "token_count": 10, "refs": [repeated_ref], "content_hash": None},
                {"type": "vector_db_context", "token_count": 5, "refs": [repeated_ref], "content_hash": None},
                {"type": "system_prompt", "token_count": 5, "refs": [excluded_ref], "content_hash": "system"},
            ],
        ),
        make_trace(
            2,
            session_id="session-a",
            captured_at=20.0,
            components=[
                {"type": "vector-db", "token_count": 8, "refs": [repeated_ref], "content_hash": None},
                {"type": "vector_db", "token_count": 8, "refs": [{"doc_id": "single"}], "content_hash": None},
                {"type": "user_input", "token_count": 3, "refs": [excluded_ref], "content_hash": "input"},
            ],
        ),
        make_trace(
            3,
            session_id="session-a",
            captured_at=30.0,
            components=[
                {"type": "chat_history", "token_count": 4, "refs": [excluded_ref], "content_hash": "history"},
            ],
        ),
    ]

    report = _build_session_report(traces)

    assert report["context_reuse"] == [
        {
            "session_id": "session-a",
            "component_type": "vector_db",
            "reuse_key": '{"chunk_id":"c1","doc_id":"doc-1"}',
            "first_seen_at": 10.0,
            "request_count": 2,
            "reuse_count": 1,
            "request_share": 0.6667,
        }
    ]


def test_session_report_uses_content_hash_reuse_fallback():
    traces = [
        make_trace(
            1,
            session_id="session-a",
            captured_at=10.0,
            components=[{"type": "tool_result", "token_count": 5, "refs": [], "content_hash": "hash-a"}],
        ),
        make_trace(
            2,
            session_id="session-a",
            captured_at=20.0,
            components=[{"type": "tool_results", "token_count": 7, "refs": None, "content_hash": "hash-a"}],
        ),
        make_trace(
            3,
            session_id="session-a",
            captured_at=30.0,
            components=[{"type": "tool_result", "token_count": 9, "refs": None, "content_hash": "hash-b"}],
        ),
    ]

    report = _build_session_report(traces)

    assert report["context_reuse"] == [
        {
            "session_id": "session-a",
            "component_type": "tool_result",
            "reuse_key": "hash-a",
            "first_seen_at": 10.0,
            "request_count": 2,
            "reuse_count": 1,
            "request_share": 0.6667,
        }
    ]


def test_session_report_does_not_merge_reuse_across_sessions():
    repeated_ref = {"url": "https://example.test/page"}
    traces = [
        make_trace(1, session_id="session-a", captured_at=10.0, components=[
            {"type": "web_search", "token_count": 5, "refs": [repeated_ref], "content_hash": None},
        ]),
        make_trace(2, session_id="session-a", captured_at=20.0, components=[
            {"type": "web_search", "token_count": 5, "refs": [repeated_ref], "content_hash": None},
        ]),
        make_trace(3, session_id="session-b", captured_at=30.0, components=[
            {"type": "web_search", "token_count": 5, "refs": [repeated_ref], "content_hash": None},
        ]),
        make_trace(4, session_id="session-b", captured_at=40.0, components=[
            {"type": "web_search", "token_count": 5, "refs": [repeated_ref], "content_hash": None},
        ]),
    ]

    report = _build_session_report(traces)

    assert [row["session_id"] for row in report["context_reuse"]] == ["session-a", "session-b"]
    assert {row["request_count"] for row in report["context_reuse"]} == {2}
    assert len({(row["session_id"], row["reuse_key"]) for row in report["context_reuse"]}) == 2


def test_sync_and_async_session_report_facades_match_shared_helper(monkeypatch):
    sync_backend = InMemoryBackend()
    async_backend = FakeAsyncTraceBackend()
    sync_corp = Corpulse(backend=sync_backend)
    async_corp = AsyncCorpulse(backend=async_backend)
    traces = [
        make_trace(
            1,
            request_id="req-1",
            session_id="session-a",
            query_text="q-1",
            query_hash=_hash_query("q-1"),
            captured_at=100.0,
            input_token_count=100,
            output_token_count=10,
            components=[
                {"type": "vector_db", "token_count": 30, "refs": [{"doc_id": "doc-1"}], "content_hash": None},
                {"type": "chat_history", "token_count": 5, "refs": None, "content_hash": None},
            ],
        ),
        make_trace(
            2,
            request_id="req-2",
            session_id="session-a",
            query_text="q-2",
            query_hash=_hash_query("q-2"),
            captured_at=150.0,
            input_token_count=180,
            output_token_count=20,
            components=[
                {"type": "vector_db", "token_count": 30, "refs": [{"doc_id": "doc-1"}], "content_hash": None},
                {"type": "chat_history", "token_count": 12, "refs": None, "content_hash": None},
            ],
        ),
    ]
    expected = _build_session_report(traces)

    sync_times = iter([100.0, 150.0])
    async_times = iter([100.0, 150.0])
    monkeypatch.setattr("corpulse.core._now", lambda: next(sync_times))
    monkeypatch.setattr("corpulse.async_core._now", lambda: next(async_times))
    monkeypatch.setattr("corpulse.core._days_ago", lambda days: 0.0)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 0.0)

    for trace in traces:
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
        for trace in traces:
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

    assert sync_corp.session_report(window_days=30) == expected

    async def read_async_report():
        return await async_corp.session_report(window_days=30)

    assert asyncio.run(read_async_report()) == expected
