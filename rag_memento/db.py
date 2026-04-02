from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id          TEXT PRIMARY KEY,
    filename        TEXT,
    embedding_vec   BLOB,               -- serialised numpy float32 array
    embedded_at     REAL,               -- unix timestamp
    source_updated_at REAL DEFAULT NULL -- unix timestamp of last known source change
);

CREATE TABLE IF NOT EXISTS retrievals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id      TEXT NOT NULL,
    query_hash  TEXT NOT NULL,
    rank        INTEGER,
    score       REAL,
    retrieved_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS engagements (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id       TEXT NOT NULL,
    event_type   TEXT NOT NULL,          -- e.g. "opened", "copied", "thumbs_up"
    engaged_at   REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_retrievals_doc    ON retrievals(doc_id);
CREATE INDEX IF NOT EXISTS idx_retrievals_time   ON retrievals(retrieved_at);
CREATE INDEX IF NOT EXISTS idx_engagements_doc   ON engagements(doc_id);
"""


class DB:
    def __init__(self, db_path: str):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self):
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ writes

    def upsert_document(self, doc_id: str, filename: str,
                        embedding: bytes | None = None,
                        embedded_at: float | None = None):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO documents (doc_id, filename, embedding_vec, embedded_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    filename      = excluded.filename,
                    embedding_vec = COALESCE(excluded.embedding_vec, embedding_vec),
                    embedded_at   = COALESCE(excluded.embedded_at,   embedded_at)
            """, (doc_id, filename, embedding, embedded_at))

    def insert_retrieval(self, doc_id: str, query_hash: str,
                         rank: int, score: float, retrieved_at: float):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO retrievals (doc_id, query_hash, rank, score, retrieved_at)
                VALUES (?, ?, ?, ?, ?)
            """, (doc_id, query_hash, rank, score, retrieved_at))

    def insert_engagement(self, doc_id: str, event_type: str, engaged_at: float):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO engagements (doc_id, event_type, engaged_at)
                VALUES (?, ?, ?)
            """, (doc_id, event_type, engaged_at))

    def update_source_timestamp(self, doc_id: str, updated_at: float):
        with self._conn() as conn:
            conn.execute("""
                UPDATE documents SET source_updated_at = ? WHERE doc_id = ?
            """, (updated_at, doc_id))

    # ------------------------------------------------------------------ reads

    def all_documents(self):
        with self._conn() as conn:
            return conn.execute("SELECT * FROM documents").fetchall()

    def retrieval_counts(self, since: float):
        with self._conn() as conn:
            return conn.execute("""
                SELECT doc_id, COUNT(*) AS cnt,
                       AVG(rank) AS avg_rank, AVG(score) AS avg_score
                FROM retrievals
                WHERE retrieved_at >= ?
                GROUP BY doc_id
            """, (since,)).fetchall()

    def engagement_counts(self, since: float):
        with self._conn() as conn:
            return conn.execute("""
                SELECT doc_id, COUNT(*) AS cnt
                FROM engagements
                WHERE engaged_at >= ?
                GROUP BY doc_id
            """, (since,)).fetchall()

    def all_embeddings(self):
        """Return rows that have a stored embedding vector."""
        with self._conn() as conn:
            return conn.execute("""
                SELECT doc_id, filename, embedding_vec
                FROM documents
                WHERE embedding_vec IS NOT NULL
            """).fetchall()
