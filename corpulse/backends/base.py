from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypedDict


class DocumentRow(TypedDict):
    doc_id: str
    filename: str
    embedding_vec: bytes | None
    embedded_at: float | None
    source_updated_at: float | None


class RetrievalRow(TypedDict):
    doc_id: str
    cnt: int
    avg_rank: float | None
    avg_score: float | None


class EngagementRow(TypedDict):
    doc_id: str
    cnt: int


class EmbeddingRow(TypedDict):
    doc_id: str
    filename: str
    embedding_vec: bytes


class StorageBackendError(RuntimeError):
    """Raised when a storage backend operation fails."""


class StorageBackend(ABC):
    @abstractmethod
    def upsert_document(
        self,
        doc_id: str,
        filename: str,
        embedding: bytes | None = None,
        embedded_at: float | None = None,
    ) -> None:
        """Create or update a document row."""

    @abstractmethod
    def insert_retrieval(
        self,
        doc_id: str,
        query_hash: str,
        rank: int,
        score: float,
        retrieved_at: float,
    ) -> None:
        """Record a retrieval event."""

    @abstractmethod
    def insert_engagement(
        self,
        doc_id: str,
        event_type: str,
        engaged_at: float,
    ) -> None:
        """Record an engagement event."""

    @abstractmethod
    def update_source_timestamp(self, doc_id: str, updated_at: float) -> None:
        """Store the latest known source update time for a document."""

    @abstractmethod
    def all_documents(self) -> list[DocumentRow]:
        """Return every stored document row."""

    @abstractmethod
    def retrieval_counts(self, since: float) -> list[RetrievalRow]:
        """Return retrieval aggregates since a timestamp."""

    @abstractmethod
    def engagement_counts(self, since: float) -> list[EngagementRow]:
        """Return engagement aggregates since a timestamp."""

    @abstractmethod
    def all_embeddings(self) -> list[EmbeddingRow]:
        """Return every document with a stored embedding vector."""

    @abstractmethod
    def close(self) -> None:
        """Release backend resources."""

    def __enter__(self) -> StorageBackend:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
