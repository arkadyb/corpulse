from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    from corpulse.async_core import AsyncCorpulse

@dataclass(frozen=True)
class IndexingResult:
    """Result of an indexing operation."""
    doc_id: str
    chunk_count: int
    duration_ms: float

@runtime_checkable
class Parser(Protocol):
    """Protocol for document parsing."""
    async def parse(self, source: Any) -> str:
        """Parse source content into plain text."""
        ...

@runtime_checkable
class Chunker(Protocol):
    """Protocol for text chunking."""
    async def chunk(self, text: str) -> list[str]:
        """Split text into a list of chunks."""
        ...

@runtime_checkable
class Embedder(Protocol):
    """Protocol for text embedding."""
    async def embed(self, chunks: list[str]) -> list[list[float]]:
        """Embed a list of chunks into vector space."""
        ...

async def index_document(
    doc_id: str,
    filename: str,
    source: Any,
    collection_name: str,
    client: Any,
    corpulse: AsyncCorpulse,
    parser: Parser,
    chunker: Chunker,
    embedder: Embedder,
    vector_name: str | None = None,
) -> IndexingResult:
    """Orchestrate the indexing of a document.

    Flow:
    1. Parse source content into plain text using `parser`.
    2. Split text into chunks using `chunker`.
    3. Embed chunks into vector space using `embedder`.
    4. Upsert vectors and payload to Qdrant using `client`.
    5. Register document in Corpulse using `corpulse`.

    Returns:
        IndexingResult: Stats about the indexing operation.
    """
    import asyncio
    import inspect
    import logging
    import time

    import numpy as np
    from qdrant_client.models import PointStruct

    from corpulse.integrations.qdrant import chunk_id, delete_document_points

    logger = logging.getLogger(__name__)
    start = time.perf_counter()

    # 1. Parse source
    text = await parser.parse(source)

    # 2. Chunk text
    chunks = await chunker.chunk(text)

    # 3. Embed chunks with exponential backoff retries
    max_attempts = 3
    embeddings: list[list[float]] = []
    for attempt in range(1, max_attempts + 1):
        try:
            embeddings = await embedder.embed(chunks)
            break
        except Exception as e:
            if attempt == max_attempts:
                raise
            delay = 2**attempt
            logger.warning(
                f"Embedding attempt {attempt} failed: {e}. Retrying in {delay}s..."
            )
            await asyncio.sleep(delay)

    # 4. Upsert to Qdrant
    points = []
    for i, vector in enumerate(embeddings):
        p_id = chunk_id(doc_id, i)
        payload = {"doc_id": doc_id}

        if vector_name:
            points.append(
                PointStruct(id=p_id, vector={vector_name: vector}, payload=payload)
            )
        else:
            points.append(PointStruct(id=p_id, vector=vector, payload=payload))

    upsert_res = client.upsert(collection_name=collection_name, points=points)
    if inspect.isawaitable(upsert_res):
        await upsert_res

    # 5. Register in Corpulse with rollback on failure
    mean_embedding = np.mean(embeddings, axis=0).tolist()
    try:
        await corpulse.register_document(doc_id, filename, mean_embedding)
    except Exception:
        # Rollback: delete points from Qdrant to avoid ghost vectors
        delete_res = delete_document_points(client, collection_name, doc_id)
        if inspect.isawaitable(delete_res):
            await delete_res
        raise

    duration_ms = (time.perf_counter() - start) * 1000
    return IndexingResult(
        doc_id=doc_id,
        chunk_count=len(chunks),
        duration_ms=duration_ms,
    )
