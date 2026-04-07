"""
Analytics test suite for corpulse.

Covers: get_ghosts, get_duplicates, get_obsolete, get_stale_embeddings,
get_suspects, corpus_health, FIX-01 (single get_duplicates call),
FIX-02 (WAL mode enabled).
"""

import sqlite3
from unittest.mock import patch

import numpy as np
import pytest

import corpulse.memento as m_mod
from corpulse.db import DB
from corpulse.memento import Corpulse, _vec_to_bytes

# ── constants ────────────────────────────────────────────────────────────────

FROZEN = 1_700_000_000.0  # arbitrary fixed timestamp for time-freezing

# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def corpulse(tmp_path):
    return Corpulse(db_path=str(tmp_path / "test.db"))


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_embedding(seed: int, dim: int = 8) -> bytes:
    rng = np.random.default_rng(seed)
    v = rng.random(dim).astype(np.float32)
    return _vec_to_bytes(v / np.linalg.norm(v))


# ── ghost tests ───────────────────────────────────────────────────────────────


def test_ghost_detection(corpulse, monkeypatch):
    """ghost1 has no recent retrievals; active has one — only ghost1 returned."""
    monkeypatch.setattr(m_mod, "_now", lambda: FROZEN)

    # Register both docs
    corpulse.db.upsert_document("ghost1", "ghost.md")
    corpulse.db.upsert_document("active", "active.md")

    # Log a retrieval for "active" within the ghost threshold window
    recent_ts = FROZEN - 5 * 86400  # 5 days ago (within 30-day threshold)
    corpulse.db.insert_retrieval("active", "qhash", 1, 0.9, recent_ts)

    ghosts = corpulse.get_ghosts()
    ghost_ids = [g["doc_id"] for g in ghosts]
    assert "ghost1" in ghost_ids
    assert "active" not in ghost_ids


def test_ghost_no_false_positives(corpulse, monkeypatch):
    """All docs have recent retrievals — get_ghosts() returns empty list."""
    monkeypatch.setattr(m_mod, "_now", lambda: FROZEN)

    corpulse.db.upsert_document("doc1", "doc1.md")
    corpulse.db.upsert_document("doc2", "doc2.md")

    recent_ts = FROZEN - 5 * 86400
    corpulse.db.insert_retrieval("doc1", "q1", 1, 0.9, recent_ts)
    corpulse.db.insert_retrieval("doc2", "q2", 1, 0.9, recent_ts)

    assert corpulse.get_ghosts() == []


# ── duplicate tests ───────────────────────────────────────────────────────────


def test_duplicates_above_threshold(corpulse):
    """Two nearly-identical normalized vectors should form 1 pair above 0.99."""
    base = np.ones(8, dtype=np.float32)
    near = base + 0.001 * np.ones(8, dtype=np.float32)

    base_norm = base / np.linalg.norm(base)
    near_norm = near / np.linalg.norm(near)

    emb_a = _vec_to_bytes(base_norm)
    emb_b = _vec_to_bytes(near_norm)

    corpulse.db.upsert_document("doc_a", "a.md", emb_a, embedded_at=1.0)
    corpulse.db.upsert_document("doc_b", "b.md", emb_b, embedded_at=1.0)

    pairs = corpulse.get_duplicates(threshold=0.99)
    assert len(pairs) == 1
    assert pairs[0]["similarity"] >= 0.99


def test_duplicates_empty_with_single_doc(corpulse):
    """Only one embedded doc — get_duplicates() returns empty (need >= 2)."""
    emb = _make_embedding(seed=42)
    corpulse.db.upsert_document("solo", "solo.md", emb, embedded_at=1.0)

    assert corpulse.get_duplicates() == []


def test_duplicates_requires_sklearn(corpulse):
    """With _SKLEARN patched to False, get_duplicates() raises RuntimeError."""
    with patch.object(m_mod, "_SKLEARN", False):
        with pytest.raises(RuntimeError, match="scikit-learn"):
            corpulse.get_duplicates()


# ── obsolete tests ────────────────────────────────────────────────────────────


def test_obsolete_detection(corpulse):
    """v1 should be flagged as obsolete, superseded_by v2."""
    corpulse.db.upsert_document("id1", "api-reference-v1.md")
    corpulse.db.upsert_document("id2", "api-reference-v2.md")

    obsolete = corpulse.get_obsolete()
    assert len(obsolete) == 1
    assert obsolete[0]["doc_id"] == "id1"
    assert "v2" in obsolete[0]["superseded_by"]


def test_obsolete_no_false_positives(corpulse):
    """Docs with unique filenames (no version pattern) — get_obsolete() empty."""
    corpulse.db.upsert_document("a", "install-guide.md")
    corpulse.db.upsert_document("b", "quickstart.md")
    corpulse.db.upsert_document("c", "faq.md")

    assert corpulse.get_obsolete() == []


# ── stale embedding tests ─────────────────────────────────────────────────────


def test_stale_embeddings(corpulse):
    """Source updated > 14 days after embedding — doc flagged as stale."""
    corpulse.db.upsert_document("stale1", "stale.md", None, 1000.0)
    corpulse.db.update_source_timestamp("stale1", 1000.0 + 15 * 86400 + 1)

    stale = corpulse.get_stale_embeddings()
    assert len(stale) == 1
    assert stale[0]["doc_id"] == "stale1"
    assert stale[0]["days_behind"] >= 15


def test_stale_embeddings_fresh(corpulse):
    """Source updated within threshold — get_stale_embeddings() returns empty."""
    corpulse.db.upsert_document("fresh1", "fresh.md", None, 1000.0)
    # Update source only 5 days after embedding (below 14-day threshold)
    corpulse.db.update_source_timestamp("fresh1", 1000.0 + 5 * 86400)

    assert corpulse.get_stale_embeddings() == []


# ── suspect tests ─────────────────────────────────────────────────────────────


def test_suspect_detection(corpulse, monkeypatch):
    """Doc with 10 retrievals and 0 engagements should appear as suspect."""
    monkeypatch.setattr(m_mod, "_now", lambda: FROZEN)

    corpulse.db.upsert_document("sus1", "suspect.md")

    # 10 retrievals, all within the window
    recent_ts = FROZEN - 5 * 86400
    for i in range(10):
        corpulse.db.insert_retrieval("sus1", f"q{i}", 1, 0.9, recent_ts)

    suspects = corpulse.get_suspects()
    sus_ids = [s["doc_id"] for s in suspects]
    assert "sus1" in sus_ids

    sus_doc = next(s for s in suspects if s["doc_id"] == "sus1")
    assert sus_doc["engagement_rate"] == 0.0


def test_suspect_below_min_retrievals(corpulse, monkeypatch):
    """Doc with only 3 retrievals — below minimum 5, not flagged as suspect."""
    monkeypatch.setattr(m_mod, "_now", lambda: FROZEN)

    corpulse.db.upsert_document("low1", "low.md")
    recent_ts = FROZEN - 5 * 86400
    for i in range(3):
        corpulse.db.insert_retrieval("low1", f"q{i}", 1, 0.9, recent_ts)

    assert corpulse.get_suspects() == []


# ── corpus_health tests ───────────────────────────────────────────────────────


def test_corpus_health_empty_db_returns_full_schema(tmp_path):
    """Empty DB should still return the full corpus_health() schema."""
    health = Corpulse(db_path=str(tmp_path / "empty.db")).corpus_health()

    assert set(health) == {
        "total_docs",
        "ghosts",
        "obsolete",
        "stale",
        "duplicates",
        "noise_estimate",
        "bloat_warning",
        "recommendation",
    }
    assert health["total_docs"] == 0
    assert health["ghosts"] == 0
    assert health["obsolete"] == 0
    assert health["stale"] == 0
    assert health["duplicates"] == 0
    assert health["noise_estimate"] == 0.0
    assert health["bloat_warning"] is False
    assert health["recommendation"] == "Corpus looks healthy."


def test_corpus_health_noise_estimate_counts_unique_noisy_docs(corpulse, monkeypatch):
    """Overlapping noisy categories should count each noisy doc only once."""
    monkeypatch.setattr(m_mod, "_now", lambda: FROZEN)

    shared_embedding = _make_embedding(seed=7)
    corpulse.db.upsert_document(
        "shared",
        "guide-v1.md",
        shared_embedding,
        embedded_at=FROZEN,
    )
    corpulse.db.upsert_document(
        "dup-peer",
        "guide-copy.md",
        shared_embedding,
        embedded_at=FROZEN,
    )
    corpulse.db.upsert_document(
        "fresh",
        "guide-v2.md",
        _make_embedding(seed=11),
        embedded_at=FROZEN,
    )

    corpulse.db.update_source_timestamp("shared", FROZEN + 15 * 86400 + 1)

    recent_ts = FROZEN - 5 * 86400
    corpulse.db.insert_retrieval("dup-peer", "dup-peer-recent", 1, 0.92, recent_ts)
    corpulse.db.insert_retrieval("fresh", "fresh-recent", 1, 0.88, recent_ts)

    health = corpulse.corpus_health()
    unique_noisy_docs = 2

    assert health["total_docs"] == 3
    assert health["ghosts"] == 1
    assert health["obsolete"] == 1
    assert health["stale"] == 1
    assert health["duplicates"] == 2
    assert health["noise_estimate"] == round(unique_noisy_docs / health["total_docs"], 2)


def test_corpus_health_calls_get_duplicates_once(corpulse):
    """FIX-01 verification: corpus_health() calls get_duplicates() exactly once."""
    # Provide 2 embedded docs so get_duplicates has data to process
    emb_a = _make_embedding(seed=1)
    emb_b = _make_embedding(seed=2)
    corpulse.db.upsert_document("h1", "health1.md", emb_a, embedded_at=1.0)
    corpulse.db.upsert_document("h2", "health2.md", emb_b, embedded_at=1.0)

    call_count = []
    original = corpulse.get_duplicates

    def counting_wrapper(*a, **kw):
        call_count.append(1)
        return original(*a, **kw)

    with patch.object(corpulse, "get_duplicates", counting_wrapper):
        corpulse.corpus_health()

    assert len(call_count) == 1, (
        f"Expected get_duplicates() called exactly once, got {len(call_count)}"
    )


# ── WAL mode test ─────────────────────────────────────────────────────────────


def test_wal_mode_enabled(tmp_path):
    """FIX-02 verification: DB initialisation sets WAL journal mode."""
    db_path = str(tmp_path / "wal.db")
    DB(db_path)

    conn = sqlite3.connect(db_path)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()

    assert mode == "wal", f"Expected WAL mode, got: {mode!r}"
