import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
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
        # Split by space for simplicity
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
    client.upsert.return_value = asyncio.Future()
    client.upsert.return_value.set_result(True)
    
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
