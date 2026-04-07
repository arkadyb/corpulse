"""
Comprehensive test suite for QdrantMementoClient (sync) and
AsyncQdrantMementoClient (async).

All tests run against real in-memory Qdrant clients (no mocks).
Covers: QDRT-01 through QDRT-10, TEST-02, TEST-03, TEST-04.
"""

import pytest
from qdrant_client import QdrantClient, AsyncQdrantClient, models
from qdrant_client.http.models import QueryResponse

from corpulse import Memento
from corpulse.integrations.qdrant import QdrantMementoClient, AsyncQdrantMementoClient

# ── constants ─────────────────────────────────────────────────────────────────

COLLECTION = "test"
VECTOR_SIZE = 4
QUERY_VEC = [0.1, 0.2, 0.3, 0.4]

# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def memento(tmp_path):
    """File-based Memento instance, isolated per test."""
    return Memento(str(tmp_path / "test.db"))


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


def _retrieval_count(memento):
    with memento.db._conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM retrievals").fetchone()[0]


def _doc_ids(memento):
    with memento.db._conn() as conn:
        rows = conn.execute("SELECT doc_id FROM retrievals").fetchall()
    return [r[0] for r in rows]


def _filenames(memento):
    with memento.db._conn() as conn:
        rows = conn.execute("SELECT filename FROM documents").fetchall()
    return [r[0] for r in rows]


def _embeddings_not_null_count(memento):
    with memento.db._conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM documents WHERE embedding_vec IS NOT NULL"
        ).fetchone()[0]


# ── sync tests ────────────────────────────────────────────────────────────────


def test_wrapper_holds_client(qdrant_client_fixture, memento):
    """QDRT-01: wrapper._client is the exact QdrantClient passed in."""
    wrapper = QdrantMementoClient(qdrant_client_fixture, memento)
    assert wrapper._client is qdrant_client_fixture


def test_query_points_calls_log_retrieval(qdrant_client_fixture, memento):
    """QDRT-02: After query_points(), Memento DB has retrieval records."""
    wrapper = QdrantMementoClient(qdrant_client_fixture, memento)
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    assert _retrieval_count(memento) > 0


def test_search_interception(qdrant_client_fixture, memento):
    """QDRT-03: wrapper.search() delegates; skipped if search() absent in client >= 1.16.0."""
    wrapper = QdrantMementoClient(qdrant_client_fixture, memento)
    has_search = hasattr(QdrantClient(":memory:"), "search")
    if not has_search:
        pytest.skip("search() removed in qdrant-client >= 1.16.0")
    result = wrapper.search(COLLECTION, query_vector=QUERY_VEC, limit=5)
    assert isinstance(result, list)


def test_returns_unmodified_response(qdrant_client_fixture, memento):
    """QDRT-04 / TEST-04: query_points() returns original QueryResponse unmodified."""
    wrapper = QdrantMementoClient(qdrant_client_fixture, memento)
    result = wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    assert isinstance(result, QueryResponse)
    assert len(result.points) == 2
    assert result.points[0].id in (1, 2)


def test_getattr_delegation(qdrant_client_fixture, memento):
    """QDRT-05: Non-intercepted methods delegate transparently via __getattr__."""
    wrapper = QdrantMementoClient(qdrant_client_fixture, memento)
    info = wrapper.get_collection(COLLECTION)
    # CollectionInfo has a config attribute — proves delegation works
    assert hasattr(info, "config")


def test_payload_id_field_none_uses_point_id(qdrant_client_fixture, memento):
    """QDRT-06: payload_id_field=None uses str(point.id) as doc_id, not payload value."""
    wrapper = QdrantMementoClient(qdrant_client_fixture, memento, payload_id_field=None)
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    ids = _doc_ids(memento)
    # Should be "1" and "2", not "abc" / "def"
    assert any(i in ("1", "2") for i in ids)
    assert "abc" not in ids
    assert "def" not in ids


def test_payload_id_field_custom(qdrant_client_fixture, memento):
    """QDRT-06: payload_id_field='doc_id' extracts doc_id from payload."""
    wrapper = QdrantMementoClient(qdrant_client_fixture, memento, payload_id_field="doc_id")
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    ids = _doc_ids(memento)
    assert any(i in ("abc", "def") for i in ids)


def test_payload_filename_key_custom(memento):
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
    wrapper = QdrantMementoClient(client, memento, payload_filename_key="source")
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    fnames = _filenames(memento)
    assert "readme.md" in fnames


def test_vector_capture_with_vectors_true(qdrant_client_fixture, memento):
    """QDRT-10: with_vectors=True causes embeddings to be stored in Memento."""
    wrapper = QdrantMementoClient(qdrant_client_fixture, memento)
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5, with_vectors=True)
    assert _embeddings_not_null_count(memento) > 0


def test_vector_not_captured_by_default(qdrant_client_fixture, memento):
    """QDRT-10: Without with_vectors, embedding should be None (not stored)."""
    wrapper = QdrantMementoClient(qdrant_client_fixture, memento)
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    assert _embeddings_not_null_count(memento) == 0


def test_empty_results_no_log(memento):
    """Empty collection: query_points returns 0 points, log_retrieval NOT called."""
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
    )
    wrapper = QdrantMementoClient(client, memento)
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    assert _retrieval_count(memento) == 0


def test_null_payload_handled(memento):
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
    wrapper = QdrantMementoClient(client, memento, payload_id_field=None)
    # Must not raise
    wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    ids = _doc_ids(memento)
    assert "99" in ids


# ── async tests ───────────────────────────────────────────────────────────────


async def test_async_wrapper_holds_client(async_qdrant_client_fixture, memento):
    """QDRT-08: async wrapper._client is the exact AsyncQdrantClient passed in."""
    wrapper = AsyncQdrantMementoClient(async_qdrant_client_fixture, memento)
    assert wrapper._client is async_qdrant_client_fixture


async def test_async_query_points(async_qdrant_client_fixture, memento):
    """QDRT-09: Async wrapper intercepts query_points and calls log_retrieval."""
    wrapper = AsyncQdrantMementoClient(async_qdrant_client_fixture, memento)
    result = await wrapper.query_points(COLLECTION, query=QUERY_VEC, limit=5)
    assert isinstance(result, QueryResponse)
    assert _retrieval_count(memento) > 0


async def test_async_search_interception(async_qdrant_client_fixture, memento):
    """Async wrapper.search() delegates; skipped if search() absent in client >= 1.16.0."""
    wrapper = AsyncQdrantMementoClient(async_qdrant_client_fixture, memento)
    has_search = hasattr(AsyncQdrantClient(":memory:"), "search")
    if not has_search:
        pytest.skip("search() removed in qdrant-client >= 1.16.0")
    result = await wrapper.search(COLLECTION, query_vector=QUERY_VEC, limit=5)
    assert isinstance(result, list)
