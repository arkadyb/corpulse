from __future__ import annotations

from corpulse import AsyncCorpulse, Corpulse
from corpulse.backends import InMemoryBackend


class FakeAsyncTraceBackend:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self.rows: list[dict] = []
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
