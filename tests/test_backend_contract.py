import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from corpulse.backends.base import (
    DocumentRow,
    EmbeddingRow,
    EngagementRow,
    RetrievalRow,
    StorageBackend,
    StorageBackendError,
)


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


@pytest.mark.skip(reason="Activate in 06-02/06-03 once concrete backends exist")
def test_sqlite_backend_parity_placeholder():
    assert False, "placeholder"


@pytest.mark.skip(reason="Activate in 06-02/06-03 once concrete backends exist")
def test_translated_runtime_error_placeholder():
    assert False, "placeholder"


@pytest.mark.skip(reason="Activate in 06-02/06-03 once concrete backends exist")
def test_shared_backend_fixture_placeholder():
    assert False, "placeholder"
