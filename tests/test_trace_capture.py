from __future__ import annotations

from copy import deepcopy

from corpulse import AsyncCorpulse, Corpulse
from corpulse.core import _hash_query
from corpulse.backends import InMemoryBackend


class FakeAsyncTraceBackend:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self.rows: list[dict] = []
        self.rag_rows: list[dict] = []
        self.closed = False

    async def insert_generation_trace(
        self,
        prompt_text: str,
        retrieved_context_refs: list[dict],
        final_answer_text: str,
        evaluation_labels: list[str] | None,
        captured_at: float,
    ) -> None:
        self.calls.append(
            (
                "insert_generation_trace",
                (
                    prompt_text,
                    retrieved_context_refs,
                    final_answer_text,
                    evaluation_labels,
                    captured_at,
                ),
            )
        )
        self.rows.append(
            {
                "trace_id": len(self.rows) + 1,
                "prompt_text": prompt_text,
                "retrieved_context_refs": [
                    ref.copy() if isinstance(ref, dict) else ref
                    for ref in retrieved_context_refs
                ],
                "final_answer_text": final_answer_text,
                "evaluation_labels": None if evaluation_labels is None else list(evaluation_labels),
                "captured_at": captured_at,
            }
        )

    async def generation_traces(self, since: float) -> list[dict]:
        self.calls.append(("generation_traces", (since,)))
        return [
            row.copy()
            for row in sorted(
                self.rows,
                key=lambda row: (float(row["captured_at"]), int(row["trace_id"])),
            )
            if float(row["captured_at"]) >= since
        ]

    async def insert_rag_request_trace(
        self,
        request_id: str | None,
        session_id: str | None,
        query_text: str | None,
        query_hash: str | None,
        input_token_count: int | None,
        output_token_count: int | None,
        components: list[dict],
        timings: dict,
        timeout: bool,
        error: str | None,
        captured_at: float,
    ) -> None:
        self.calls.append(
            (
                "insert_rag_request_trace",
                (
                    request_id,
                    session_id,
                    query_text,
                    query_hash,
                    input_token_count,
                    output_token_count,
                    components,
                    timings,
                    timeout,
                    error,
                    captured_at,
                ),
            )
        )
        self.rag_rows.append(
            {
                "trace_id": len(self.rag_rows) + 1,
                "request_id": request_id,
                "session_id": session_id,
                "query_text": query_text,
                "query_hash": query_hash,
                "input_token_count": input_token_count,
                "output_token_count": output_token_count,
                "components": deepcopy(components),
                "timings": deepcopy(timings),
                "timeout": timeout,
                "error": error,
                "captured_at": captured_at,
            }
        )

    async def rag_request_traces(self, since: float) -> list[dict]:
        self.calls.append(("rag_request_traces", (since,)))
        return [
            row.copy()
            for row in sorted(
                self.rag_rows,
                key=lambda row: (float(row["captured_at"]), int(row["trace_id"])),
            )
            if float(row["captured_at"]) >= since
        ]

    async def close(self) -> None:
        self.calls.append(("close", ()))
        self.closed = True


def test_generation_trace_round_trip_is_ordered_and_append_only(monkeypatch):
    backend = InMemoryBackend()
    corpulse = Corpulse(backend=backend)

    monkeypatch.setattr("corpulse.core._now", lambda: 100.0)
    monkeypatch.setattr("corpulse.core._days_ago", lambda days: 0.0)

    corpulse.log_generation_trace(
        prompt_text="prompt-1",
        retrieved_context_refs=[{"doc_id": "doc-1", "chunk_id": "c-1"}],
        final_answer_text="answer-1",
        evaluation_labels=["grounded"],
    )
    corpulse.log_generation_trace(
        prompt_text="prompt-2",
        retrieved_context_refs=[],
        final_answer_text="answer-2",
        evaluation_labels=None,
    )

    assert corpulse.get_generation_traces(window_days=30) == [
        {
            "trace_id": 1,
            "prompt_text": "prompt-1",
            "retrieved_context_refs": [{"doc_id": "doc-1", "chunk_id": "c-1"}],
            "final_answer_text": "answer-1",
            "evaluation_labels": ["grounded"],
            "captured_at": 100.0,
        },
        {
            "trace_id": 2,
            "prompt_text": "prompt-2",
            "retrieved_context_refs": [],
            "final_answer_text": "answer-2",
            "evaluation_labels": None,
            "captured_at": 100.0,
        },
    ]

    backend.upsert_document("doc-1", "doc-1.md")
    backend.delete_document("doc-1")

    assert corpulse.get_generation_traces(window_days=30) == [
        {
            "trace_id": 1,
            "prompt_text": "prompt-1",
            "retrieved_context_refs": [{"doc_id": "doc-1", "chunk_id": "c-1"}],
            "final_answer_text": "answer-1",
            "evaluation_labels": ["grounded"],
            "captured_at": 100.0,
        },
        {
            "trace_id": 2,
            "prompt_text": "prompt-2",
            "retrieved_context_refs": [],
            "final_answer_text": "answer-2",
            "evaluation_labels": None,
            "captured_at": 100.0,
        },
    ]


async def test_async_generation_trace_matches_sync_parity_and_backend_calls(monkeypatch):
    sync_backend = InMemoryBackend()
    async_backend = FakeAsyncTraceBackend()
    sync_corpulse = Corpulse(backend=sync_backend)
    async_corpulse = AsyncCorpulse(backend=async_backend)

    monkeypatch.setattr("corpulse.core._now", lambda: 200.0)
    monkeypatch.setattr("corpulse.async_core._now", lambda: 200.0)
    monkeypatch.setattr("corpulse.core._days_ago", lambda days: 0.0)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 0.0)

    payloads = [
        (
            "prompt-1",
            [{"doc_id": "doc-1", "rank": 1}],
            "answer-1",
            ["grounded"],
        ),
        (
            "prompt-2",
            [],
            "answer-2",
            None,
        ),
    ]

    for prompt_text, retrieved_context_refs, final_answer_text, evaluation_labels in payloads:
        sync_corpulse.log_generation_trace(
            prompt_text=prompt_text,
            retrieved_context_refs=retrieved_context_refs,
            final_answer_text=final_answer_text,
            evaluation_labels=evaluation_labels,
        )
        await async_corpulse.log_generation_trace(
            prompt_text=prompt_text,
            retrieved_context_refs=retrieved_context_refs,
            final_answer_text=final_answer_text,
            evaluation_labels=evaluation_labels,
        )

    expected = [
        {
            "trace_id": 1,
            "prompt_text": "prompt-1",
            "retrieved_context_refs": [{"doc_id": "doc-1", "rank": 1}],
            "final_answer_text": "answer-1",
            "evaluation_labels": ["grounded"],
            "captured_at": 200.0,
        },
        {
            "trace_id": 2,
            "prompt_text": "prompt-2",
            "retrieved_context_refs": [],
            "final_answer_text": "answer-2",
            "evaluation_labels": None,
            "captured_at": 200.0,
        },
    ]

    assert sync_corpulse.get_generation_traces(window_days=30) == expected
    assert await async_corpulse.get_generation_traces(window_days=30) == expected
    assert async_backend.calls == [
        (
            "insert_generation_trace",
            (
                "prompt-1",
                [{"doc_id": "doc-1", "rank": 1}],
                "answer-1",
                ["grounded"],
                200.0,
            ),
        ),
        (
            "insert_generation_trace",
            ("prompt-2", [], "answer-2", None, 200.0),
        ),
        ("generation_traces", (0.0,)),
    ]


def test_rag_request_trace_in_memory_round_trip_is_ordered_and_append_only(monkeypatch):
    backend = InMemoryBackend()
    corpulse = Corpulse(backend=backend)

    monkeypatch.setattr("corpulse.core._now", lambda: 200.0)
    monkeypatch.setattr("corpulse.core._days_ago", lambda days: 0.0)

    components = [
        {
            "type": "system_prompt",
            "token_count": 12,
            "refs": None,
            "content_hash": "sp-1",
            "metadata": {"source": "prompt"},
        },
        {
            "type": "vector_db",
            "token_count": 42,
            "refs": [{"doc_id": "doc-1", "chunk_id": "c-1"}],
            "content_hash": "vec-1",
            "metadata": {"top_k": 5},
        },
        {
            "type": "chat_history",
            "token_count": 18,
            "refs": [{"turn": 3}],
            "content_hash": None,
            "metadata": {"window": 4},
        },
        {
            "type": "web_search",
            "token_count": None,
            "refs": [{"url": "https://example.com"}],
            "content_hash": "ws-1",
            "metadata": None,
        },
        {
            "type": "user_input",
            "token_count": 9,
            "refs": None,
            "content_hash": "ui-1",
            "metadata": {"channel": "web"},
        },
        {
            "type": "file_attachment",
            "token_count": 3,
            "refs": [{"filename": "notes.md"}],
            "content_hash": "fa-1",
            "metadata": {"mime_type": "text/markdown"},
        },
        {
            "type": "tool_result",
            "token_count": 15,
            "refs": [{"tool": "search", "call_id": "t-1"}],
            "content_hash": "tr-1",
            "metadata": {"status": "ok"},
        },
        {
            "type": "other",
            "token_count": None,
            "refs": None,
            "content_hash": None,
            "metadata": {"kind": "fallback"},
        },
    ]
    timings = {
        "ttft_ms": 210.0,
        "tpot_ms": 18.0,
        "retrieval_ms": 42.0,
        "rerank_ms": 8.0,
        "generation_ms": 124.0,
        "queue_ms": 7.0,
        "total_latency_ms": 409.0,
    }

    corpulse.log_rag_request(
        session_id="session-123",
        query="What is the current answer?",
        request_id="req-1",
        components=components,
        input_token_count=123,
        output_token_count=45,
        timings=timings,
        timeout=False,
        error=None,
    )

    components[0]["metadata"]["source"] = "mutated"
    timings["ttft_ms"] = 999.0

    corpulse.log_rag_request(
        session_id="session-123",
        query=None,
        request_id="req-2",
        components=[
            {
                "type": "other",
                "token_count": None,
                "refs": None,
                "content_hash": "fallback",
                "metadata": {"mode": "hash-only"},
            }
        ],
        input_token_count=None,
        output_token_count=None,
        timings={},
        timeout=True,
        error="timeout",
    )

    assert corpulse.get_rag_request_traces(window_days=30) == [
        {
            "trace_id": 1,
            "request_id": "req-1",
            "session_id": "session-123",
            "query_text": "What is the current answer?",
            "query_hash": _hash_query("What is the current answer?"),
            "input_token_count": 123,
            "output_token_count": 45,
            "components": [
                {
                    "type": "system_prompt",
                    "token_count": 12,
                    "refs": None,
                    "content_hash": "sp-1",
                    "metadata": {"source": "prompt"},
                },
                {
                    "type": "vector_db",
                    "token_count": 42,
                    "refs": [{"doc_id": "doc-1", "chunk_id": "c-1"}],
                    "content_hash": "vec-1",
                    "metadata": {"top_k": 5},
                },
                {
                    "type": "chat_history",
                    "token_count": 18,
                    "refs": [{"turn": 3}],
                    "content_hash": None,
                    "metadata": {"window": 4},
                },
                {
                    "type": "web_search",
                    "token_count": None,
                    "refs": [{"url": "https://example.com"}],
                    "content_hash": "ws-1",
                    "metadata": None,
                },
                {
                    "type": "user_input",
                    "token_count": 9,
                    "refs": None,
                    "content_hash": "ui-1",
                    "metadata": {"channel": "web"},
                },
                {
                    "type": "file_attachment",
                    "token_count": 3,
                    "refs": [{"filename": "notes.md"}],
                    "content_hash": "fa-1",
                    "metadata": {"mime_type": "text/markdown"},
                },
                {
                    "type": "tool_result",
                    "token_count": 15,
                    "refs": [{"tool": "search", "call_id": "t-1"}],
                    "content_hash": "tr-1",
                    "metadata": {"status": "ok"},
                },
                {
                    "type": "other",
                    "token_count": None,
                    "refs": None,
                    "content_hash": None,
                    "metadata": {"kind": "fallback"},
                },
            ],
            "timings": {
                "ttft_ms": 210.0,
                "tpot_ms": 18.0,
                "retrieval_ms": 42.0,
                "rerank_ms": 8.0,
                "generation_ms": 124.0,
                "queue_ms": 7.0,
                "total_latency_ms": 409.0,
            },
            "timeout": False,
            "error": None,
            "captured_at": 200.0,
        },
        {
            "trace_id": 2,
            "request_id": "req-2",
            "session_id": "session-123",
            "query_text": None,
            "query_hash": None,
            "input_token_count": None,
            "output_token_count": None,
            "components": [
                {
                    "type": "other",
                    "token_count": None,
                    "refs": None,
                    "content_hash": "fallback",
                    "metadata": {"mode": "hash-only"},
                }
            ],
            "timings": {},
            "timeout": True,
            "error": "timeout",
            "captured_at": 200.0,
        },
    ]


async def test_async_rag_request_trace_matches_sync_parity_and_backend_calls(monkeypatch):
    sync_backend = InMemoryBackend()
    async_backend = FakeAsyncTraceBackend()
    sync_corpulse = Corpulse(backend=sync_backend)
    async_corpulse = AsyncCorpulse(backend=async_backend)

    monkeypatch.setattr("corpulse.core._now", lambda: 300.0)
    monkeypatch.setattr("corpulse.async_core._now", lambda: 300.0)
    monkeypatch.setattr("corpulse.core._days_ago", lambda days: 0.0)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 0.0)

    payloads = [
        {
            "session_id": "session-123",
            "query": "How should we answer this?",
            "request_id": "req-1",
            "components": [
                {
                    "type": "system_prompt",
                    "token_count": 8,
                    "refs": None,
                    "content_hash": "sp-1",
                    "metadata": None,
                },
                {
                    "type": "vector_db",
                    "token_count": 27,
                    "refs": [{"doc_id": "doc-1"}],
                    "content_hash": "vec-1",
                    "metadata": {"source": "retrieval"},
                },
                {
                    "type": "user_input",
                    "token_count": 5,
                    "refs": None,
                    "content_hash": "ui-1",
                    "metadata": None,
                },
            ],
            "input_token_count": 40,
            "output_token_count": 11,
            "timings": {
                "ttft_ms": 100.0,
                "tpot_ms": 12.0,
                "retrieval_ms": 25.0,
                "total_latency_ms": 180.0,
            },
            "timeout": False,
            "error": None,
        },
        {
            "session_id": "session-123",
            "query": None,
            "request_id": "req-2",
            "components": [
                {
                    "type": "other",
                    "token_count": None,
                    "refs": None,
                    "content_hash": "fallback",
                    "metadata": {"mode": "hash-only"},
                }
            ],
            "input_token_count": None,
            "output_token_count": None,
            "timings": {},
            "timeout": True,
            "error": "timeout",
        },
    ]

    for payload in payloads:
        sync_corpulse.log_rag_request(**payload)
        await async_corpulse.alog_rag_request(**payload)

    expected = [
        {
            "trace_id": 1,
            "request_id": "req-1",
            "session_id": "session-123",
            "query_text": "How should we answer this?",
            "query_hash": _hash_query("How should we answer this?"),
            "input_token_count": 40,
            "output_token_count": 11,
            "components": [
                {
                    "type": "system_prompt",
                    "token_count": 8,
                    "refs": None,
                    "content_hash": "sp-1",
                    "metadata": None,
                },
                {
                    "type": "vector_db",
                    "token_count": 27,
                    "refs": [{"doc_id": "doc-1"}],
                    "content_hash": "vec-1",
                    "metadata": {"source": "retrieval"},
                },
                {
                    "type": "user_input",
                    "token_count": 5,
                    "refs": None,
                    "content_hash": "ui-1",
                    "metadata": None,
                },
            ],
            "timings": {
                "ttft_ms": 100.0,
                "tpot_ms": 12.0,
                "retrieval_ms": 25.0,
                "total_latency_ms": 180.0,
            },
            "timeout": False,
            "error": None,
            "captured_at": 300.0,
        },
        {
            "trace_id": 2,
            "request_id": "req-2",
            "session_id": "session-123",
            "query_text": None,
            "query_hash": None,
            "input_token_count": None,
            "output_token_count": None,
            "components": [
                {
                    "type": "other",
                    "token_count": None,
                    "refs": None,
                    "content_hash": "fallback",
                    "metadata": {"mode": "hash-only"},
                }
            ],
            "timings": {},
            "timeout": True,
            "error": "timeout",
            "captured_at": 300.0,
        },
    ]

    assert sync_corpulse.get_rag_request_traces(window_days=30) == expected
    assert await async_corpulse.get_rag_request_traces(window_days=30) == expected
    assert async_backend.calls == [
        (
            "insert_rag_request_trace",
            (
                "req-1",
                "session-123",
                "How should we answer this?",
                _hash_query("How should we answer this?"),
                40,
                11,
                [
                    {
                        "type": "system_prompt",
                        "token_count": 8,
                        "refs": None,
                        "content_hash": "sp-1",
                        "metadata": None,
                    },
                    {
                        "type": "vector_db",
                        "token_count": 27,
                        "refs": [{"doc_id": "doc-1"}],
                        "content_hash": "vec-1",
                        "metadata": {"source": "retrieval"},
                    },
                    {
                        "type": "user_input",
                        "token_count": 5,
                        "refs": None,
                        "content_hash": "ui-1",
                        "metadata": None,
                    },
                ],
                {
                    "ttft_ms": 100.0,
                    "tpot_ms": 12.0,
                    "retrieval_ms": 25.0,
                    "total_latency_ms": 180.0,
                },
                False,
                None,
                300.0,
            ),
        ),
        (
            "insert_rag_request_trace",
            (
                "req-2",
                "session-123",
                None,
                None,
                None,
                None,
                [
                    {
                        "type": "other",
                        "token_count": None,
                        "refs": None,
                        "content_hash": "fallback",
                        "metadata": {"mode": "hash-only"},
                    }
                ],
                {},
                True,
                "timeout",
                300.0,
            ),
        ),
        ("rag_request_traces", (0.0,)),
    ]
