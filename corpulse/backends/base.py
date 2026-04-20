from __future__ import annotations

from abc import ABC, abstractmethod
from ..models import (
    DocumentRow as DocumentRow,
    EngagementEventRow as EngagementEventRow,
    QueryAttemptRow as QueryAttemptRow,
    QueryRow as QueryRow,
    RetrievalRow as RetrievalRow,
    EngagementRow as EngagementRow,
    EmbeddingRow as EmbeddingRow,
)


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
    def insert_query_attempt(
        self,
        query_hash: str,
        result_count: int,
        attempted_at: float,
    ) -> None:
        """Record a query attempt regardless of whether results were returned."""

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
    def delete_document(self, doc_id: str) -> None:
        """Delete a document and its related retrieval and engagement rows."""

    @abstractmethod
    def all_documents(self) -> list[DocumentRow]:
        """Return every stored document row."""

    @abstractmethod
    def retrieval_counts(self, since: float) -> list[RetrievalRow]:
        """Return retrieval aggregates since a timestamp."""

    @abstractmethod
    def query_counts(self, since: float) -> list[QueryRow]:
        """Return query aggregates since a timestamp."""

    @abstractmethod
    def query_attempt_counts(self, since: float) -> list[QueryAttemptRow]:
        """Return query-attempt aggregates since a timestamp."""

    @abstractmethod
    def engagement_counts(self, since: float) -> list[EngagementRow]:
        """Return engagement aggregates since a timestamp."""

    @abstractmethod
    def engagement_event_counts(self, since: float) -> list[EngagementEventRow]:
        """Return engagement event-type aggregates since a timestamp."""

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
