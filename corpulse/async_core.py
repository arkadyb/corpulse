from __future__ import annotations

from typing import Any, List

import numpy as np

from .core import (
    _SKLEARN,
    _build_cleanup_payload,
    _build_corpus_health,
    _build_dataframe_rows,
    _build_duplicate_pairs,
    _build_ghosts,
    _build_obsolete_documents,
    _build_report_rows,
    _build_report_summary,
    _build_stale_embeddings,
    _build_suspects,
    _days_ago,
    _hash_query,
    _now,
    _vec_to_bytes,
)
from .models import (
    ReportPayload, CleanupPayload, GhostItem, DuplicatePair,
    ObsoleteItem, StaleItem, SuspectItem, CorpusHealth
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
        """Record a retrieval event batch for ranked search results.

        Async equivalent of :meth:`Corpulse.log_retrieval`.

        Args:
            results: Retrieved document records. Each item must include
                ``doc_id`` and may include ``filename``, ``score``, and
                ``embedding``.
            query: Raw user query text used to derive the stored query hash.

        Returns:
            None.
        """
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
        """Record a user engagement event for a document.

        Async equivalent of :meth:`Corpulse.log_engagement`.

        Args:
            doc_id: Document identifier tied to the engagement.
            event: Engagement type such as ``"opened"`` or ``"clicked"``.

        Returns:
            None.
        """
        await self.db.insert_engagement(doc_id, event, _now())

    async def log_source_update(
        self,
        doc_id: str,
        updated_at: float | None = None,
    ) -> None:
        """Mark a document source as updated.

        Async equivalent of :meth:`Corpulse.log_source_update`.

        Args:
            doc_id: Document identifier whose source changed.
            updated_at: Unix timestamp for the source update. Defaults to
                the current time if omitted.

        Returns:
            None.
        """
        await self.db.update_source_timestamp(doc_id, updated_at or _now())

    async def register_document(
        self,
        doc_id: str,
        filename: str,
        embedding: list | np.ndarray | None = None,
    ) -> None:
        """Register or update a document in the corpus.

        Async equivalent of :meth:`Corpulse.register_document`.

        Args:
            doc_id: Stable document identifier.
            filename: Human-readable document name shown in reports.
            embedding: Optional embedding vector to persist with the
                document.

        Returns:
            None.
        """
        await self.db.upsert_document(
            doc_id=doc_id,
            filename=filename,
            embedding=_vec_to_bytes(embedding) if embedding is not None else None,
            embedded_at=_now() if embedding is not None else None,
        )

    async def delete_document(self, doc_id: str) -> None:
        """Delete a document and its associated retrieval and engagement history."""
        await self.db.delete_document(doc_id)

    async def get_ghosts(self) -> List[GhostItem]:
        """Return documents not retrieved within the ghost threshold window.

        Async equivalent of :meth:`Corpulse.get_ghosts`.

        Returns:
            List[GhostItem]: Ghost document records with identifiers and filenames.
        """
        cutoff = _days_ago(self.ghost_threshold_days)
        retrieval_rows = await self.db.retrieval_counts(since=cutoff)
        all_docs = await self.db.all_documents()
        return _build_ghosts(all_docs, retrieval_rows)

    async def get_duplicates(
        self,
        threshold: float | None = None,
    ) -> List[DuplicatePair]:
        """Return near-duplicate document pairs by cosine similarity.

        Async equivalent of :meth:`Corpulse.get_duplicates`.

        Args:
            threshold: Optional cosine-similarity cutoff. Defaults to
                ``duplicate_threshold`` if omitted.

        Returns:
            List[DuplicatePair]: Duplicate-pair records with filenames and similarity.
        """
        duplicate_threshold = threshold or self.duplicate_threshold
        embedding_rows = await self.db.all_embeddings()
        return _build_duplicate_pairs(embedding_rows, duplicate_threshold)

    async def get_obsolete(self) -> List[ObsoleteItem]:
        """Return documents superseded by newer versioned filenames.

        Async equivalent of :meth:`Corpulse.get_obsolete`.

        Returns:
            List[ObsoleteItem]: Obsolete document records with replacement metadata.
        """
        all_docs = await self.db.all_documents()
        return _build_obsolete_documents(all_docs, self.obsolete_pattern)

    async def get_stale_embeddings(self) -> List[StaleItem]:
        """Return documents whose source is newer than their embedding.

        Async equivalent of :meth:`Corpulse.get_stale_embeddings`.

        Returns:
            List[StaleItem]: Stale-embedding records including lag details.
        """
        all_docs = await self.db.all_documents()
        return _build_stale_embeddings(all_docs, self.stale_threshold_days)

    async def get_suspects(self, window_days: int | None = None) -> List[SuspectItem]:
        """Return high-retrieval, low-engagement suspect documents.

        Async equivalent of :meth:`Corpulse.get_suspects`.

        Args:
            window_days: Lookback window in days for retrieval and
                engagement counts. Defaults to ``ghost_threshold_days``
                if ``None``.

        Returns:
            List[SuspectItem]: Suspect document records with retrieval and
            engagement metrics.
        """
        since = _days_ago(window_days or self.ghost_threshold_days)
        all_docs = await self.db.all_documents()
        retrieval_rows = await self.db.retrieval_counts(since=since)
        engagement_rows = await self.db.engagement_counts(since=since)
        return _build_suspects(all_docs, retrieval_rows, engagement_rows)

    async def corpus_health(self) -> CorpusHealth:
        """Return aggregate corpus-health metrics.

        Async equivalent of :meth:`Corpulse.corpus_health`.

        Returns:
            CorpusHealth: Summary metrics including noise estimate, counts, and
            bloat recommendation fields.
        """
        all_docs = await self.db.all_documents()
        if not all_docs:
            return _build_corpus_health([], [], [], [], [])

        ghosts = await self.get_ghosts()
        obsolete = await self.get_obsolete()
        stale = await self.get_stale_embeddings()
        duplicate_pairs: List[DuplicatePair] = []
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
        """Return corpus stats as a pandas DataFrame.

        Async equivalent of :meth:`Corpulse.to_dataframe`. Retrieval and
        engagement counts are fetched from the async backend before building
        the DataFrame.

        Args:
            window_days: Lookback window in days for retrieval/engagement
                counts. Defaults to ``ghost_threshold_days`` if ``None``.

        Returns:
            pandas.DataFrame with columns: ``doc_id``, ``filename``,
            ``retrievals``, ``engagements``, ``engagement_rate``, ``status``.
            Sorted by retrievals descending.

        Raises:
            RuntimeError: If pandas is not installed
                (``pip install pandas`` to resolve).
        """
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

    async def cleanup_report(self) -> CleanupPayload:
        """Return a structured cleanup action payload.

        Unlike sync :meth:`Corpulse.cleanup_report` which prints to stdout,
        this method returns the payload as a dict so callers can format, log,
        or forward it.

        MODEL-04: This method is analysis-only and does not mutate document data.
        It only calls read-only analysis methods and pure payload builders.

        Returns:
            CleanupPayload with sections for ghosts, obsolete, stale, and suspects.
        """
        health = await self.corpus_health()
        ghosts = await self.get_ghosts()
        obsolete = await self.get_obsolete()
        stale = await self.get_stale_embeddings()
        suspects = await self.get_suspects()
        return _build_cleanup_payload(
            health,
            ghosts,
            obsolete,
            stale,
            suspects,
            self.ghost_threshold_days,
        )

    async def report(self, window_days: int | None = None) -> ReportPayload:
        """Return a structured corpus health payload.

        Unlike sync :meth:`Corpulse.report` which prints to stdout, this method
        returns the payload as a dict so callers can format, log, or forward it.

        Args:
            window_days: Lookback window in days for retrieval and engagement
                counts. Defaults to ``ghost_threshold_days`` if ``None``.

        Returns:
            ReportPayload containing summary metrics and document rows.
        """
        report_window_days = window_days or self.ghost_threshold_days
        since = _days_ago(report_window_days)
        all_docs = await self.db.all_documents()
        retrieval_rows = await self.db.retrieval_counts(since=since)
        engagement_rows = await self.db.engagement_counts(since=since)
        ghosts = await self.get_ghosts()
        obsolete = await self.get_obsolete()
        stale = await self.get_stale_embeddings()
        health = await self.corpus_health()
        return {
            "summary": _build_report_summary(
                all_docs,
                report_window_days,
                health,
            ),
            "rows": _build_report_rows(
                all_docs,
                {row["doc_id"]: row for row in retrieval_rows},
                {row["doc_id"]: row["cnt"] for row in engagement_rows},
                {row["doc_id"] for row in ghosts},
                {row["doc_id"] for row in obsolete},
                {row["doc_id"] for row in stale},
                self.top_k_report,
            ),
        }

    async def close(self) -> None:
        """Close the underlying async backend.

        Returns:
            None.
        """
        await self.db.close()

    async def __aenter__(self) -> AsyncCorpulse:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
