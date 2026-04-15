import pytest
import uuid
from corpulse.integrations.qdrant import collection_name_for_user, chunk_id

def test_collection_name_for_user_sanitization():
    # Normal ID
    assert collection_name_for_user("user1") == "corpulse_user1"
    
    # Mixed case
    assert collection_name_for_user("UserOne") == "corpulse_userone"
    
    # Special characters
    assert collection_name_for_user("user-@#123") == "corpulse_user_123"
    
    # Leading/trailing separators
    assert collection_name_for_user("-user-") == "corpulse_user"
    
    # Custom base
    assert collection_name_for_user("user1", base="app") == "app_user1"

def test_chunk_id_determinism():
    id1 = chunk_id("doc1", 0)
    id2 = chunk_id("doc1", 0)
    assert id1 == id2
    assert isinstance(id1, str)
    # Check if it's a valid UUID
    uuid.UUID(id1)

def test_chunk_id_uniqueness():
    id1 = chunk_id("doc1", 0)
    id2 = chunk_id("doc1", 1)
    id3 = chunk_id("doc2", 0)
    assert id1 != id2
    assert id1 != id3

def test_chunk_id_stability():
    # Verify against a hardcoded UUID string to ensure the namespace doesn't change.
    # We need to know what CORPULSE_NAMESPACE (uuid.uuid5(uuid.NAMESPACE_DNS, "corpulse.ai")) 
    # and the input "doc1:0" produces.
    expected = "617fd494-f536-5ad4-9e0f-cfe17240c580"
    assert chunk_id("doc1", 0) == expected

# ── integration tests ─────────────────────────────────────────────────────────

from qdrant_client import QdrantClient, AsyncQdrantClient, models
from corpulse.integrations.qdrant import delete_document_points, ensure_collection

def test_delete_document_points_sync():
    client = QdrantClient(":memory:")
    collection_name = "test_delete"
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=4, distance=models.Distance.COSINE),
    )
    client.upsert(
        collection_name=collection_name,
        points=[
            models.PointStruct(id=1, vector=[0.1, 0.2, 0.3, 0.4], payload={"doc_id": "abc"}),
            models.PointStruct(id=2, vector=[0.5, 0.6, 0.7, 0.8], payload={"doc_id": "def"}),
            models.PointStruct(id=3, vector=[0.1, 0.1, 0.1, 0.1], payload={"doc_id": "abc"}),
        ],
    )
    
    # Verify count
    assert client.count(collection_name).count == 3
    
    # Delete "abc"
    delete_document_points(client, collection_name, "abc")
    
    # Verify remaining
    assert client.count(collection_name).count == 1
    points = client.retrieve(collection_name, ids=[2])
    assert len(points) == 1
    assert points[0].payload["doc_id"] == "def"

def test_delete_document_points_none_id_field_sync():
    client = QdrantClient(":memory:")
    collection_name = "test_delete_none"
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=4, distance=models.Distance.COSINE),
    )
    client.upsert(
        collection_name=collection_name,
        points=[
            models.PointStruct(id=100, vector=[0.1, 0.2, 0.3, 0.4], payload={"doc_id": "abc"}),
        ],
    )
    
    # Delete by point ID directly
    delete_document_points(client, collection_name, 100, payload_id_field=None)
    
    assert client.count(collection_name).count == 0

@pytest.mark.asyncio
async def test_delete_document_points_async():
    client = AsyncQdrantClient(":memory:")
    collection_name = "test_delete_async"
    await client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=4, distance=models.Distance.COSINE),
    )
    await client.upsert(
        collection_name=collection_name,
        points=[
            models.PointStruct(id=1, vector=[0.1, 0.2, 0.3, 0.4], payload={"doc_id": "abc"}),
            models.PointStruct(id=2, vector=[0.5, 0.6, 0.7, 0.8], payload={"doc_id": "def"}),
        ],
    )
    
    # Delete "abc"
    await delete_document_points(client, collection_name, "abc")
    
    # Verify remaining
    res = await client.count(collection_name)
    assert res.count == 1

def test_ensure_collection_sync():
    client = QdrantClient(":memory:")
    name = "test_ensure"
    vec_config = models.VectorParams(size=4, distance=models.Distance.COSINE)
    
    # First call - creates
    ensure_collection(client, name, vec_config, payload_indexes=["doc_id", "filename"])
    assert client.collection_exists(name)
    
    # Check info
    info = client.get_collection(name)
    assert info.status == models.CollectionStatus.GREEN
    # Note: payload_schema may be empty in :memory: Qdrant as it issues a warning
    # that payload indexes have no effect in local mode.
    
    # Second call - idempotent
    ensure_collection(client, name, vec_config, payload_indexes=["doc_id"])
    assert client.collection_exists(name)

@pytest.mark.asyncio
async def test_ensure_collection_async():
    client = AsyncQdrantClient(":memory:")
    name = "test_ensure_async"
    vec_config = models.VectorParams(size=4, distance=models.Distance.COSINE)
    
    # First call
    await ensure_collection(client, name, vec_config, payload_indexes=["doc_id"])
    assert await client.collection_exists(name)
    
    # Second call
    await ensure_collection(client, name, vec_config)
    assert await client.collection_exists(name)
