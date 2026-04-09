from __future__ import annotations

from typing import Any

import numpy as np

from .core import _days_ago, _hash_query, _now, _vec_to_bytes


class AsyncCorpulse:
    def __init__(
        self,
        backend,
        ghost_threshold_days: int = 30,
        duplicate_threshold: float = 0.92,
        stale_threshold_days: int = 14,
        obsolete_pattern: str = r"v\d+",
        top_k_report: int = 20,
    ):
        self.db = backend
        self.ghost_threshold_days = ghost_threshold_days
        self.duplicate_threshold = duplicate_threshold
        self.stale_threshold_days = stale_threshold_days
        self.obsolete_pattern = obsolete_pattern
        self.top_k_report = top_k_report

    async def log_retrieval(
        self,
        results: list[dict[str, Any]],
        query: str = "",
    ) -> None:
        qhash = _hash_query(query)
        ts = _now()

        for rank, item in enumerate(results, start=1):
            doc_id = item["doc_id"]
            filename = item.get("filename", doc_id)
            score = float(item.get("score", 0.0))
            vec = item.get("embedding")

            await self.db.upsert_document(
                doc_id=doc_id,
                filename=filename,
                embedding=_vec_to_bytes(vec) if vec is not None else None,
                embedded_at=ts if vec is not None else None,
            )
            await self.db.insert_retrieval(doc_id, qhash, rank, score, ts)

    async def log_engagement(
        self,
        doc_id: str,
        event: str = "opened",
    ) -> None:
        await self.db.insert_engagement(doc_id, event, _now())

    async def log_source_update(
        self,
        doc_id: str,
        updated_at: float | None = None,
    ) -> None:
        await self.db.update_source_timestamp(doc_id, updated_at or _now())

    async def register_document(
        self,
        doc_id: str,
        filename: str,
        embedding: list | np.ndarray | None = None,
    ) -> None:
        await self.db.upsert_document(
            doc_id=doc_id,
            filename=filename,
            embedding=_vec_to_bytes(embedding) if embedding is not None else None,
            embedded_at=_now() if embedding is not None else None,
        )

    async def get_ghosts(self) -> list[dict]:
        cutoff = _days_ago(self.ghost_threshold_days)
        recent_ids = {
            row["doc_id"]
            for row in await self.db.retrieval_counts(since=cutoff)
        }
        all_docs = await self.db.all_documents()
        return [
            {"doc_id": doc["doc_id"], "filename": doc["filename"]}
            for doc in all_docs
            if doc["doc_id"] not in recent_ids
        ]

    async def close(self) -> None:
        await self.db.close()

    async def __aenter__(self) -> AsyncCorpulse:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
