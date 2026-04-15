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
