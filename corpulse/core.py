"""
corpulse  v0.1.0
Core public API — track, analyse, and report on your RAG corpus health.
"""

from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np

from .backends import SQLiteBackend, StorageBackend

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


def _build_ghosts(
    all_docs: list[dict[str, Any]],
    retrieval_rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    recent_ids = {row["doc_id"] for row in retrieval_rows}
    return [
        {"doc_id": doc["doc_id"], "filename": doc["filename"]}
        for doc in all_docs
        if doc["doc_id"] not in recent_ids
    ]


def _build_duplicate_pairs(
    embedding_rows: list[dict[str, Any]],
    threshold: float,
) -> list[dict[str, Any]]:
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
    pairs = []
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
    all_docs: list[dict[str, Any]],
    obsolete_pattern: str,
) -> list[dict[str, str]]:
    pattern = re.compile(obsolete_pattern, re.IGNORECASE)

    groups: dict[str, list[dict[str, Any]]] = {}
    for doc in all_docs:
        base = pattern.sub("", doc["filename"]).strip(" -_.")
        groups.setdefault(base, []).append(doc)

    obsolete = []
    for docs in groups.values():
        if len(docs) < 2:
            continue

        def _version(doc: dict[str, Any]) -> int:
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
    all_docs: list[dict[str, Any]],
    stale_threshold_days: int,
) -> list[dict[str, Any]]:
    threshold_secs = stale_threshold_days * 86_400
    stale = []
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
    all_docs: list[dict[str, Any]],
    retrieval_rows: list[dict[str, Any]],
    engagement_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    doc_map = {doc["doc_id"]: doc for doc in all_docs}
    retrieval_map = {row["doc_id"]: row for row in retrieval_rows}
    engagement_map = {row["doc_id"]: row["cnt"] for row in engagement_rows}

    suspects = []
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


def _build_corpus_health(
    all_docs: list[dict[str, Any]],
    ghosts: list[dict[str, Any]],
    obsolete: list[dict[str, Any]],
    stale: list[dict[str, Any]],
    duplicate_pairs: list[dict[str, Any]],
) -> dict[str, Any]:
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
        """
        if backend is not None and db_path != "./corpulse.db":
            raise ValueError("Pass either the default db_path or an explicit backend, not both")

        self.db = backend if backend is not None else SQLiteBackend(db_path)
        self.ghost_threshold_days = ghost_threshold_days
        self.duplicate_threshold = duplicate_threshold
        self.stale_threshold_days = stale_threshold_days
        self.obsolete_pattern = obsolete_pattern
        self.top_k_report = top_k_report

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

    # ── analysis ──────────────────────────────────────────────────────────────

    def get_ghosts(self) -> list[dict]:
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
    ) -> list[dict]:
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

    def get_obsolete(self) -> list[dict]:
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

    def get_stale_embeddings(self) -> list[dict]:
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

    def get_suspects(self, window_days: int | None = None) -> list[dict]:
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

    def corpus_health(self) -> dict:
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
        duplicate_pairs: list[dict[str, Any]] = []
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

        rows = []
        for doc in self.db.all_documents():
            did  = doc["doc_id"]
            ret  = r_map[did]["cnt"] if did in r_map else 0
            eng  = e_map.get(did, 0)
            rate = round(eng / ret, 2) if ret > 0 else 0.0

            if did in ghosts:   status = "ghost"
            elif did in obs:    status = "obsolete"
            elif did in stale:  status = "stale"
            elif ret > 0 and rate < 0.15: status = "low_engagement"
            else:               status = "healthy"

            rows.append({
                "doc_id":          did,
                "filename":        doc["filename"],
                "retrievals":      ret,
                "engagements":     eng,
                "engagement_rate": rate,
                "status":          status,
            })

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

        print("\n" + "─" * 60)
        print("  corpulse — Cleanup Report")
        print("─" * 60)
        print(f"  Total documents : {health['total_docs']}")
        print(f"  Noise estimate  : {health['noise_estimate']*100:.0f}%")
        if health["bloat_warning"]:
            print(f"  ⚠  {health['recommendation']}")
        print()

        if ghosts:
            print(f"  👻  GHOSTS  ({len(ghosts)} docs — never retrieved in "
                  f"{self.ghost_threshold_days}d)")
            for g in ghosts[:5]:
                print(f"      · {g['filename']}")
            if len(ghosts) > 5:
                print(f"      … and {len(ghosts)-5} more")
            print()

        if obsolete:
            print(f"  💀  OBSOLETE  ({len(obsolete)} docs)")
            for o in obsolete[:5]:
                print(f"      · {o['filename']}  →  superseded by {o['superseded_by']}")
            if len(obsolete) > 5:
                print(f"      … and {len(obsolete)-5} more")
            print()

        if stale:
            print(f"  🕓  STALE EMBEDDINGS  ({len(stale)} docs)")
            for s in stale[:5]:
                print(f"      · {s['filename']}  "
                      f"({s['days_behind']}d behind — "
                      f"source {s['source_updated']}, embedded {s['last_embedded']})")
            if len(stale) > 5:
                print(f"      … and {len(stale)-5} more")
            print()

        if suspects:
            print(f"  🔁  RE-CHUNK CANDIDATES  ({len(suspects)} docs — high retrieval, low engagement)")
            for s in suspects[:5]:
                print(f"      · {s['filename']}  "
                      f"({s['retrievals']} retrievals, {s['engagement_rate']*100:.0f}% engagement)")
            if len(suspects) > 5:
                print(f"      … and {len(suspects)-5} more")
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
        total    = len(all_docs)
        r_map    = {r["doc_id"]: r for r in self.db.retrieval_counts(since=since)}
        e_map    = {e["doc_id"]: e["cnt"] for e in self.db.engagement_counts(since=since)}
        ghosts   = {d["doc_id"] for d in self.get_ghosts()}
        obs      = {d["doc_id"] for d in self.get_obsolete()}
        stale    = {d["doc_id"] for d in self.get_stale_embeddings()}

        STATUS_ICON = {
            "ghost":          "👻 ghost",
            "obsolete":       "⚠  obsolete",
            "stale":          "🕓 stale emb.",
            "low_engagement": "◌  low eng.",
            "healthy":        "✓  healthy",
        }

        rows = []
        for doc in sorted(all_docs,
                          key=lambda d: r_map.get(d["doc_id"], {"cnt": 0})["cnt"],
                          reverse=True)[: self.top_k_report]:
            did = doc["doc_id"]
            ret = r_map[did]["cnt"] if did in r_map else 0
            eng = e_map.get(did, 0)
            rate = f"{eng/ret*100:.0f}%" if ret > 0 else "—"

            if did in ghosts:   status = "ghost"
            elif did in obs:    status = "obsolete"
            elif did in stale:  status = "stale"
            elif ret > 0 and (e_map.get(did, 0) / ret) < 0.15:
                                status = "low_engagement"
            else:               status = "healthy"

            rows.append([doc["filename"], ret, rate, STATUS_ICON[status]])

        health = self.corpus_health()
        header = (
            f"\n  corpulse — Corpus Health Report\n"
            f"  {total} documents · last {window_days or self.ghost_threshold_days} days"
        )
        if health["bloat_warning"]:
            header += f" · ⚠ corpus bloat detected ({health['noise_estimate']*100:.0f}% noise est.)"

        print(header)
        if _tabulate:
            print(tabulate(rows,
                           headers=["Document", "Retrieved", "Engagement", "Status"],
                           tablefmt="rounded_outline"))
        else:
            print(f"  {'Document':<35} {'Retrieved':>10} {'Engagement':>12}  Status")
            print("  " + "─" * 70)
            for r in rows:
                print(f"  {r[0]:<35} {r[1]:>10} {r[2]:>12}  {r[3]}")

        print(f"\n  👻 ghosts: {health['ghosts']}  "
              f"💀 obsolete: {health['obsolete']}  "
              f"⚠ duplicates: {health['duplicates']}  "
              f"🕓 stale: {health['stale']}")
        print(f"  Run corpulse.cleanup_report() for a prioritised action list.\n")
