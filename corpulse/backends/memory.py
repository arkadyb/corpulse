from __future__ import annotations

from .base import (
    StorageBackend,
)
from ..models import (
    DocumentRow,
    EmbeddingRow,
    EngagementRow,
    RetrievalRow,
)


class InMemoryBackend(StorageBackend):
    def __init__(self) -> None:
        self._documents: dict[str, DocumentRow] = {}
        self._retrievals: list[dict[str, str | int | float]] = []
        self._engagements: list[dict[str, str | float]] = []
        self._closed = False

    def upsert_document(
        self,
        doc_id: str,
        filename: str,
        embedding: bytes | None = None,
        embedded_at: float | None = None,
    ) -> None:
        existing = self._documents.get(doc_id)
        self._documents[doc_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "embedding_vec": (
                existing["embedding_vec"] if existing is not None and embedding is None else embedding
            ),
            "embedded_at": (
                existing["embedded_at"] if existing is not None and embedded_at is None else embedded_at
            ),
            "source_updated_at": None if existing is None else existing["source_updated_at"],
        }

    def insert_retrieval(
        self,
        doc_id: str,
        query_hash: str,
        rank: int,
        score: float,
        retrieved_at: float,
    ) -> None:
        self._retrievals.append(
            {
                "doc_id": doc_id,
                "query_hash": query_hash,
                "rank": rank,
                "score": score,
                "retrieved_at": retrieved_at,
            }
        )

    def insert_engagement(
        self,
        doc_id: str,
        event_type: str,
        engaged_at: float,
    ) -> None:
        self._engagements.append(
            {
                "doc_id": doc_id,
                "event_type": event_type,
                "engaged_at": engaged_at,
            }
        )

    def update_source_timestamp(self, doc_id: str, updated_at: float) -> None:
        if doc_id not in self._documents:
            return

        document = self._documents[doc_id]
        self._documents[doc_id] = {
            "doc_id": document["doc_id"],
            "filename": document["filename"],
            "embedding_vec": document["embedding_vec"],
            "embedded_at": document["embedded_at"],
            "source_updated_at": updated_at,
        }

    def delete_document(self, doc_id: str) -> None:
        self._documents.pop(doc_id, None)
        self._retrievals = [
            event for event in self._retrievals if str(event["doc_id"]) != doc_id
        ]
        self._engagements = [
            event for event in self._engagements if str(event["doc_id"]) != doc_id
        ]

    def all_documents(self) -> list[DocumentRow]:
        return [document.copy() for document in self._documents.values()]

    def retrieval_counts(self, since: float) -> list[RetrievalRow]:
        aggregates: dict[str, dict[str, float | int]] = {}
        for event in self._retrievals:
            if float(event["retrieved_at"]) < since:
                continue

            doc_stats = aggregates.setdefault(
                str(event["doc_id"]),
                {"cnt": 0, "rank_total": 0.0, "score_total": 0.0},
            )
            doc_stats["cnt"] = int(doc_stats["cnt"]) + 1
            doc_stats["rank_total"] = float(doc_stats["rank_total"]) + float(event["rank"])
            doc_stats["score_total"] = float(doc_stats["score_total"]) + float(event["score"])

        return [
            {
                "doc_id": doc_id,
                "cnt": int(stats["cnt"]),
                "avg_rank": float(stats["rank_total"]) / int(stats["cnt"]) if int(stats["cnt"]) else None,
                "avg_score": float(stats["score_total"]) / int(stats["cnt"]) if int(stats["cnt"]) else None,
            }
            for doc_id, stats in aggregates.items()
        ]

    def engagement_counts(self, since: float) -> list[EngagementRow]:
        aggregates: dict[str, int] = {}
        for event in self._engagements:
            if float(event["engaged_at"]) < since:
                continue
            doc_id = str(event["doc_id"])
            aggregates[doc_id] = aggregates.get(doc_id, 0) + 1

        return [
            {"doc_id": doc_id, "cnt": count}
            for doc_id, count in aggregates.items()
        ]

    def all_embeddings(self) -> list[EmbeddingRow]:
        return [
            {
                "doc_id": document["doc_id"],
                "filename": document["filename"],
                "embedding_vec": document["embedding_vec"],
            }
            for document in self._documents.values()
            if document["embedding_vec"] is not None
        ]

    def close(self) -> None:
        self._closed = True
