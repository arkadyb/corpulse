from __future__ import annotations

import sys

import numpy as np

from corpulse import AsyncCorpulse, Corpulse
from corpulse.core import _hash_query, _vec_to_bytes


class FakeAsyncBackend:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self.documents: list[dict] = []
        self.retrieval_rows: list[dict] = []
        self.engagement_rows: list[dict] = []
        self.embedding_rows: list[dict] = []
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

    async def engagement_counts(self, since: float) -> list[dict]:
        self.calls.append(("engagement_counts", (since,)))
        return self.engagement_rows

    async def all_embeddings(self) -> list[dict]:
        self.calls.append(("all_embeddings", ()))
        return self.embedding_rows

    async def close(self) -> None:
        self.calls.append(("close", ()))
        self.closed = True


class FakeSyncBackend:
    def __init__(
        self,
        documents: list[dict],
        retrieval_rows: list[dict],
        engagement_rows: list[dict],
        embedding_rows: list[dict],
    ):
        self.documents = documents
        self.retrieval_rows = retrieval_rows
        self.engagement_rows = engagement_rows
        self.embedding_rows = embedding_rows

    def all_documents(self) -> list[dict]:
        return self.documents

    def retrieval_counts(self, since: float) -> list[dict]:
        return self.retrieval_rows

    def engagement_counts(self, since: float) -> list[dict]:
        return self.engagement_rows

    def all_embeddings(self) -> list[dict]:
        return self.embedding_rows


def _analysis_fixture_rows() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    day = 86_400
    documents = [
        {
            "doc_id": "old",
            "filename": "api-v1.md",
            "source_updated_at": 10 * day,
            "embedded_at": 10 * day,
        },
        {
            "doc_id": "new",
            "filename": "api-v2.md",
            "source_updated_at": 12 * day,
            "embedded_at": 12 * day,
        },
        {
            "doc_id": "stale",
            "filename": "stale.md",
            "source_updated_at": 30 * day,
            "embedded_at": 5 * day,
        },
        {
            "doc_id": "dup-a",
            "filename": "dup-a.md",
            "source_updated_at": 20 * day,
            "embedded_at": 20 * day,
        },
        {
            "doc_id": "dup-b",
            "filename": "dup-b.md",
            "source_updated_at": 20 * day,
            "embedded_at": 20 * day,
        },
        {
            "doc_id": "suspect",
            "filename": "suspect.md",
            "source_updated_at": 15 * day,
            "embedded_at": 15 * day,
        },
        {
            "doc_id": "healthy",
            "filename": "healthy.md",
            "source_updated_at": 18 * day,
            "embedded_at": 18 * day,
        },
    ]
    retrieval_rows = [
        {"doc_id": "new", "cnt": 3, "avg_rank": 1.0, "avg_score": 0.93},
        {"doc_id": "dup-a", "cnt": 2, "avg_rank": 1.5, "avg_score": 0.87},
        {"doc_id": "dup-b", "cnt": 2, "avg_rank": 1.5, "avg_score": 0.86},
        {"doc_id": "suspect", "cnt": 6, "avg_rank": 2.0, "avg_score": 0.8},
        {"doc_id": "healthy", "cnt": 10, "avg_rank": 1.1, "avg_score": 0.95},
    ]
    engagement_rows = [
        {"doc_id": "healthy", "cnt": 4},
        {"doc_id": "suspect", "cnt": 0},
    ]
    embedding_rows = [
        {"doc_id": "dup-a", "filename": "dup-a.md", "embedding_vec": _vec_to_bytes([1.0, 0.0])},
        {"doc_id": "dup-b", "filename": "dup-b.md", "embedding_vec": _vec_to_bytes([0.999, 0.001])},
        {"doc_id": "healthy", "filename": "healthy.md", "embedding_vec": _vec_to_bytes([0.0, 1.0])},
    ]
    return documents, retrieval_rows, engagement_rows, embedding_rows


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


async def test_async_analysis_methods_match_sync_parity(monkeypatch):
    documents, retrieval_rows, engagement_rows, embedding_rows = _analysis_fixture_rows()
    async_backend = FakeAsyncBackend()
    async_backend.documents = documents
    async_backend.retrieval_rows = retrieval_rows
    async_backend.engagement_rows = engagement_rows
    async_backend.embedding_rows = embedding_rows
    sync_backend = FakeSyncBackend(
        documents=documents,
        retrieval_rows=retrieval_rows,
        engagement_rows=engagement_rows,
        embedding_rows=embedding_rows,
    )

    async_corpulse = AsyncCorpulse(
        backend=async_backend,
        ghost_threshold_days=30,
        stale_threshold_days=14,
    )
    sync_corpulse = Corpulse(
        backend=sync_backend,
        ghost_threshold_days=30,
        stale_threshold_days=14,
    )
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)
    monkeypatch.setattr("corpulse.core._days_ago", lambda days: 123.0)

    assert await async_corpulse.get_obsolete() == sync_corpulse.get_obsolete() == [
        {"doc_id": "old", "filename": "api-v1.md", "superseded_by": "api-v2.md"}
    ]
    assert await async_corpulse.get_stale_embeddings() == sync_corpulse.get_stale_embeddings() == [
        {
            "doc_id": "stale",
            "filename": "stale.md",
            "source_updated": "1970-01-31",
            "last_embedded": "1970-01-06",
            "days_behind": 25,
        }
    ]
    assert await async_corpulse.get_suspects() == sync_corpulse.get_suspects() == [
        {
            "doc_id": "suspect",
            "filename": "suspect.md",
            "retrievals": 6,
            "engagement_rate": 0.0,
        }
    ]
    assert await async_corpulse.get_duplicates() == sync_corpulse.get_duplicates() == [
        {
            "doc_id_a": "dup-a",
            "filename_a": "dup-a.md",
            "doc_id_b": "dup-b",
            "filename_b": "dup-b.md",
            "similarity": 1.0,
        }
    ]
    assert await async_corpulse.corpus_health() == sync_corpulse.corpus_health() == {
        "total_docs": 7,
        "ghosts": 2,
        "obsolete": 1,
        "stale": 1,
        "duplicates": 2,
        "noise_estimate": 0.57,
        "bloat_warning": True,
        "recommendation": "Consider pruning ~3 low-signal documents.",
    }


async def test_async_analysis_methods_await_expected_backend_reads(monkeypatch):
    documents, retrieval_rows, engagement_rows, embedding_rows = _analysis_fixture_rows()
    backend = FakeAsyncBackend()
    backend.documents = documents
    backend.retrieval_rows = retrieval_rows
    backend.engagement_rows = engagement_rows
    backend.embedding_rows = embedding_rows
    corpulse = AsyncCorpulse(backend=backend)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 456.0)

    await corpulse.get_obsolete()
    await corpulse.get_stale_embeddings()
    await corpulse.get_suspects()
    await corpulse.get_duplicates()
    await corpulse.corpus_health()

    assert backend.calls == [
        ("all_documents", ()),
        ("all_documents", ()),
        ("all_documents", ()),
        ("retrieval_counts", (456.0,)),
        ("engagement_counts", (456.0,)),
        ("all_embeddings", ()),
        ("all_documents", ()),
        ("retrieval_counts", (456.0,)),
        ("all_documents", ()),
        ("all_documents", ()),
        ("all_documents", ()),
        ("all_embeddings", ()),
    ]


async def test_async_get_duplicates_preserves_sklearn_guard(monkeypatch):
    backend = FakeAsyncBackend()
    backend.embedding_rows = [
        {"doc_id": "a", "filename": "a.md", "embedding_vec": _vec_to_bytes([1.0, 0.0])},
        {"doc_id": "b", "filename": "b.md", "embedding_vec": _vec_to_bytes([0.0, 1.0])},
    ]
    corpulse = AsyncCorpulse(backend=backend)
    monkeypatch.setattr("corpulse.core._SKLEARN", False)

    try:
        await corpulse.get_duplicates()
    except RuntimeError as exc:
        assert "scikit-learn is required for duplicate detection" in str(exc)
    else:
        raise AssertionError("expected get_duplicates() to preserve the sklearn guard")


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
