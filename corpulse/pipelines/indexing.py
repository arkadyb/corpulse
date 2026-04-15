from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

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
