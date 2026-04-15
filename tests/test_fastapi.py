from __future__ import annotations

import pytest

try:
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from corpulse.async_core import AsyncCorpulse
from corpulse.core import _vec_to_bytes
from corpulse.fastapi import get_corpulse_router

if not HAS_FASTAPI:
    pytest.skip("fastapi and httpx are required for integration tests", allow_module_level=True)

# --- Reusing FakeAsyncBackend from tests/test_async_core_integration.py ---

class FakeAsyncBackend:
    def __init__(self, documents, retrieval_rows, engagement_rows, embedding_rows):
        self.documents = documents
        self.retrieval_rows = retrieval_rows
        self.engagement_rows = engagement_rows
        self.embedding_rows = embedding_rows
        self.closed = False

    async def all_documents(self) -> list[dict]:
        return self.documents

    async def retrieval_counts(self, since: float) -> list[dict]:
        return self.retrieval_rows

    async def engagement_counts(self, since: float) -> list[dict]:
        return self.engagement_rows

    async def all_embeddings(self) -> list[dict]:
        return self.embedding_rows

    async def close(self) -> None:
        self.closed = True

def _analysis_fixture_rows():
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

# --- Test Infrastructure ---

@pytest.fixture
def test_backend():
    docs, r_rows, e_rows, emb_rows = _analysis_fixture_rows()
    return FakeAsyncBackend(docs, r_rows, e_rows, emb_rows)

@pytest.fixture
def app(test_backend):
    def get_test_corpulse():
        return AsyncCorpulse(backend=test_backend)

    app = FastAPI()
    router = get_corpulse_router(get_test_corpulse)
    app.include_router(router)
    return app

@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

# --- Integration Tests ---

@pytest.mark.asyncio
async def test_get_report(client, monkeypatch):
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)
    response = await client.get("/report")
    assert response.status_code == 200
    payload = response.json()
    assert "summary" in payload
    assert "rows" in payload
    assert payload["summary"]["total_docs"] == 7

@pytest.mark.asyncio
async def test_get_cleanup_report(client, monkeypatch):
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)
    response = await client.get("/cleanup-report")
    assert response.status_code == 200
    payload = response.json()
    assert "total_docs" in payload
    assert payload["total_docs"] == 7
    assert "ghosts" in payload
    assert "obsolete" in payload

@pytest.mark.asyncio
async def test_get_ghosts(client, monkeypatch):
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)
    response = await client.get("/ghosts")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    # Documents: old, new, stale, dup-a, dup-b, suspect, healthy
    # Retrieval rows for: new, dup-a, dup-b, suspect, healthy
    # Ghosts should be: old, stale
    assert len(payload) == 2
    ghost_ids = {g["doc_id"] for g in payload}
    assert "old" in ghost_ids
    assert "stale" in ghost_ids

@pytest.mark.asyncio
async def test_get_duplicates(client):
    response = await client.get("/duplicates")
    if response.status_code == 501:
        pytest.skip("scikit-learn is not installed")
    
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 1
    assert payload[0]["doc_id_a"] == "dup-a"
    assert payload[0]["doc_id_b"] == "dup-b"

@pytest.mark.asyncio
async def test_get_obsolete(client):
    response = await client.get("/obsolete")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["doc_id"] == "old"
    assert payload[0]["superseded_by"] == "api-v2.md"

@pytest.mark.asyncio
async def test_get_stale(client):
    response = await client.get("/stale")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["doc_id"] == "stale"

@pytest.mark.asyncio
async def test_get_suspects(client, monkeypatch):
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 123.0)
    response = await client.get("/suspects")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["doc_id"] == "suspect"
    assert payload[0]["engagement_rate"] == 0.0
