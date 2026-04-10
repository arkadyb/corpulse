from __future__ import annotations

from typing import Any

import numpy as np

from corpulse.backends.memory import InMemoryBackend
from corpulse.core import (
    Corpulse,
    _build_cleanup_payload,
    _build_report_rows,
    _build_report_summary,
    _vec_to_bytes,
)

FROZEN = 1_700_000_000.0
_DAY = 86_400


def _embedding(seed: int, dim: int = 8) -> bytes:
    rng = np.random.default_rng(seed)
    vec = rng.random(dim).astype(np.float32)
    return _vec_to_bytes(vec / np.linalg.norm(vec))


def _document_seed_rows() -> list[dict[str, Any]]:
    return [
        {
            "doc_id": "ghost-a",
            "filename": "ghost_a.md",
            "embedding_seed": 1,
            "embedded_at": FROZEN - 4 * _DAY,
            "source_updated_at": FROZEN - 4 * _DAY,
        },
        {
            "doc_id": "ghost-b",
            "filename": "ghost_b.md",
            "embedding_seed": 2,
            "embedded_at": FROZEN - 5 * _DAY,
            "source_updated_at": FROZEN - 5 * _DAY,
        },
        {
            "doc_id": "api-v1",
            "filename": "api-v1.md",
            "embedding_seed": 3,
            "embedded_at": FROZEN - 12 * _DAY,
            "source_updated_at": FROZEN - 1 * _DAY,
        },
        {
            "doc_id": "api-v2",
            "filename": "api-v2.md",
            "embedding_seed": 3,
            "embedded_at": FROZEN - 2 * _DAY,
            "source_updated_at": FROZEN - 1 * _DAY,
        },
        {
            "doc_id": "guide-v1",
            "filename": "guide-v1.md",
            "embedding_seed": 4,
            "embedded_at": FROZEN - 8 * _DAY,
            "source_updated_at": FROZEN - 2 * _DAY,
        },
        {
            "doc_id": "guide-v2",
            "filename": "guide-v2.md",
            "embedding_seed": 5,
            "embedded_at": FROZEN - 1 * _DAY,
            "source_updated_at": FROZEN - 1 * _DAY,
        },
        {
            "doc_id": "stale-doc",
            "filename": "stale.md",
            "embedding_seed": 6,
            "embedded_at": FROZEN - 50 * _DAY,
            "source_updated_at": FROZEN - 10 * _DAY,
        },
        {
            "doc_id": "noisy-doc",
            "filename": "noisy.md",
            "embedding_seed": 7,
            "embedded_at": FROZEN - 6 * _DAY,
            "source_updated_at": FROZEN - 2 * _DAY,
        },
        {
            "doc_id": "healthy-a",
            "filename": "healthy_a.md",
            "embedding_seed": 8,
            "embedded_at": FROZEN - 3 * _DAY,
            "source_updated_at": FROZEN - 2 * _DAY,
        },
        {
            "doc_id": "healthy-b",
            "filename": "healthy_b.md",
            "embedding_seed": 9,
            "embedded_at": FROZEN - 3 * _DAY,
            "source_updated_at": FROZEN - 2 * _DAY,
        },
    ]


def _retrieval_seed_rows() -> list[dict[str, Any]]:
    recent_ts = FROZEN - 5 * _DAY
    return [
        *[
            {"doc_id": "api-v1", "query_hash": f"api-v1-q{i}", "rank": 1, "score": 0.81, "retrieved_at": recent_ts}
            for i in range(2)
        ],
        *[
            {"doc_id": "api-v2", "query_hash": f"api-v2-q{i}", "rank": 1, "score": 0.96, "retrieved_at": recent_ts}
            for i in range(5)
        ],
        *[
            {"doc_id": "guide-v1", "query_hash": f"guide-v1-q{i}", "rank": 1, "score": 0.72, "retrieved_at": recent_ts}
            for i in range(1)
        ],
        *[
            {"doc_id": "guide-v2", "query_hash": f"guide-v2-q{i}", "rank": 1, "score": 0.95, "retrieved_at": recent_ts}
            for i in range(6)
        ],
        *[
            {"doc_id": "stale-doc", "query_hash": f"stale-q{i}", "rank": 1, "score": 0.7, "retrieved_at": recent_ts}
            for i in range(3)
        ],
        *[
            {"doc_id": "noisy-doc", "query_hash": f"noisy-q{i}", "rank": 1, "score": 0.75, "retrieved_at": recent_ts}
            for i in range(10)
        ],
        *[
            {"doc_id": "healthy-a", "query_hash": f"healthy-a-q{i}", "rank": 1, "score": 0.97, "retrieved_at": recent_ts}
            for i in range(8)
        ],
        *[
            {"doc_id": "healthy-b", "query_hash": f"healthy-b-q{i}", "rank": 1, "score": 0.91, "retrieved_at": recent_ts}
            for i in range(7)
        ],
    ]


def _engagement_seed_rows() -> list[dict[str, Any]]:
    recent_ts = FROZEN - 5 * _DAY
    return [
        {"doc_id": "api-v2", "event_type": "opened", "engaged_at": recent_ts},
        *[
            {"doc_id": "guide-v2", "event_type": "opened", "engaged_at": recent_ts}
            for _ in range(2)
        ],
        {"doc_id": "noisy-doc", "event_type": "opened", "engaged_at": recent_ts},
        *[
            {"doc_id": "healthy-a", "event_type": "opened", "engaged_at": recent_ts}
            for _ in range(3)
        ],
        *[
            {"doc_id": "healthy-b", "event_type": "opened", "engaged_at": recent_ts}
            for _ in range(2)
        ],
    ]


def build_report_fixture_backend() -> InMemoryBackend:
    backend = InMemoryBackend()

    for row in _document_seed_rows():
        backend.upsert_document(
            row["doc_id"],
            row["filename"],
            embedding=_embedding(row["embedding_seed"]),
            embedded_at=row["embedded_at"],
        )
        backend.update_source_timestamp(row["doc_id"], row["source_updated_at"])

    for row in _retrieval_seed_rows():
        backend.insert_retrieval(
            row["doc_id"],
            row["query_hash"],
            row["rank"],
            row["score"],
            row["retrieved_at"],
        )

    for row in _engagement_seed_rows():
        backend.insert_engagement(
            row["doc_id"],
            row["event_type"],
            row["engaged_at"],
        )

    return backend


def build_report_fixture_snapshot(window_days: int = 30) -> dict[str, Any]:
    backend = build_report_fixture_backend()
    since = FROZEN - window_days * _DAY
    return {
        "window_days": window_days,
        "documents": backend.all_documents(),
        "retrieval_rows": backend.retrieval_counts(since=since),
        "engagement_rows": backend.engagement_counts(since=since),
        "embedding_rows": backend.all_embeddings(),
    }


def helper_inputs(window_days: int = 30) -> dict[str, Any]:
    corpulse = Corpulse(backend=build_report_fixture_backend())
    since = FROZEN - window_days * _DAY
    all_docs = corpulse.db.all_documents()
    retrieval_rows = corpulse.db.retrieval_counts(since=since)
    engagement_rows = corpulse.db.engagement_counts(since=since)
    ghosts = corpulse.get_ghosts()
    obsolete = corpulse.get_obsolete()
    stale = corpulse.get_stale_embeddings()
    suspects = corpulse.get_suspects()
    health = corpulse.corpus_health()
    return {
        "window_days": window_days,
        "all_docs": all_docs,
        "r_map": {row["doc_id"]: row for row in retrieval_rows},
        "e_map": {row["doc_id"]: row["cnt"] for row in engagement_rows},
        "ghosts": ghosts,
        "obsolete": obsolete,
        "stale": stale,
        "suspects": suspects,
        "ghost_ids": {row["doc_id"] for row in ghosts},
        "obsolete_ids": {row["doc_id"] for row in obsolete},
        "stale_ids": {row["doc_id"] for row in stale},
        "health": health,
    }


def expected_report_payload(window_days: int = 30, top_k: int = 20) -> dict[str, Any]:
    inputs = helper_inputs(window_days=window_days)
    return {
        "summary": _build_report_summary(
            inputs["all_docs"],
            inputs["window_days"],
            inputs["health"],
        ),
        "rows": _build_report_rows(
            inputs["all_docs"],
            inputs["r_map"],
            inputs["e_map"],
            inputs["ghost_ids"],
            inputs["obsolete_ids"],
            inputs["stale_ids"],
            top_k,
        ),
    }


def expected_cleanup_payload(window_days: int = 30, ghost_threshold_days: int = 30) -> dict[str, Any]:
    inputs = helper_inputs(window_days=window_days)
    return _build_cleanup_payload(
        inputs["health"],
        inputs["ghosts"],
        inputs["obsolete"],
        inputs["stale"],
        inputs["suspects"],
        ghost_threshold_days,
    )
