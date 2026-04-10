from __future__ import annotations

from typing import Any

import numpy as np

from .core import (
    _SKLEARN,
    _build_corpus_health,
    _build_dataframe_rows,
    _build_duplicate_pairs,
    _build_ghosts,
    _build_obsolete_documents,
    _build_stale_embeddings,
    _build_suspects,
    _days_ago,
    _hash_query,
    _now,
    _vec_to_bytes,
)


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
        retrieval_rows = await self.db.retrieval_counts(since=cutoff)
        all_docs = await self.db.all_documents()
        return _build_ghosts(all_docs, retrieval_rows)

    async def get_duplicates(
        self,
        threshold: float | None = None,
    ) -> list[dict]:
        duplicate_threshold = threshold or self.duplicate_threshold
        embedding_rows = await self.db.all_embeddings()
        return _build_duplicate_pairs(embedding_rows, duplicate_threshold)

    async def get_obsolete(self) -> list[dict]:
        all_docs = await self.db.all_documents()
        return _build_obsolete_documents(all_docs, self.obsolete_pattern)

    async def get_stale_embeddings(self) -> list[dict]:
        all_docs = await self.db.all_documents()
        return _build_stale_embeddings(all_docs, self.stale_threshold_days)

    async def get_suspects(self, window_days: int | None = None) -> list[dict]:
        since = _days_ago(window_days or self.ghost_threshold_days)
        all_docs = await self.db.all_documents()
        retrieval_rows = await self.db.retrieval_counts(since=since)
        engagement_rows = await self.db.engagement_counts(since=since)
        return _build_suspects(all_docs, retrieval_rows, engagement_rows)

    async def corpus_health(self) -> dict:
        all_docs = await self.db.all_documents()
        if not all_docs:
            return _build_corpus_health([], [], [], [], [])

        ghosts = await self.get_ghosts()
        obsolete = await self.get_obsolete()
        stale = await self.get_stale_embeddings()
        duplicate_pairs: list[dict[str, Any]] = []
        if _SKLEARN:
            duplicate_pairs = await self.get_duplicates()

        return _build_corpus_health(
            all_docs,
            ghosts,
            obsolete,
            stale,
            duplicate_pairs,
        )

    async def to_dataframe(self, window_days: int | None = None):
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("pip install pandas to use to_dataframe()")

        since = _days_ago(window_days or self.ghost_threshold_days)
        all_docs = await self.db.all_documents()
        retrieval_rows = await self.db.retrieval_counts(since=since)
        engagement_rows = await self.db.engagement_counts(since=since)
        ghost_ids = {doc["doc_id"] for doc in await self.get_ghosts()}
        obsolete_ids = {doc["doc_id"] for doc in await self.get_obsolete()}
        stale_ids = {doc["doc_id"] for doc in await self.get_stale_embeddings()}
        rows = _build_dataframe_rows(
            all_docs,
            {row["doc_id"]: row for row in retrieval_rows},
            {row["doc_id"]: row["cnt"] for row in engagement_rows},
            ghost_ids,
            obsolete_ids,
            stale_ids,
        )
        return pd.DataFrame(rows).sort_values("retrievals", ascending=False)

    async def close(self) -> None:
        await self.db.close()

    async def __aenter__(self) -> AsyncCorpulse:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
