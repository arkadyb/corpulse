import inspect
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from corpulse.backends import InMemoryBackend
from corpulse.backends.base import (
    DocumentRow,
    EmbeddingRow,
    EngagementRow,
    RetrievalRow,
    StorageBackend,
    StorageBackendError,
)
from corpulse.db import DB


def test_storage_backend_contract_is_frozen():
    required = {
        "upsert_document": ["self", "doc_id", "filename", "embedding", "embedded_at"],
        "insert_retrieval": ["self", "doc_id", "query_hash", "rank", "score", "retrieved_at"],
        "insert_engagement": ["self", "doc_id", "event_type", "engaged_at"],
        "update_source_timestamp": ["self", "doc_id", "updated_at"],
        "all_documents": ["self"],
        "retrieval_counts": ["self", "since"],
        "engagement_counts": ["self", "since"],
        "all_embeddings": ["self"],
        "close": ["self"],
    }

    assert required.keys() <= StorageBackend.__abstractmethods__

    for name, expected in required.items():
        actual = list(inspect.signature(getattr(StorageBackend, name)).parameters)
        assert actual == expected

    assert "__enter__" in StorageBackend.__dict__
    assert "__exit__" in StorageBackend.__dict__

    expected_keys = {
        DocumentRow: {"doc_id", "filename", "source_updated_at", "embedding_vec", "embedded_at"},
        RetrievalRow: {"doc_id", "cnt", "avg_rank", "avg_score"},
        EngagementRow: {"doc_id", "cnt"},
        EmbeddingRow: {"doc_id", "filename", "embedding_vec"},
    }
    for row_type, keys in expected_keys.items():
        assert keys <= set(row_type.__annotations__)

    assert issubclass(StorageBackendError, RuntimeError)


def test_backend_parity(backend):
    backend.upsert_document(
        "doc-1",
        "doc-1.md",
        embedding=b"vec",
        embedded_at=12.5,
    )
    backend.insert_retrieval("doc-1", "hash", 1, 0.9, 25.0)
    backend.insert_engagement("doc-1", "opened", 30.0)
    backend.update_source_timestamp("doc-1", 40.0)

    documents = backend.all_documents()
    retrievals = backend.retrieval_counts(0.0)
    engagements = backend.engagement_counts(0.0)
    embeddings = backend.all_embeddings()

    assert documents == [
        {
            "doc_id": "doc-1",
            "filename": "doc-1.md",
            "embedding_vec": b"vec",
            "embedded_at": 12.5,
            "source_updated_at": 40.0,
        }
    ]
    assert retrievals == [
        {"doc_id": "doc-1", "cnt": 1, "avg_rank": 1.0, "avg_score": 0.9}
    ]
    assert engagements == [{"doc_id": "doc-1", "cnt": 1}]
    assert embeddings == [
        {"doc_id": "doc-1", "filename": "doc-1.md", "embedding_vec": b"vec"}
    ]


def test_sqlite_backend_enables_wal(sqlite_backend):
    with sqlite_backend._conn() as conn:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]

    assert journal_mode == "wal"


def test_translated_runtime_error(sqlite_backend, monkeypatch):
    def raising_conn():
        raise sqlite3.OperationalError("boom")

    monkeypatch.setattr(sqlite_backend, "_conn", raising_conn)

    with pytest.raises(StorageBackendError, match="boom") as exc_info:
        sqlite_backend.all_documents()

    assert isinstance(exc_info.value.__cause__, sqlite3.OperationalError)


def test_shared_backend_fixture_uses_sqlite_backend(sqlite_backend):
    assert isinstance(sqlite_backend, DB)


def test_shared_backend_fixture_runs_for_sqlite_and_memory(backend, request):
    if request.node.callspec.params["backend"] == "sqlite":
        assert isinstance(backend, DB)
        return

    if request.node.callspec.params["backend"] == "postgres":
        assert backend.__class__.__name__ == "PostgresBackend"
        return

    assert isinstance(backend, InMemoryBackend)


def test_inmemory_backend_persists_documents_and_events_without_filesystem():
    backend = InMemoryBackend()

    backend.upsert_document("doc-1", "guide.md")
    backend.insert_retrieval("doc-1", "qhash", 1, 0.75, 20.0)
    backend.insert_engagement("doc-1", "opened", 25.0)

    assert backend.all_documents() == [
        {
            "doc_id": "doc-1",
            "filename": "guide.md",
            "embedding_vec": None,
            "embedded_at": None,
            "source_updated_at": None,
        }
    ]
    assert backend.retrieval_counts(0.0) == [
        {"doc_id": "doc-1", "cnt": 1, "avg_rank": 1.0, "avg_score": 0.75}
    ]
    assert backend.engagement_counts(0.0) == [{"doc_id": "doc-1", "cnt": 1}]


def test_inmemory_backend_upsert_preserves_existing_embedding_fields_on_none():
    backend = InMemoryBackend()

    backend.upsert_document("doc-1", "guide-v1.md", embedding=b"vec-1", embedded_at=10.0)
    backend.upsert_document("doc-1", "guide-v2.md", embedding=None, embedded_at=None)

    assert backend.all_documents() == [
        {
            "doc_id": "doc-1",
            "filename": "guide-v2.md",
            "embedding_vec": b"vec-1",
            "embedded_at": 10.0,
            "source_updated_at": None,
        }
    ]


def test_inmemory_backend_matches_sqlite_visible_aggregate_shapes():
    backend = InMemoryBackend()

    backend.upsert_document("doc-1", "guide.md", embedding=b"vec-1", embedded_at=10.0)
    backend.insert_retrieval("doc-1", "qhash-1", 1, 0.5, 20.0)
    backend.insert_retrieval("doc-1", "qhash-2", 3, 1.0, 21.0)
    backend.insert_engagement("doc-1", "opened", 22.0)
    backend.update_source_timestamp("missing-doc", 30.0)

    assert backend.retrieval_counts(0.0) == [
        {"doc_id": "doc-1", "cnt": 2, "avg_rank": 2.0, "avg_score": 0.75}
    ]
    assert backend.engagement_counts(0.0) == [{"doc_id": "doc-1", "cnt": 1}]
    assert backend.all_embeddings() == [
        {"doc_id": "doc-1", "filename": "guide.md", "embedding_vec": b"vec-1"}
    ]
