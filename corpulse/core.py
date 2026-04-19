"""
corpulse  v0.1.0
Core public API — track, analyse, and report on your RAG corpus health.
"""

from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
from typing import Any, List, Set, Dict

import numpy as np

from .backends import SQLiteBackend, StorageBackend
from .models import (
    ReportRow, ReportSummary, CleanupPayload, GhostItem,
    DuplicatePair, ObsoleteItem, StaleItem, SuspectItem,
    CorpusHealth, DocumentRow, RetrievalRow, EngagementRow, QueryRow,
    LowConfidenceQueryRow, ZeroResultQueryRow,
    EmbeddingRow
)

try:
    from sklearn.metrics.pairwise import cosine_similarity
    _SKLEARN = True
except ImportError:
    _SKLEARN = False


# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _hash_query(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()[:16]


def _days_ago(days: int) -> float:
    return _now() - days * 86_400


def _ts_to_date(ts: float | None) -> str:
    if ts is None:
        return "—"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def _vec_to_bytes(vec) -> bytes:
    return np.array(vec, dtype=np.float32).tobytes()


def _bytes_to_vec(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)


_STATUS_ICON = {
    "ghost": "👻 ghost",
    "obsolete": "⚠  obsolete",
    "stale": "🕓 stale emb.",
    "low_engagement": "◌  low eng.",
    "healthy": "✓  healthy",
}


def _build_dataframe_rows(
    all_docs: List[DocumentRow],
    r_map: Dict[str, RetrievalRow],
    e_map: Dict[str, int],
    ghost_ids: Set[str],
    obsolete_ids: Set[str],
    stale_ids: Set[str],
) -> List[Dict[str, Any]]:
    rows = []
    for doc in all_docs:
        doc_id = doc["doc_id"]
        retrievals = r_map[doc_id]["cnt"] if doc_id in r_map else 0
        engagements = e_map.get(doc_id, 0)
        engagement_rate = round(engagements / retrievals, 2) if retrievals > 0 else 0.0

        # Preserve the existing dataframe path's rounded threshold behavior.
        if doc_id in ghost_ids:
            status = "ghost"
        elif doc_id in obsolete_ids:
            status = "obsolete"
        elif doc_id in stale_ids:
            status = "stale"
        elif retrievals > 0 and engagement_rate < 0.15:
            status = "low_engagement"
        else:
            status = "healthy"

        rows.append({
            "doc_id": doc_id,
            "filename": doc["filename"],
            "retrievals": retrievals,
            "engagements": engagements,
            "engagement_rate": engagement_rate,
            "status": status,
        })

    return rows


def _build_report_rows(
    all_docs: List[DocumentRow],
    r_map: Dict[str, RetrievalRow],
    e_map: Dict[str, int],
    ghost_ids: Set[str],
    obsolete_ids: Set[str],
    stale_ids: Set[str],
    top_k: int,
) -> List[ReportRow]:
    rows: List[ReportRow] = []
    for doc in sorted(
        all_docs,
        key=lambda d: r_map.get(d["doc_id"], {"cnt": 0})["cnt"],
        reverse=True,
    )[:top_k]:
        doc_id = doc["doc_id"]
        retrievals = r_map[doc_id]["cnt"] if doc_id in r_map else 0
        engagements = e_map.get(doc_id, 0)
        engagement_rate = f"{engagements / retrievals * 100:.0f}%" if retrievals > 0 else "—"

        # Preserve the existing report path's unrounded threshold behavior.
        if doc_id in ghost_ids:
            status = "ghost"
        elif doc_id in obsolete_ids:
            status = "obsolete"
        elif doc_id in stale_ids:
            status = "stale"
        elif retrievals > 0 and (e_map.get(doc_id, 0) / retrievals) < 0.15:
            status = "low_engagement"
        else:
            status = "healthy"

        rows.append({
            "filename": doc["filename"],
            "retrievals": retrievals,
            "engagement_rate": engagement_rate,
            "status": status,
            "status_display": _STATUS_ICON[status],
        })

    return rows


def _build_report_summary(
    all_docs: List[DocumentRow],
    window_days: int,
    health: CorpusHealth,
) -> ReportSummary:
    return {
        "total_docs": len(all_docs),
        "window_days": window_days,
        "bloat_warning": health["bloat_warning"],
        "noise_pct": health["noise_estimate"] * 100,
        "ghosts": health["ghosts"],
        "obsolete": health["obsolete"],
        "duplicates": health["duplicates"],
        "stale": health["stale"],
        "recommendation": health["recommendation"],
    }


def _build_cleanup_payload(
    health: CorpusHealth,
    ghosts: List[GhostItem],
    obsolete: List[ObsoleteItem],
    stale: List[StaleItem],
    suspects: List[SuspectItem],
    ghost_threshold_days: int,
) -> CleanupPayload:
    def _section(items: List[Any]) -> CleanupSection:
        return {
            "count": len(items),
            "top5": items[:5],
            "overflow": max(0, len(items) - 5),
        }

    return {
        "total_docs": health["total_docs"],
        "noise_pct": health["noise_estimate"] * 100,
        "bloat_warning": health["bloat_warning"],
        "recommendation": health["recommendation"],
        "ghost_threshold_days": ghost_threshold_days,
        "ghosts": _section(ghosts),
        "obsolete": _section(obsolete),
        "stale": _section(stale),
        "suspects": _section(suspects),
    }


def _build_ghosts(
    all_docs: List[DocumentRow],
    retrieval_rows: List[RetrievalRow],
) -> List[GhostItem]:
    recent_ids = {row["doc_id"] for row in retrieval_rows}
    return [
        {"doc_id": doc["doc_id"], "filename": doc["filename"]}
        for doc in all_docs
        if doc["doc_id"] not in recent_ids
    ]


def _build_duplicate_pairs(
    embedding_rows: List[EmbeddingRow],
    threshold: float,
) -> List[DuplicatePair]:
    if not _SKLEARN:
        raise RuntimeError(
            "scikit-learn is required for duplicate detection. "
            "Install it with: pip install scikit-learn"
        )

    if len(embedding_rows) < 2:
        return []

    ids = [row["doc_id"] for row in embedding_rows]
    names = [row["filename"] for row in embedding_rows]
    vecs = np.array([_bytes_to_vec(row["embedding_vec"]) for row in embedding_rows])

    sim_matrix = cosine_similarity(vecs)
    pairs: List[DuplicatePair] = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if sim_matrix[i, j] >= threshold:
                pairs.append({
                    "doc_id_a": ids[i],
                    "filename_a": names[i],
                    "doc_id_b": ids[j],
                    "filename_b": names[j],
                    "similarity": round(float(sim_matrix[i, j]), 4),
                })

    return sorted(pairs, key=lambda x: x["similarity"], reverse=True)


def _build_obsolete_documents(
    all_docs: List[DocumentRow],
    obsolete_pattern: str,
) -> List[ObsoleteItem]:
    pattern = re.compile(obsolete_pattern, re.IGNORECASE)

    groups: Dict[str, List[DocumentRow]] = {}
    for doc in all_docs:
        base = pattern.sub("", doc["filename"]).strip(" -_.")
        groups.setdefault(base, []).append(doc)

    obsolete: List[ObsoleteItem] = []
    for docs in groups.values():
        if len(docs) < 2:
            continue

        def _version(doc: DocumentRow) -> int:
            match = pattern.search(doc["filename"])
            nums = re.findall(r"\d+", match.group()) if match else []
            return int(nums[0]) if nums else 0

        sorted_docs = sorted(docs, key=_version)
        newest = sorted_docs[-1]
        for old in sorted_docs[:-1]:
            obsolete.append({
                "doc_id": old["doc_id"],
                "filename": old["filename"],
                "superseded_by": newest["filename"],
            })

    return obsolete


def _build_stale_embeddings(
    all_docs: List[DocumentRow],
    stale_threshold_days: int,
) -> List[StaleItem]:
    threshold_secs = stale_threshold_days * 86_400
    stale: List[StaleItem] = []
    for doc in all_docs:
        src = doc["source_updated_at"]
        emb = doc["embedded_at"]
        if src is None or emb is None:
            continue
        gap = src - emb
        if gap > threshold_secs:
            stale.append({
                "doc_id": doc["doc_id"],
                "filename": doc["filename"],
                "source_updated": _ts_to_date(src),
                "last_embedded": _ts_to_date(emb),
                "days_behind": int(gap // 86_400),
            })

    return sorted(stale, key=lambda x: x["days_behind"], reverse=True)


def _build_suspects(
    all_docs: List[DocumentRow],
    retrieval_rows: List[RetrievalRow],
    engagement_rows: List[EngagementRow],
) -> List[SuspectItem]:
    doc_map = {doc["doc_id"]: doc for doc in all_docs}
    retrieval_map = {row["doc_id"]: row for row in retrieval_rows}
    engagement_map = {row["doc_id"]: row["cnt"] for row in engagement_rows}

    suspects: List[SuspectItem] = []
    for doc_id, retrieval in retrieval_map.items():
        total_retrievals = retrieval["cnt"]
        if total_retrievals < 5:
            continue

        engagement_rate = engagement_map.get(doc_id, 0) / total_retrievals
        if engagement_rate < 0.15:
            doc = doc_map.get(doc_id)
            suspects.append({
                "doc_id": doc_id,
                "filename": doc["filename"] if doc else doc_id,
                "retrievals": total_retrievals,
                "engagement_rate": round(engagement_rate, 3),
            })

    return sorted(suspects, key=lambda x: x["retrievals"], reverse=True)


def _build_low_confidence_queries(
    query_rows: List[QueryRow],
    threshold: float,
) -> List[LowConfidenceQueryRow]:
    low_confidence = [
        row.copy()
        for row in query_rows
        if row["cnt"] > 0
        and row["max_score"] is not None
        and float(row["max_score"]) < threshold
    ]
    return sorted(
        low_confidence,
        key=lambda row: (
            float(row["max_score"]) if row["max_score"] is not None else float("inf"),
            -int(row["cnt"]),
            row["query_hash"],
        ),
    )


def _build_zero_result_queries(
    query_rows: List[QueryRow],
) -> List[ZeroResultQueryRow]:
    zero_result = [row.copy() for row in query_rows if int(row["cnt"]) == 0]
    return sorted(zero_result, key=lambda row: row["query_hash"])


def _build_query_rate(
    query_rows: List[QueryRow],
    filtered_rows: List[QueryRow],
) -> float:
    if not query_rows:
        return 0.0
    return round(len(filtered_rows) / len(query_rows), 2)


def _build_corpus_health(
    all_docs: List[DocumentRow],
    ghosts: List[GhostItem],
    obsolete: List[ObsoleteItem],
    stale: List[StaleItem],
    duplicate_pairs: List[DuplicatePair],
) -> CorpusHealth:
    total = len(all_docs)
    if total == 0:
        return {
            "total_docs": 0,
            "ghosts": 0,
            "obsolete": 0,
            "stale": 0,
            "duplicates": 0,
            "noise_estimate": 0.0,
            "bloat_warning": False,
            "recommendation": "Corpus looks healthy.",
        }

    ghost_ids = {doc["doc_id"] for doc in ghosts}
    obsolete_ids = {doc["doc_id"] for doc in obsolete}
    stale_ids = {doc["doc_id"] for doc in stale}
    duplicate_ids = {pair["doc_id_a"] for pair in duplicate_pairs} | {
        pair["doc_id_b"] for pair in duplicate_pairs
    }

    noisy_ids = ghost_ids | obsolete_ids | stale_ids | duplicate_ids
    noise_ratio = round(len(noisy_ids) / total, 2) if total > 0 else 0.0

    return {
        "total_docs": total,
        "ghosts": len(ghost_ids),
        "obsolete": len(obsolete_ids),
        "stale": len(stale_ids),
        "duplicates": len(duplicate_ids),
        "noise_estimate": noise_ratio,
        "bloat_warning": noise_ratio > 0.20,
        "recommendation": (
            f"Consider pruning ~{int(noise_ratio * total)} low-signal documents."
            if noise_ratio > 0.20 else "Corpus looks healthy."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Corpulse
# ─────────────────────────────────────────────────────────────────────────────

class Corpulse:
    """
    Lightweight RAG corpus analytics.

    Usage::

        corp = Corpulse()
        results = vectordb.search(query)
        corp.log_retrieval(results, query=query)
        corp.log_engagement("my-doc-id", event="opened")
        corp.report()
    """

    def __init__(
        self,
        db_path: str = "./corpulse.db",
        backend: StorageBackend | None = None,
        ghost_threshold_days: int = 30,
        duplicate_threshold: float = 0.92,
        stale_threshold_days: int = 14,
        obsolete_pattern: str = r"v\d+",
        top_k_report: int = 20,
        low_confidence_threshold: float = 0.8,
    ):
        """Initialise a Corpulse instance backed by a SQLite database.

        Args:
            db_path: Path to the SQLite database file. Created if it does
                not exist. Defaults to ``"./corpulse.db"``.
            backend: Explicit storage backend instance. When omitted,
                corpulse uses ``SQLiteBackend(db_path)``.
            ghost_threshold_days: Number of days without retrieval before a
                document is flagged as a ghost. Defaults to 30.
            duplicate_threshold: Cosine similarity threshold for duplicate
                detection. Pairs above this value are flagged. Defaults to 0.92.
            stale_threshold_days: Number of days of source-vs-embedding lag
                before an embedding is flagged as stale. Defaults to 14.
            obsolete_pattern: Regex pattern used to detect version tokens in
                filenames (e.g. ``v1``, ``v2``). Defaults to ``r"v\\d+"``.
            top_k_report: Maximum number of documents shown in ``report()``
                output. Defaults to 20.
            low_confidence_threshold: Top-score cutoff used by
                ``low_confidence_rate()`` and ``get_low_confidence_queries()``.
        """
        if backend is not None and db_path != "./corpulse.db":
            raise ValueError("Pass either the default db_path or an explicit backend, not both")

        self.db = backend if backend is not None else SQLiteBackend(db_path)
        self.ghost_threshold_days = ghost_threshold_days
        self.duplicate_threshold = duplicate_threshold
        self.stale_threshold_days = stale_threshold_days
        self.obsolete_pattern = obsolete_pattern
        self.top_k_report = top_k_report
        self.low_confidence_threshold = low_confidence_threshold

    def close(self) -> None:
        """Close the underlying storage backend."""
        self.db.close()

    def __enter__(self) -> Corpulse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ── ingestion ─────────────────────────────────────────────────────────────

    def log_retrieval(
        self,
        results: list[dict[str, Any]],
        query: str = "",
    ) -> None:
        """
        Call this right after your vector DB search.

        Each item in *results* must contain at least ``doc_id``.
        Optional keys: ``filename``, ``score`` (float), ``embedding`` (list/array).

        Example::

            results = [
                {"doc_id": "abc123", "filename": "guide.md", "score": 0.91},
                {"doc_id": "def456", "filename": "faq.md",   "score": 0.87},
            ]
            corp.log_retrieval(results, query="how to install?")

        Args:
            results: List of dicts, each containing at least ``"doc_id"``.
                Optional keys: ``"filename"``, ``"score"`` (float),
                ``"embedding"`` (list or numpy array).
            query: The search query string. Used for query deduplication
                via hashing. Defaults to ``""``.

        Returns:
            None.
        """
        qhash = _hash_query(query)
        ts = _now()

        for rank, item in enumerate(results, start=1):
            doc_id   = item["doc_id"]
            filename = item.get("filename", doc_id)
            score    = float(item.get("score", 0.0))
            vec      = item.get("embedding")

            self.db.upsert_document(
                doc_id=doc_id,
                filename=filename,
                embedding=_vec_to_bytes(vec) if vec is not None else None,
                embedded_at=ts if vec is not None else None,
            )
            self.db.insert_retrieval(doc_id, qhash, rank, score, ts)

    def log_engagement(
        self,
        doc_id: str,
        event: str = "opened",
    ) -> None:
        """
        Call this when a user acts on a retrieved document.

        *event* is a free-form label — e.g. "opened", "copied", "thumbs_up".

        Args:
            doc_id: Identifier of the document the user interacted with.
            event: Free-form label for the interaction type.
                Defaults to ``"opened"``.
        """
        self.db.insert_engagement(doc_id, event, _now())

    def log_source_update(
        self,
        doc_id: str,
        updated_at: float | None = None,
    ) -> None:
        """
        Notify corpulse that a source file was modified.

        *updated_at* defaults to now if omitted.

        Args:
            doc_id: Identifier of the document whose source was modified.
            updated_at: Unix timestamp of the modification. Defaults to
                the current time if ``None``.
        """
        self.db.update_source_timestamp(doc_id, updated_at or _now())

    def register_document(
        self,
        doc_id: str,
        filename: str,
        embedding: list | np.ndarray | None = None,
    ) -> None:
        """
        Optionally pre-register documents with their embeddings so duplicate
        detection works even before the first retrieval.

        Args:
            doc_id: Unique identifier for the document.
            filename: Human-readable filename or label.
            embedding: Optional embedding vector as a list or numpy array.
                When provided, enables duplicate detection for this document
                even before its first retrieval.
        """
        self.db.upsert_document(
            doc_id=doc_id,
            filename=filename,
            embedding=_vec_to_bytes(embedding) if embedding is not None else None,
            embedded_at=_now() if embedding is not None else None,
        )

    def delete_document(self, doc_id: str) -> None:
        """Delete a document and its associated retrieval and engagement history."""
        self.db.delete_document(doc_id)

    # ── analysis ──────────────────────────────────────────────────────────────

    def get_ghosts(self) -> List[GhostItem]:
        """Documents not retrieved in the last *ghost_threshold_days* days.

        Returns:
            List of dicts with keys: ``doc_id``, ``filename``.
        """
        cutoff = _days_ago(self.ghost_threshold_days)
        all_docs = self.db.all_documents()
        retrieval_rows = self.db.retrieval_counts(since=cutoff)
        return _build_ghosts(all_docs, retrieval_rows)

    def get_duplicates(
        self,
        threshold: float | None = None,
    ) -> List[DuplicatePair]:
        """
        Pairs of documents whose embedding vectors are cosine-similar above
        *threshold* — likely redundant content competing for the same queries.

        Requires scikit-learn and stored embeddings.

        Args:
            threshold: Cosine similarity threshold above which documents are
                considered duplicates. Defaults to ``duplicate_threshold``
                if ``None``.

        Returns:
            List of dicts with keys: ``doc_id_a``, ``filename_a``,
            ``doc_id_b``, ``filename_b``, ``similarity`` (float).
            Sorted by similarity descending.

        Raises:
            RuntimeError: If scikit-learn is not installed.
        """
        threshold = threshold or self.duplicate_threshold
        rows = self.db.all_embeddings()
        return _build_duplicate_pairs(rows, threshold)

    def get_obsolete(self) -> List[ObsoleteItem]:
        """
        Documents likely superseded by a newer version of the same file,
        detected via the *obsolete_pattern* (default: version numbers like v1, v2).

        e.g. if both "api-reference-v1.md" and "api-reference-v2.md" exist,
        v1 is flagged as obsolete.

        Returns:
            List of dicts with keys: ``doc_id``, ``filename``,
            ``superseded_by`` (filename of the newer version).
        """
        all_docs = self.db.all_documents()
        return _build_obsolete_documents(all_docs, self.obsolete_pattern)

    def get_stale_embeddings(self) -> List[StaleItem]:
        """
        Documents where the source file was updated more than
        *stale_threshold_days* days after the last embedding.

        Returns:
            List of dicts with keys: ``doc_id``, ``filename``,
            ``source_updated`` (date string), ``last_embedded`` (date string),
            ``days_behind`` (int). Sorted by days_behind descending.
        """
        all_docs = self.db.all_documents()
        return _build_stale_embeddings(all_docs, self.stale_threshold_days)

    def get_suspects(self, window_days: int | None = None) -> List[SuspectItem]:
        """
        Documents with high retrieval count but low engagement rate —
        retrieved often but users don't act on them. Good re-chunking candidates.

        Args:
            window_days: Lookback window in days. Defaults to
                ``ghost_threshold_days`` if ``None``.

        Returns:
            List of dicts with keys: ``doc_id``, ``filename``,
            ``retrievals`` (int), ``engagement_rate`` (float 0-1).
            Sorted by retrievals descending.
        """
        since = _days_ago(window_days or self.ghost_threshold_days)
        all_docs = self.db.all_documents()
        retrieval_rows = self.db.retrieval_counts(since=since)
        engagement_rows = self.db.engagement_counts(since=since)
        return _build_suspects(all_docs, retrieval_rows, engagement_rows)

    def _query_rows(self, window_days: int | None = None) -> List[QueryRow]:
        since = _days_ago(window_days or self.ghost_threshold_days)
        return self.db.query_counts(since=since)

    def low_confidence_rate(
        self,
        window_days: int | None = None,
        threshold: float | None = None,
    ) -> float:
        """Return the share of queries whose top score falls below *threshold*."""
        query_rows = self._query_rows(window_days)
        confidence_threshold = threshold if threshold is not None else self.low_confidence_threshold
        low_confidence_rows = _build_low_confidence_queries(query_rows, confidence_threshold)
        return _build_query_rate(
            [row for row in query_rows if int(row["cnt"]) > 0],
            low_confidence_rows,
        )

    def get_low_confidence_queries(
        self,
        window_days: int | None = None,
        threshold: float | None = None,
    ) -> List[LowConfidenceQueryRow]:
        """Return query aggregates whose top score falls below *threshold*."""
        query_rows = self._query_rows(window_days)
        confidence_threshold = threshold if threshold is not None else self.low_confidence_threshold
        return _build_low_confidence_queries(query_rows, confidence_threshold)

    def zero_result_rate(self, window_days: int | None = None) -> float:
        """Return the share of query aggregates recorded with zero results."""
        query_rows = self._query_rows(window_days)
        zero_result_rows = _build_zero_result_queries(query_rows)
        return _build_query_rate(query_rows, zero_result_rows)

    def get_zero_result_queries(
        self,
        window_days: int | None = None,
    ) -> List[ZeroResultQueryRow]:
        """Return query aggregates recorded with zero results."""
        query_rows = self._query_rows(window_days)
        return _build_zero_result_queries(query_rows)

    def corpus_health(self) -> CorpusHealth:
        """
        High-level corpus noise estimate and bloat warning.

        Returns:
            Dict with keys: ``total_docs`` (int), ``ghosts`` (int),
            ``obsolete`` (int), ``stale`` (int), ``duplicates`` (int),
            ``noise_estimate`` (float 0-1), ``bloat_warning`` (bool),
            ``recommendation`` (str).
        """
        all_docs = self.db.all_documents()
        ghosts = self.get_ghosts()
        obsolete = self.get_obsolete()
        stale = self.get_stale_embeddings()
        duplicate_pairs: List[DuplicatePair] = []
        if _SKLEARN:
            duplicate_pairs = self.get_duplicates()
        return _build_corpus_health(all_docs, ghosts, obsolete, stale, duplicate_pairs)

    # ── reporting ─────────────────────────────────────────────────────────────

    def to_dataframe(self, window_days: int | None = None):
        """Return corpus stats as a pandas DataFrame.

        Args:
            window_days: Lookback window in days for retrieval/engagement
                counts. Defaults to ``ghost_threshold_days`` if ``None``.

        Returns:
            pandas.DataFrame with columns: ``doc_id``, ``filename``,
            ``retrievals``, ``engagements``, ``engagement_rate``, ``status``.
            Sorted by retrievals descending.

        Raises:
            RuntimeError: If pandas is not installed.
        """
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("pip install pandas to use to_dataframe()")

        since  = _days_ago(window_days or self.ghost_threshold_days)
        r_map  = {r["doc_id"]: r for r in self.db.retrieval_counts(since=since)}
        e_map  = {e["doc_id"]: e["cnt"] for e in self.db.engagement_counts(since=since)}
        ghosts = {d["doc_id"] for d in self.get_ghosts()}
        obs    = {d["doc_id"] for d in self.get_obsolete()}
        stale  = {d["doc_id"] for d in self.get_stale_embeddings()}
        rows = _build_dataframe_rows(
            self.db.all_documents(),
            r_map,
            e_map,
            ghosts,
            obs,
            stale,
        )

        return pd.DataFrame(rows).sort_values("retrievals", ascending=False)

    def cleanup_report(self) -> None:
        """Print a prioritised, human-readable action list.

        Prints sections for ghosts, obsolete documents, stale embeddings,
        and re-chunk candidates with counts and top-5 examples in each
        category.

        Returns:
            None. Output is printed to stdout.
        """
        health   = self.corpus_health()
        ghosts   = self.get_ghosts()
        obsolete = self.get_obsolete()
        stale    = self.get_stale_embeddings()
        suspects = self.get_suspects()
        payload = _build_cleanup_payload(
            health,
            ghosts,
            obsolete,
            stale,
            suspects,
            self.ghost_threshold_days,
        )

        print("\n" + "─" * 60)
        print("  corpulse — Cleanup Report")
        print("─" * 60)
        print(f"  Total documents : {payload['total_docs']}")
        print(f"  Noise estimate  : {payload['noise_pct']:.0f}%")
        if payload["bloat_warning"]:
            print(f"  ⚠  {payload['recommendation']}")
        print()

        if ghosts:
            print(f"  👻  GHOSTS  ({payload['ghosts']['count']} docs — never retrieved in "
                  f"{payload['ghost_threshold_days']}d)")
            for g in payload["ghosts"]["top5"]:
                print(f"      · {g['filename']}")
            if payload["ghosts"]["overflow"] > 0:
                print(f"      … and {payload['ghosts']['overflow']} more")
            print()

        if obsolete:
            print(f"  💀  OBSOLETE  ({payload['obsolete']['count']} docs)")
            for o in payload["obsolete"]["top5"]:
                print(f"      · {o['filename']}  →  superseded by {o['superseded_by']}")
            if payload["obsolete"]["overflow"] > 0:
                print(f"      … and {payload['obsolete']['overflow']} more")
            print()

        if stale:
            print(f"  🕓  STALE EMBEDDINGS  ({payload['stale']['count']} docs)")
            for s in payload["stale"]["top5"]:
                print(f"      · {s['filename']}  "
                      f"({s['days_behind']}d behind — "
                      f"source {s['source_updated']}, embedded {s['last_embedded']})")
            if payload["stale"]["overflow"] > 0:
                print(f"      … and {payload['stale']['overflow']} more")
            print()

        if suspects:
            print(f"  🔁  RE-CHUNK CANDIDATES  ({payload['suspects']['count']} docs — high retrieval, low engagement)")
            for s in payload["suspects"]["top5"]:
                print(f"      · {s['filename']}  "
                      f"({s['retrievals']} retrievals, {s['engagement_rate']*100:.0f}% engagement)")
            if payload["suspects"]["overflow"] > 0:
                print(f"      … and {payload['suspects']['overflow']} more")
            print()

        print("─" * 60 + "\n")

    def report(self, window_days: int | None = None) -> None:
        """Print the full corpus health table to stdout.

        Uses tabulate for pretty-printing if installed, falls back to
        plain-text columns otherwise.

        Args:
            window_days: Lookback window in days for retrieval and
                engagement counts. Defaults to ``ghost_threshold_days``
                if ``None``.

        Returns:
            None. Output is printed to stdout.
        """
        try:
            from tabulate import tabulate
            _tabulate = True
        except ImportError:
            _tabulate = False

        since    = _days_ago(window_days or self.ghost_threshold_days)
        all_docs = self.db.all_documents()
        r_map    = {r["doc_id"]: r for r in self.db.retrieval_counts(since=since)}
        e_map    = {e["doc_id"]: e["cnt"] for e in self.db.engagement_counts(since=since)}
        ghosts   = {d["doc_id"] for d in self.get_ghosts()}
        obs      = {d["doc_id"] for d in self.get_obsolete()}
        stale    = {d["doc_id"] for d in self.get_stale_embeddings()}
        health = self.corpus_health()
        rows = _build_report_rows(
            all_docs,
            r_map,
            e_map,
            ghosts,
            obs,
            stale,
            self.top_k_report,
        )
        summary = _build_report_summary(
            all_docs,
            window_days or self.ghost_threshold_days,
            health,
        )
        table_rows = [
            [row["filename"], row["retrievals"], row["engagement_rate"], row["status_display"]]
            for row in rows
        ]
        header = (
            f"\n  corpulse — Corpus Health Report\n"
            f"  {summary['total_docs']} documents · last {summary['window_days']} days"
        )
        if summary["bloat_warning"]:
            header += f" · ⚠ corpus bloat detected ({summary['noise_pct']:.0f}% noise est.)"

        print(header)
        if _tabulate:
            print(tabulate(table_rows,
                           headers=["Document", "Retrieved", "Engagement", "Status"],
                           tablefmt="rounded_outline"))
        else:
            print(f"  {'Document':<35} {'Retrieved':>10} {'Engagement':>12}  Status")
            print("  " + "─" * 70)
            for r in table_rows:
                print(f"  {r[0]:<35} {r[1]:>10} {r[2]:>12}  {r[3]}")

        print(f"\n  👻 ghosts: {summary['ghosts']}  "
              f"💀 obsolete: {summary['obsolete']}  "
              f"⚠ duplicates: {summary['duplicates']}  "
              f"🕓 stale: {summary['stale']}")
        print(f"  Run corpulse.cleanup_report() for a prioritised action list.\n")
