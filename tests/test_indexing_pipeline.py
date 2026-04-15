import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from corpulse.pipelines.indexing import (
    index_document,
    Parser,
    Chunker,
    Embedder,
    IndexingResult,
)

class FakeParser:
    async def parse(self, source: str) -> str:
        return f"parsed:{source}"

class FakeChunker:
    async def chunk(self, text: str) -> list[str]:
        # Split by : for simplicity
        return text.split(":")

class FakeEmbedder:
    def __init__(self, fail_count=0):
        self.fail_count = fail_count
        self.calls = 0

    async def embed(self, chunks: list[str]) -> list[list[float]]:
        self.calls += 1
        if self.calls <= self.fail_count:
            raise ValueError(f"Injected failure {self.calls}")
        # Return a simple 128-dim vector for each chunk
        return [[float(i)] * 128 for i in range(len(chunks))]

@pytest.mark.asyncio
async def test_indexing_pipeline_happy_path():
    doc_id = "doc1"
    filename = "test.txt"
    source = "hello"
    collection_name = "test_col"
    
    # client.upsert can be sync or async in index_document
    client = MagicMock()
    # Mock upsert to return something that isn't awaitable by default
    # But index_document checks if it's awaitable
    client.upsert.return_value = None
    
    corpulse = AsyncMock()
    parser = FakeParser()
    chunker = FakeChunker()
    embedder = FakeEmbedder()

    result = await index_document(
        doc_id=doc_id,
        filename=filename,
        source=source,
        collection_name=collection_name,
        client=client,
        corpulse=corpulse,
        parser=parser,
        chunker=chunker,
        embedder=embedder,
    )

    assert isinstance(result, IndexingResult)
    assert result.doc_id == doc_id
    assert result.chunk_count == 2
    assert result.duration_ms >= 0

    # Verify calls
    client.upsert.assert_called_once()
    corpulse.register_document.assert_called_once()
    
    # Verify registration call details
    args, kwargs = corpulse.register_document.call_args
    assert args[0] == doc_id
    assert args[1] == filename
    assert len(args[2]) == 128  # mean embedding
    # mean of [0]*128 and [1]*128 should be [0.5]*128
    assert all(v == 0.5 for v in args[2])

@pytest.mark.asyncio
async def test_indexing_pipeline_embed_retry():
    # Fail once, then succeed
    embedder = FakeEmbedder(fail_count=1)
    
    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        result = await index_document(
            doc_id="doc1",
            filename="test.txt",
            source="hello",
            collection_name="test_col",
            client=MagicMock(),
            corpulse=AsyncMock(),
            parser=FakeParser(),
            chunker=FakeChunker(),
            embedder=embedder,
        )
        assert embedder.calls == 2
        mock_sleep.assert_called_once_with(2)

@pytest.mark.asyncio
async def test_indexing_pipeline_embed_retry_failure():
    # Always fail (max attempts = 3)
    embedder = FakeEmbedder(fail_count=3)
    with patch("asyncio.sleep", AsyncMock()):
        with pytest.raises(ValueError, match="Injected failure 3"):
            await index_document(
                doc_id="doc1",
                filename="test.txt",
                source="hello",
                collection_name="test_col",
                client=MagicMock(),
                corpulse=AsyncMock(),
                parser=FakeParser(),
                chunker=FakeChunker(),
                embedder=embedder,
            )
    assert embedder.calls == 3

@pytest.mark.asyncio
async def test_indexing_pipeline_rollback():
    client = MagicMock()
    corpulse = AsyncMock()
    corpulse.register_document.side_effect = Exception("Registration failed")
    
    with pytest.raises(Exception, match="Registration failed"):
        await index_document(
            doc_id="doc1",
            filename="test.txt",
            source="hello",
            collection_name="test_col",
            client=client,
            corpulse=corpulse,
            parser=FakeParser(),
            chunker=FakeChunker(),
            embedder=FakeEmbedder(),
        )
    
    # Verify rollback called delete
    client.delete.assert_called_once()
    # Check that it was called with the correct doc_id filter
    # delete_document_points uses models.Filter by default
    args, kwargs = client.delete.call_args
    assert kwargs["collection_name"] == "test_col"
    # The points_selector is a models.Filter
    from qdrant_client import models
    assert isinstance(kwargs["points_selector"], models.Filter)
    assert kwargs["points_selector"].must[0].match.value == "doc1"
