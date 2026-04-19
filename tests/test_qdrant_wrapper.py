"""
Comprehensive test suite for QdrantCorpulseClient (sync) and
AsyncQdrantCorpulseClient (async).

All tests run against real in-memory Qdrant clients (no mocks).
Covers: QDRT-01 through QDRT-10, TEST-02, TEST-03, TEST-04.
"""

import numpy as np
import pytest
from qdrant_client import QdrantClient, AsyncQdrantClient, models
from qdrant_client.http.models import QueryResponse

from corpulse import Corpulse
from corpulse.integrations.qdrant import QdrantCorpulseClient, AsyncQdrantCorpulseClient

# ── constants ─────────────────────────────────────────────────────────────────

COLLECTION = "test"
VECTOR_SIZE = 4
QUERY_VEC = [0.1, 0.2, 0.3, 0.4]

# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def corpulse(tmp_path):
    """File-based Corpulse instance, isolated per test."""
    return Corpulse(str(tmp_path / "test.db"))


@pytest.fixture
def qdrant_client_fixture():
    """Real in-memory QdrantClient with a pre-populated test collection."""
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE,
        ),
    )
    client.upsert(
        collection_name=COLLECTION,
        points=[
            models.PointStruct(
                id=1,
                vector=[0.1, 0.2, 0.3, 0.4],
                payload={"doc_id": "abc", "filename": "guide.md"},
            ),
            models.PointStruct(
                id=2,
                vector=[0.5, 0.6, 0.7, 0.8],
                payload={"doc_id": "def", "filename": "faq.md"},
            ),
        ],
    )
    return client


@pytest.fixture
async def async_qdrant_client_fixture():
    """Real in-memory AsyncQdrantClient with a pre-populated test collection."""
    client = AsyncQdrantClient(":memory:")
    await client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE,
        ),
    )
    await client.upsert(
        collection_name=COLLECTION,
        points=[
            models.PointStruct(
                id=1,
                vector=[0.1, 0.2, 0.3, 0.4],
                payload={"doc_id": "abc", "filename": "guide.md"},
            ),
            models.PointStruct(
                id=2,
                vector=[0.5, 0.6, 0.7, 0.8],
                payload={"doc_id": "def", "filename": "faq.md"},
            ),
        ],
    )
    return client


# ── helpers ───────────────────────────────────────────────────────────────────


def _retrieval_count(corpulse):
    with corpulse.db._conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM retrievals").fetchone()[0]


def _query_attempt_count(corpulse):
    with corpulse.db._conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM query_attempts").fetchone()[0]


def _doc_ids(corpulse):
    with corpulse.db._conn() as conn:
        rows = conn.execute("SELECT doc_id FROM retrievals").fetchall()
    return [r[0] for r in rows]


def _filenames(corpulse):
    with corpulse.db._conn() as conn:
        rows = conn.execute("SELECT filename FROM documents").fetchall()
    return [r[0] for r in rows]


def _embeddings_not_null_count(corpulse):
    with corpulse.db._conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM documents WHERE embedding_vec IS NOT NULL"
        ).fetchone()[0]


def _stored_embedding(corpulse, doc_id):
    with corpulse.db._conn() as conn:
        row = conn.execute(
            "SELECT embedding_vec FROM documents WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()
    assert row is not None
    assert row[0] is not None
    return np.frombuffer(row[0], dtype=np.float32)


class _SyncLoggingCorpulse:
    def __init__(self):
        self.calls = []

    def log_retrieval(self, results, query=""):
        self.calls.append((results, query))


# ── sync tests ────────────────────────────────────────────────────────────────


def test_wrapper_holds_client(qdrant_client_fixture, corpulse):
    """QDRT-01: wrapper._client is the exact QdrantClient passed in."""
    wrapper = QdrantCorpulseClient(qdrant_client_fixture, corpulse)
    assert wrapper._client is qdrant_client_fixture


def test_query_points_calls_log_retrieval(qdrant_client_fixture, corpulse):
    """QDRT-02: After query_points(), Corpulse DB has retrieval records."""
    wrapper = QdrantCorpulseClient(qdrant_client_fixture, corpulse)
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    assert _retrieval_count(corpulse) > 0


def test_query_text_is_forwarded_to_sync_log_retrieval(qdrant_client_fixture):
    """QDRT-02: Sync wrapper forwards caller query text to log_retrieval()."""
    corpulse = _SyncLoggingCorpulse()
    wrapper = QdrantCorpulseClient(qdrant_client_fixture, corpulse)

    wrapper.query_points(
        COLLECTION,
        query=QUERY_VEC,
        query_text="how do I install corpulse?",
        limit=5,
    )

    assert corpulse.calls and corpulse.calls[0][1] == "how do I install corpulse?"


def test_search_interception(qdrant_client_fixture, corpulse):
    """QDRT-03: wrapper.search() follows the installed client's behavior."""
    wrapper = QdrantCorpulseClient(qdrant_client_fixture, corpulse)
    client = QdrantClient(":memory:")

    if hasattr(client, "search"):
        result = wrapper.search(COLLECTION, query_vector=QUERY_VEC, limit=5)
        assert _retrieval_count(corpulse) > 0
        assert isinstance(result, list)
    else:
        with pytest.raises(AttributeError):
            wrapper.search(COLLECTION, query_vector=QUERY_VEC, limit=5)
        assert _retrieval_count(corpulse) == 0


def test_returns_unmodified_response(qdrant_client_fixture, corpulse):
    """QDRT-04 / TEST-04: query_points() returns original QueryResponse unmodified."""
    wrapper = QdrantCorpulseClient(qdrant_client_fixture, corpulse)
    result = wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    assert isinstance(result, QueryResponse)
    assert len(result.points) == 2
    assert result.points[0].id in (1, 2)


def test_getattr_delegation(qdrant_client_fixture, corpulse):
    """QDRT-05: Non-intercepted methods delegate transparently via __getattr__."""
    wrapper = QdrantCorpulseClient(qdrant_client_fixture, corpulse)
    info = wrapper.get_collection(COLLECTION)
    # CollectionInfo has a config attribute — proves delegation works
    assert hasattr(info, "config")


def test_payload_id_field_none_uses_point_id(qdrant_client_fixture, corpulse):
    """QDRT-06: payload_id_field=None uses str(point.id) as doc_id, not payload value."""
    wrapper = QdrantCorpulseClient(qdrant_client_fixture, corpulse, payload_id_field=None)
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    ids = _doc_ids(corpulse)
    # Should be "1" and "2", not "abc" / "def"
    assert any(i in ("1", "2") for i in ids)
    assert "abc" not in ids
    assert "def" not in ids


def test_payload_id_field_custom(qdrant_client_fixture, corpulse):
    """QDRT-06: payload_id_field='doc_id' extracts doc_id from payload."""
    wrapper = QdrantCorpulseClient(qdrant_client_fixture, corpulse, payload_id_field="doc_id")
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    ids = _doc_ids(corpulse)
    assert any(i in ("abc", "def") for i in ids)


def test_payload_filename_key_custom(corpulse):
    """QDRT-07: payload_filename_key='source' extracts filename from custom payload key."""
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
    )
    client.upsert(
        collection_name=COLLECTION,
        points=[
            models.PointStruct(
                id=10,
                vector=[0.1, 0.2, 0.3, 0.4],
                payload={"doc_id": "x", "source": "readme.md"},
            ),
        ],
    )
    wrapper = QdrantCorpulseClient(client, corpulse, payload_filename_key="source")
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    fnames = _filenames(corpulse)
    assert "readme.md" in fnames


def test_vector_capture_with_vectors_true(qdrant_client_fixture, corpulse):
    """QDRT-10: with_vectors=True causes embeddings to be stored in Corpulse."""
    wrapper = QdrantCorpulseClient(qdrant_client_fixture, corpulse)
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5, with_vectors=True)
    assert _embeddings_not_null_count(corpulse) > 0


def test_named_vector_capture_uses_requested_vector(corpulse):
    """QDRT-10: with_vectors=['dense'] stores the requested named vector bytes."""
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={
            "dense": models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
            "sparse": models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
        },
    )
    client.upsert(
        collection_name=COLLECTION,
        points=[
            models.PointStruct(
                id=10,
                vector={
                    "dense": [0.1, 0.2, 0.3, 0.4],
                    "sparse": [0.9, 0.8, 0.7, 0.6],
                },
                payload={"doc_id": "named-doc", "filename": "named.md"},
            ),
        ],
    )

    wrapper = QdrantCorpulseClient(client, corpulse, payload_id_field="doc_id")
    result = wrapper.query_points(
        COLLECTION,
        query=QUERY_VEC,
        using="dense",
        with_vectors=["dense"],
        limit=1,
    )

    assert isinstance(result.points[0].vector, dict)
    stored = _stored_embedding(corpulse, "named-doc")
    dense_vector = np.array(result.points[0].vector["dense"], dtype=np.float32)
    assert np.allclose(stored, dense_vector)


def test_vector_not_captured_by_default(qdrant_client_fixture, corpulse):
    """QDRT-10: Without with_vectors, embedding should be None (not stored)."""
    wrapper = QdrantCorpulseClient(qdrant_client_fixture, corpulse)
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    assert _embeddings_not_null_count(corpulse) == 0


def test_empty_query_points_records_query_attempt(corpulse):
    """Empty query_points() calls should persist a zero-result attempt."""
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
    )
    wrapper = QdrantCorpulseClient(client, corpulse)
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    assert _retrieval_count(corpulse) == 0
    assert _query_attempt_count(corpulse) == 1


def test_empty_search_records_query_attempt(corpulse):
    """Empty search() calls should persist a zero-result attempt."""
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
    )
    wrapper = QdrantCorpulseClient(client, corpulse)

    if not hasattr(client, "search"):
        pytest.skip("search() not available in this qdrant-client build")

    wrapper.search(COLLECTION, query_vector=QUERY_VEC, limit=5)
    assert _retrieval_count(corpulse) == 0
    assert _query_attempt_count(corpulse) == 1


def test_null_payload_handled(corpulse):
    """Point with payload=None should not raise; doc_id falls back to str(point_id)."""
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
    )
    client.upsert(
        collection_name=COLLECTION,
        points=[
            models.PointStruct(id=99, vector=[0.1, 0.2, 0.3, 0.4], payload=None),
        ],
    )
    wrapper = QdrantCorpulseClient(client, corpulse, payload_id_field=None)
    # Must not raise
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    ids = _doc_ids(corpulse)
    assert "99" in ids


# ── async tests ───────────────────────────────────────────────────────────────


async def test_async_wrapper_holds_client(async_qdrant_client_fixture, corpulse):
    """QDRT-08: async wrapper._client is the exact AsyncQdrantClient passed in."""
    wrapper = AsyncQdrantCorpulseClient(async_qdrant_client_fixture, corpulse)
    assert wrapper._client is async_qdrant_client_fixture


async def test_async_query_points(async_qdrant_client_fixture, corpulse):
    """QDRT-09: Async wrapper intercepts query_points and calls log_retrieval."""
    wrapper = AsyncQdrantCorpulseClient(async_qdrant_client_fixture, corpulse)
    result = await wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    assert isinstance(result, QueryResponse)
    assert _retrieval_count(corpulse) > 0


async def test_async_query_text_is_forwarded_to_log_retrieval(async_qdrant_client_fixture):
    """QDRT-09: Async wrapper forwards caller query text to log_retrieval()."""
    corpulse = _AsyncLoggingCorpulse()
    wrapper = AsyncQdrantCorpulseClient(async_qdrant_client_fixture, corpulse)

    await wrapper.query_points(
        COLLECTION,
        query=QUERY_VEC,
        query_text="how do I install corpulse?",
        limit=5,
    )

    assert corpulse.calls and corpulse.calls[0][1] == "how do I install corpulse?"


async def test_async_search_interception(async_qdrant_client_fixture, corpulse):
    """Async wrapper.search() follows the installed client's behavior."""
    wrapper = AsyncQdrantCorpulseClient(async_qdrant_client_fixture, corpulse)
    client = AsyncQdrantClient(":memory:")

    if hasattr(client, "search"):
        result = await wrapper.search(COLLECTION, query_vector=QUERY_VEC, limit=5)
        assert _retrieval_count(corpulse) > 0
        assert isinstance(result, list)
    else:
        with pytest.raises(AttributeError):
            await wrapper.search(COLLECTION, query_vector=QUERY_VEC, limit=5)
        assert _retrieval_count(corpulse) == 0


async def test_async_empty_query_points_records_query_attempt(corpulse):
    """Empty async query_points() calls should persist a zero-result attempt."""
    client = AsyncQdrantClient(":memory:")
    await client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
    )
    wrapper = AsyncQdrantCorpulseClient(client, corpulse)

    await wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)

    assert _retrieval_count(corpulse) == 0
    assert _query_attempt_count(corpulse) == 1


async def test_async_empty_search_records_query_attempt(corpulse):
    """Empty async search() calls should persist a zero-result attempt."""
    client = AsyncQdrantClient(":memory:")
    await client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
    )
    wrapper = AsyncQdrantCorpulseClient(client, corpulse)

    if not hasattr(client, "search"):
        pytest.skip("search() not available in this qdrant-client build")

    await wrapper.search(COLLECTION, query_vector=QUERY_VEC, limit=5)
    assert _retrieval_count(corpulse) == 0
    assert _query_attempt_count(corpulse) == 1


class _AsyncLoggingCorpulse:
    def __init__(self):
        self.calls = []

    async def log_retrieval(self, results, query=""):
        self.calls.append((results, query))


class _AsyncSearchClient:
    async def search(self, collection_name, **kwargs):
        return [
            models.ScoredPoint(
                id=1,
                version=1,
                score=0.99,
                payload={"doc_id": "abc", "filename": "guide.md"},
                vector=None,
            )
        ]


async def test_async_search_awaits_async_corpulse_log_retrieval():
    wrapper = AsyncQdrantCorpulseClient(
        _AsyncSearchClient(),
        _AsyncLoggingCorpulse(),
        payload_id_field="doc_id",
    )

    result = await wrapper.search(COLLECTION, query_vector=QUERY_VEC, limit=5)

    assert len(result) == 1
    assert wrapper._corpulse.calls == [
        (
            [
                {
                    "doc_id": "abc",
                    "filename": "guide.md",
                    "score": 0.99,
                    "embedding": None,
                }
            ],
            "",
        )
    ]
