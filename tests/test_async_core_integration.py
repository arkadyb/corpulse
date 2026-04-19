from __future__ import annotations

import builtins
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from corpulse import AsyncCorpulse, Corpulse
from corpulse.core import (
    _build_cleanup_payload,
    _build_report_rows,
    _build_report_summary,
    _hash_query,
    _vec_to_bytes,
)
from tests.report_fixtures import (
    build_report_fixture_snapshot,
    expected_cleanup_payload,
    expected_report_payload,
    helper_inputs,
    seed_async_backend,
)


class FakeAsyncBackend:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self.documents: list[dict] = []
        self.retrieval_rows: list[dict] = []
        self.query_rows: list[dict] = []
        self.query_attempt_rows: list[dict] = []
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

    async def insert_query_attempt(
        self,
        query_hash: str,
        result_count: int,
        attempted_at: float,
    ) -> None:
        self.calls.append(
            ("insert_query_attempt", (query_hash, result_count, attempted_at))
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

    async def delete_document(self, doc_id: str) -> None:
        self.calls.append(("delete_document", (doc_id,)))

    async def all_documents(self) -> list[dict]:
        self.calls.append(("all_documents", ()))
        return self.documents

    async def retrieval_counts(self, since: float) -> list[dict]:
        self.calls.append(("retrieval_counts", (since,)))
        return self.retrieval_rows

    async def query_counts(self, since: float) -> list[dict]:
        self.calls.append(("query_counts", (since,)))
        return self.query_rows

    async def query_attempt_counts(self, since: float) -> list[dict]:
        self.calls.append(("query_attempt_counts", (since,)))
        return self.query_attempt_rows

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
        query_rows: list[dict],
        query_attempt_rows: list[dict],
        engagement_rows: list[dict],
        embedding_rows: list[dict],
    ):
        self.documents = documents
        self.retrieval_rows = retrieval_rows
        self.query_rows = query_rows
        self.query_attempt_rows = query_attempt_rows
        self.engagement_rows = engagement_rows
        self.embedding_rows = embedding_rows

    def all_documents(self) -> list[dict]:
        return self.documents

    def delete_document(self, doc_id: str) -> None:
        self.documents = [
            document for document in self.documents if document["doc_id"] != doc_id
        ]
        self.retrieval_rows = [
            row for row in self.retrieval_rows if row["doc_id"] != doc_id
        ]
        self.engagement_rows = [
            row for row in self.engagement_rows if row["doc_id"] != doc_id
        ]
        self.embedding_rows = [
            row for row in self.embedding_rows if row["doc_id"] != doc_id
        ]

    def retrieval_counts(self, since: float) -> list[dict]:
        return self.retrieval_rows

    def query_counts(self, since: float) -> list[dict]:
        return self.query_rows

    def query_attempt_counts(self, since: float) -> list[dict]:
        return self.query_attempt_rows

    def engagement_counts(self, since: float) -> list[dict]:
        return self.engagement_rows

    def all_embeddings(self) -> list[dict]:
        return self.embedding_rows


def _shared_report_fixture_backends() -> tuple[FakeSyncBackend, FakeAsyncBackend]:
    snapshot = build_report_fixture_snapshot()
    async_backend = FakeAsyncBackend()
    async_backend.documents = snapshot["documents"]
    async_backend.retrieval_rows = snapshot["retrieval_rows"]
    async_backend.query_rows = snapshot.get("query_rows", [])
    async_backend.query_attempt_rows = snapshot.get("query_attempt_rows", [])
    async_backend.engagement_rows = snapshot["engagement_rows"]
    async_backend.embedding_rows = snapshot["embedding_rows"]
    sync_backend = FakeSyncBackend(
        documents=snapshot["documents"],
        retrieval_rows=snapshot["retrieval_rows"],
        query_rows=snapshot.get("query_rows", []),
        query_attempt_rows=snapshot.get("query_attempt_rows", []),
        engagement_rows=snapshot["engagement_rows"],
        embedding_rows=snapshot["embedding_rows"],
    )
    return sync_backend, async_backend


def _install_fake_pandas(monkeypatch):
    orig_import = builtins.__import__

    class FakeSeries:
        def __init__(self, values):
            self._values = values

        def head(self, n):
            return self._values[:n]

        def __iter__(self):
            return iter(self._values)

    class FakeDataFrame:
        def __init__(self, rows):
            self._rows = list(rows)
            self.columns = list(rows[0].keys()) if rows else []

        def sort_values(self, key, ascending=False):
            return FakeDataFrame(
                sorted(self._rows, key=lambda row: row[key], reverse=not ascending)
            )

        def to_dict(self, orient):
            assert orient == "records"
            return list(self._rows)

        def __getitem__(self, key):
            return FakeSeries([row[key] for row in self._rows])

    def _fake_pandas(name, *args, **kwargs):
        if name == "pandas":
            return SimpleNamespace(DataFrame=FakeDataFrame)
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_pandas)


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


def _low_confidence_query_rows() -> list[dict]:
    day = 86_400
    return [
        {
            "query_hash": "healthy-query",
            "cnt": 3,
            "avg_rank": 1.0,
            "avg_score": 0.91,
            "min_rank": 1,
            "max_rank": 2,
            "min_score": 0.88,
            "max_score": 0.95,
            "first_retrieved_at": 20 * day,
            "last_retrieved_at": 20 * day,
        },
        {
            "query_hash": "low-query",
            "cnt": 2,
            "avg_rank": 1.5,
            "avg_score": 0.51,
            "min_rank": 1,
            "max_rank": 2,
            "min_score": 0.44,
            "max_score": 0.58,
            "first_retrieved_at": 20 * day,
            "last_retrieved_at": 20 * day,
        },
    ]


def _query_attempt_rows() -> list[dict]:
    day = 86_400
    return [
        {
            "query_hash": "healthy-query",
            "cnt": 3,
            "result_cnt": 3,
            "first_attempted_at": 20 * day,
            "last_attempted_at": 20 * day,
        },
        {
            "query_hash": "mixed-query",
            "cnt": 2,
            "result_cnt": 1,
            "first_attempted_at": 20 * day,
            "last_attempted_at": 20 * day,
        },
        {
            "query_hash": "zero-query",
            "cnt": 1,
            "result_cnt": 0,
            "first_attempted_at": 20 * day,
            "last_attempted_at": 20 * day,
        },
    ]


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
            "insert_query_attempt",
            (_hash_query("status"), 1, fixed_now),
        ),
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


async def test_async_corpulse_delete_document_delegates_to_backend():
    backend = FakeAsyncBackend()
    corpulse = AsyncCorpulse(backend=backend)

    await corpulse.delete_document("doc-1")

    assert backend.calls == [("delete_document", ("doc-1",))]


async def test_async_analysis_methods_match_sync_parity(monkeypatch):
    documents, retrieval_rows, engagement_rows, embedding_rows = _analysis_fixture_rows()
    query_rows = _low_confidence_query_rows()
    query_attempt_rows = _query_attempt_rows()
    async_backend = FakeAsyncBackend()
    async_backend.documents = documents
    async_backend.retrieval_rows = retrieval_rows
    async_backend.query_rows = query_rows
    async_backend.query_attempt_rows = query_attempt_rows
    async_backend.engagement_rows = engagement_rows
    async_backend.embedding_rows = embedding_rows
    sync_backend = FakeSyncBackend(
        documents=documents,
        retrieval_rows=retrieval_rows,
        query_rows=query_rows,
        query_attempt_rows=query_attempt_rows,
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
    assert await async_corpulse.get_low_confidence_queries(threshold=0.8) == sync_corpulse.get_low_confidence_queries(threshold=0.8) == [
        {
            "query_hash": "low-query",
            "cnt": 2,
            "avg_rank": 1.5,
            "avg_score": 0.51,
            "min_rank": 1,
            "max_rank": 2,
            "min_score": 0.44,
            "max_score": 0.58,
            "first_retrieved_at": 20 * 86_400,
            "last_retrieved_at": 20 * 86_400,
        }
    ]
    assert await async_corpulse.low_confidence_rate(threshold=0.8) == sync_corpulse.low_confidence_rate(threshold=0.8) == 0.5
    assert await async_corpulse.get_zero_result_queries() == sync_corpulse.get_zero_result_queries() == [
        {
            "query_hash": "zero-query",
            "cnt": 1,
            "result_cnt": 0,
            "first_attempted_at": 20 * 86_400,
            "last_attempted_at": 20 * 86_400,
        }
    ]
    assert await async_corpulse.zero_result_rate() == sync_corpulse.zero_result_rate() == 0.33
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


async def test_async_to_dataframe_matches_sync_on_shared_report_fixture(monkeypatch):
    sync_backend, async_backend = _shared_report_fixture_backends()
    sync_corpulse = Corpulse(backend=sync_backend, ghost_threshold_days=30, stale_threshold_days=14)
    async_corpulse = AsyncCorpulse(backend=async_backend, ghost_threshold_days=30, stale_threshold_days=14)

    _install_fake_pandas(monkeypatch)
    monkeypatch.setattr("corpulse.core._days_ago", lambda days: 123.0)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)

    sync_df = sync_corpulse.to_dataframe(window_days=30)
    async_df = await async_corpulse.to_dataframe(window_days=30)

    assert list(async_df.columns) == list(sync_df.columns)
    assert async_df.to_dict("records") == sync_df.to_dict("records")


async def test_async_to_dataframe_sorts_rows_by_retrievals_descending(monkeypatch):
    _, async_backend = _shared_report_fixture_backends()
    async_corpulse = AsyncCorpulse(backend=async_backend, ghost_threshold_days=30, stale_threshold_days=14)

    _install_fake_pandas(monkeypatch)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)

    df = await async_corpulse.to_dataframe(window_days=30)

    assert list(df["retrievals"].head(4)) == [10, 8, 7, 6]


async def test_async_to_dataframe_raises_without_pandas(monkeypatch):
    _, async_backend = _shared_report_fixture_backends()
    async_corpulse = AsyncCorpulse(backend=async_backend)
    orig_import = builtins.__import__

    def _missing_pandas(name, *args, **kwargs):
        if name == "pandas":
            raise ImportError("forced missing pandas")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _missing_pandas)

    with pytest.raises(RuntimeError, match="^pip install pandas to use to_dataframe\\(\\)$"):
        await async_corpulse.to_dataframe()


async def test_async_report_returns_helper_derived_payload(monkeypatch):
    _, async_backend = _shared_report_fixture_backends()
    corpulse = AsyncCorpulse(backend=async_backend, ghost_threshold_days=30, stale_threshold_days=14)
    inputs = helper_inputs(window_days=30)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)

    expected = {
        "summary": _build_report_summary(
            inputs["all_docs"],
            inputs["window_days"],
            inputs["health"],
        ),
        "rows": _build_report_rows(
            inputs["all_docs"],
            inputs["r_map"],
            inputs["e_map"],
            inputs["ghost_ids"],
            inputs["obsolete_ids"],
            inputs["stale_ids"],
            corpulse.top_k_report,
        ),
    }

    assert await corpulse.report(window_days=30) == expected


async def test_async_report_preserves_low_engagement_threshold_parity(monkeypatch):
    _, async_backend = _shared_report_fixture_backends()
    corpulse = AsyncCorpulse(backend=async_backend, ghost_threshold_days=30, stale_threshold_days=14)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)

    payload = await corpulse.report(window_days=30)

    noisy_row = next(row for row in payload["rows"] if row["filename"] == "noisy.md")
    assert noisy_row["status"] == "low_engagement"
    assert noisy_row["status_display"] == "◌  low eng."
    assert noisy_row["engagement_rate"] == "10%"


async def test_async_cleanup_report_returns_helper_derived_payload(monkeypatch):
    _, async_backend = _shared_report_fixture_backends()
    corpulse = AsyncCorpulse(backend=async_backend, ghost_threshold_days=30, stale_threshold_days=14)
    inputs = helper_inputs(window_days=30)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)

    expected = _build_cleanup_payload(
        inputs["health"],
        inputs["ghosts"],
        inputs["obsolete"],
        inputs["stale"],
        inputs["suspects"],
        corpulse.ghost_threshold_days,
    )

    assert await corpulse.cleanup_report() == expected


async def test_async_cleanup_report_matches_counts_top5_and_metadata(monkeypatch):
    _, async_backend = _shared_report_fixture_backends()
    corpulse = AsyncCorpulse(backend=async_backend, ghost_threshold_days=30, stale_threshold_days=14)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)

    payload = await corpulse.cleanup_report()

    assert payload["total_docs"] == 10
    assert payload["noise_pct"] == 70.0
    assert payload["bloat_warning"] is True
    assert payload["recommendation"] == "Consider pruning ~7 low-signal documents."
    assert payload["ghost_threshold_days"] == 30
    assert payload["ghosts"] == {
        "count": 2,
        "top5": [
            {"doc_id": "ghost-a", "filename": "ghost_a.md"},
            {"doc_id": "ghost-b", "filename": "ghost_b.md"},
        ],
        "overflow": 0,
    }
    assert payload["obsolete"] == {
        "count": 2,
        "top5": [
            {"doc_id": "api-v1", "filename": "api-v1.md", "superseded_by": "api-v2.md"},
            {"doc_id": "guide-v1", "filename": "guide-v1.md", "superseded_by": "guide-v2.md"},
        ],
        "overflow": 0,
    }
    assert payload["stale"] == {
        "count": 1,
        "top5": [
            {
                "doc_id": "stale-doc",
                "filename": "stale.md",
                "source_updated": "2023-11-04",
                "last_embedded": "2023-09-25",
                "days_behind": 40,
            }
        ],
        "overflow": 0,
    }
    assert payload["suspects"] == {
        "count": 1,
        "top5": [
            {
                "doc_id": "noisy-doc",
                "filename": "noisy.md",
                "retrievals": 10,
                "engagement_rate": 0.1,
            }
        ],
        "overflow": 0,
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


async def _seed_live_backend(async_backend) -> None:
    """Seed a real async backend with the canonical report fixture corpus."""
    await seed_async_backend(async_backend)


async def test_live_async_corpulse_round_trip(async_backend):
    corpulse = AsyncCorpulse(backend=async_backend, ghost_threshold_days=30)

    await corpulse.register_document("ghost-doc", "ghost.md")
    await corpulse.log_retrieval(
        [{"doc_id": "fresh-doc", "filename": "fresh.md", "score": 0.8}],
        query="status",
    )

    ghosts = await corpulse.get_ghosts()

    assert ghosts == [{"doc_id": "ghost-doc", "filename": "ghost.md"}]


async def test_live_async_to_dataframe_shape_and_ordering(async_backend, monkeypatch):
    """Live: to_dataframe() returns correct shape, columns, and descending retrieval order."""
    await _seed_live_backend(async_backend)
    corpulse = AsyncCorpulse(backend=async_backend, ghost_threshold_days=30, stale_threshold_days=14)

    _install_fake_pandas(monkeypatch)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)

    df = await corpulse.to_dataframe(window_days=30)
    records = df.to_dict("records")

    assert df.columns  # non-empty
    assert "doc_id" in df.columns
    assert "retrievals" in df.columns
    assert "status" in df.columns
    assert len(records) == 10  # canonical corpus has 10 documents
    # top 4 retrieval counts in descending order match the canonical fixture
    retrieval_counts = [r["retrievals"] for r in records]
    assert retrieval_counts == sorted(retrieval_counts, reverse=True)
    assert retrieval_counts[:4] == [10, 8, 7, 6]


async def test_live_async_report_summary_and_representative_rows(async_backend, monkeypatch):
    """Live: report() returns summary matching shared helpers and contains expected rows."""
    await _seed_live_backend(async_backend)
    corpulse = AsyncCorpulse(backend=async_backend, ghost_threshold_days=30, stale_threshold_days=14)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)

    payload = await corpulse.report(window_days=30)
    expected = expected_report_payload(window_days=30, top_k=corpulse.top_k_report)

    assert payload["summary"] == expected["summary"]
    # representative row content: noisy-doc must appear as low_engagement
    noisy_row = next((r for r in payload["rows"] if r["filename"] == "noisy.md"), None)
    assert noisy_row is not None
    assert noisy_row["status"] == "low_engagement"
    assert noisy_row["retrievals"] == 10
    # section counts match the shared helper expectation
    assert len(payload["rows"]) == len(expected["rows"])


async def test_live_async_cleanup_report_metadata_and_section_counts(async_backend, monkeypatch):
    """Live: cleanup_report() returns metadata and section counts from the shared expected payload."""
    await _seed_live_backend(async_backend)
    corpulse = AsyncCorpulse(backend=async_backend, ghost_threshold_days=30, stale_threshold_days=14)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)

    payload = await corpulse.cleanup_report()
    expected = expected_cleanup_payload(window_days=30, ghost_threshold_days=30)

    assert payload["total_docs"] == expected["total_docs"]
    assert payload["ghost_threshold_days"] == expected["ghost_threshold_days"]
    assert payload["bloat_warning"] == expected["bloat_warning"]
    # section counts
    assert payload["ghosts"]["count"] == expected["ghosts"]["count"]
    assert payload["obsolete"]["count"] == expected["obsolete"]["count"]
    assert payload["stale"]["count"] == expected["stale"]["count"]
    assert payload["suspects"]["count"] == expected["suspects"]["count"]
    # representative top entries
    assert payload["ghosts"]["top5"] == expected["ghosts"]["top5"]
    assert payload["stale"]["top5"] == expected["stale"]["top5"]


async def test_importing_async_corpulse_from_package_root_is_lazy(monkeypatch):
    monkeypatch.delitem(sys.modules, "asyncpg", raising=False)

    import corpulse

    assert hasattr(corpulse, "AsyncCorpulse")
    assert corpulse.AsyncCorpulse.__name__ == "AsyncCorpulse"
    assert "asyncpg" not in sys.modules
