from __future__ import annotations

import sys

import numpy as np

from corpulse import AsyncCorpulse
from corpulse.core import _hash_query, _vec_to_bytes


class FakeAsyncBackend:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self.documents: list[dict] = []
        self.retrieval_rows: list[dict] = []
        self.closed = False

    async def upsert_document(
        self,
        doc_id: str,
        filename: str,
        embedding: bytes | None = None,
        embedded_at: float | None = None,
    ) -> None:
        self.calls.append(
            ("upsert_document", (doc_id, filename, embedding, embedded_at))
        )

    async def insert_retrieval(
        self,
        doc_id: str,
        query_hash: str,
        rank: int,
        score: float,
        retrieved_at: float,
    ) -> None:
        self.calls.append(
            ("insert_retrieval", (doc_id, query_hash, rank, score, retrieved_at))
        )

    async def insert_engagement(
        self,
        doc_id: str,
        event_type: str,
        engaged_at: float,
    ) -> None:
        self.calls.append(("insert_engagement", (doc_id, event_type, engaged_at)))

    async def update_source_timestamp(self, doc_id: str, updated_at: float) -> None:
        self.calls.append(("update_source_timestamp", (doc_id, updated_at)))

    async def all_documents(self) -> list[dict]:
        self.calls.append(("all_documents", ()))
        return self.documents

    async def retrieval_counts(self, since: float) -> list[dict]:
        self.calls.append(("retrieval_counts", (since,)))
        return self.retrieval_rows

    async def close(self) -> None:
        self.calls.append(("close", ()))
        self.closed = True


async def test_async_corpulse_log_retrieval_awaits_backend_writes(monkeypatch):
    backend = FakeAsyncBackend()
    corpulse = AsyncCorpulse(backend=backend)
    fixed_now = 1_710_000_000.5
    monkeypatch.setattr("corpulse.async_core._now", lambda: fixed_now)

    await corpulse.log_retrieval(
        [
            {
                "doc_id": "doc-1",
                "filename": "guide.md",
                "score": "0.9",
                "embedding": np.array([1.0, 2.0], dtype=np.float32),
            }
        ],
        query="status",
    )

    assert backend.calls == [
        (
            "upsert_document",
            ("doc-1", "guide.md", _vec_to_bytes([1.0, 2.0]), fixed_now),
        ),
        (
            "insert_retrieval",
            ("doc-1", _hash_query("status"), 1, 0.9, fixed_now),
        ),
    ]


async def test_async_corpulse_other_ingestion_methods_await_backend(monkeypatch):
    backend = FakeAsyncBackend()
    corpulse = AsyncCorpulse(backend=backend)
    fixed_now = 1_710_000_010.0
    monkeypatch.setattr("corpulse.async_core._now", lambda: fixed_now)

    await corpulse.log_engagement("doc-1")
    await corpulse.log_source_update("doc-1", updated_at=555.0)
    await corpulse.register_document("doc-2", "faq.md")
    await corpulse.register_document("doc-3", "guide.md", embedding=[3.0, 4.0])

    assert backend.calls == [
        ("insert_engagement", ("doc-1", "opened", fixed_now)),
        ("update_source_timestamp", ("doc-1", 555.0)),
        ("upsert_document", ("doc-2", "faq.md", None, None)),
        (
            "upsert_document",
            ("doc-3", "guide.md", _vec_to_bytes([3.0, 4.0]), fixed_now),
        ),
    ]


async def test_async_corpulse_get_ghosts_matches_sync_shape(monkeypatch):
    backend = FakeAsyncBackend()
    backend.documents = [
        {"doc_id": "stale-doc", "filename": "stale.md"},
        {"doc_id": "fresh-doc", "filename": "fresh.md"},
    ]
    backend.retrieval_rows = [{"doc_id": "fresh-doc", "cnt": 1, "avg_rank": 1.0, "avg_score": 0.9}]
    corpulse = AsyncCorpulse(backend=backend, ghost_threshold_days=30)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)

    assert await corpulse.get_ghosts() == [
        {"doc_id": "stale-doc", "filename": "stale.md"}
    ]
    assert backend.calls == [
        ("retrieval_counts", (123.0,)),
        ("all_documents", ()),
    ]


async def test_async_corpulse_async_context_manager_closes_backend():
    backend = FakeAsyncBackend()

    async with AsyncCorpulse(backend=backend) as corpulse:
        assert corpulse.db is backend

    assert backend.closed is True
    assert backend.calls == [("close", ())]


async def test_live_async_corpulse_round_trip(async_backend):
    corpulse = AsyncCorpulse(backend=async_backend, ghost_threshold_days=30)

    await corpulse.register_document("ghost-doc", "ghost.md")
    await corpulse.log_retrieval(
        [{"doc_id": "fresh-doc", "filename": "fresh.md", "score": 0.8}],
        query="status",
    )

    ghosts = await corpulse.get_ghosts()

    assert ghosts == [{"doc_id": "ghost-doc", "filename": "ghost.md"}]


async def test_importing_async_corpulse_from_package_root_is_lazy(monkeypatch):
    monkeypatch.delitem(sys.modules, "asyncpg", raising=False)

    import corpulse

    assert hasattr(corpulse, "AsyncCorpulse")
    assert corpulse.AsyncCorpulse.__name__ == "AsyncCorpulse"
    assert "asyncpg" not in sys.modules
