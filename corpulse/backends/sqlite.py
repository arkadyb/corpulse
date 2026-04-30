from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Callable, ParamSpec, TypeVar

from .base import (
    StorageBackend,
    StorageBackendError,
)
from ..models import (
    DocumentRow,
    EmbeddingRow,
    EngagementEventRow,
    EngagementRow,
    GenerationTraceRow,
    QueryRow,
    RetrievalRow,
)

SCHEMA = """
PRAGMA journal_mode=WAL;

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

CREATE TABLE IF NOT EXISTS query_attempts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash   TEXT NOT NULL,
    result_count INTEGER NOT NULL,
    attempted_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS engagements (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id       TEXT NOT NULL,
    event_type   TEXT NOT NULL,          -- e.g. "opened", "copied", "thumbs_up"
    engaged_at   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS generation_traces (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_text           TEXT NOT NULL,
    retrieved_context_refs TEXT NOT NULL,
    final_answer_text     TEXT NOT NULL,
    evaluation_labels     TEXT DEFAULT NULL,
    captured_at           REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_retrievals_doc    ON retrievals(doc_id);
CREATE INDEX IF NOT EXISTS idx_retrievals_time   ON retrievals(retrieved_at);
CREATE INDEX IF NOT EXISTS idx_query_attempts_query ON query_attempts(query_hash);
CREATE INDEX IF NOT EXISTS idx_query_attempts_time ON query_attempts(attempted_at);
CREATE INDEX IF NOT EXISTS idx_engagements_doc   ON engagements(doc_id);
CREATE INDEX IF NOT EXISTS idx_generation_traces_time ON generation_traces(captured_at);
"""

P = ParamSpec("P")
R = TypeVar("R")


def _translate_sqlite_errors(fn: Callable[P, R]) -> Callable[P, R]:
    @wraps(fn)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except sqlite3.Error as exc:
            raise StorageBackendError(str(exc)) from exc

    return wrapped


class SQLiteBackend(StorageBackend):
    def __init__(self, db_path: str):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @_translate_sqlite_errors
    def _init(self) -> None:
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

    @_translate_sqlite_errors
    def upsert_document(
        self,
        doc_id: str,
        filename: str,
        embedding: bytes | None = None,
        embedded_at: float | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO documents (doc_id, filename, embedding_vec, embedded_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    filename      = excluded.filename,
                    embedding_vec = COALESCE(excluded.embedding_vec, embedding_vec),
                    embedded_at   = COALESCE(excluded.embedded_at,   embedded_at)
                """,
                (doc_id, filename, embedding, embedded_at),
            )

    @_translate_sqlite_errors
    def insert_retrieval(
        self,
        doc_id: str,
        query_hash: str,
        rank: int,
        score: float,
        retrieved_at: float,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO retrievals (doc_id, query_hash, rank, score, retrieved_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (doc_id, query_hash, rank, score, retrieved_at),
            )

    @_translate_sqlite_errors
    def insert_query_attempt(
        self,
        query_hash: str,
        result_count: int,
        attempted_at: float,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO query_attempts (query_hash, result_count, attempted_at)
                VALUES (?, ?, ?)
                """,
                (query_hash, result_count, attempted_at),
            )

    @_translate_sqlite_errors
    def insert_engagement(
        self,
        doc_id: str,
        event_type: str,
        engaged_at: float,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO engagements (doc_id, event_type, engaged_at)
                VALUES (?, ?, ?)
                """,
                (doc_id, event_type, engaged_at),
            )

    @_translate_sqlite_errors
    def insert_generation_trace(
        self,
        prompt_text: str,
        retrieved_context_refs: list[dict[str, object]],
        final_answer_text: str,
        evaluation_labels: list[str] | None,
        captured_at: float,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO generation_traces (
                    prompt_text,
                    retrieved_context_refs,
                    final_answer_text,
                    evaluation_labels,
                    captured_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    prompt_text,
                    json.dumps(retrieved_context_refs),
                    final_answer_text,
                    json.dumps(evaluation_labels) if evaluation_labels is not None else None,
                    captured_at,
                ),
            )

    @_translate_sqlite_errors
    def update_source_timestamp(self, doc_id: str, updated_at: float) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE documents SET source_updated_at = ? WHERE doc_id = ?
                """,
                (updated_at, doc_id),
            )

    @_translate_sqlite_errors
    def delete_document(self, doc_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM retrievals WHERE doc_id = ?", (doc_id,))
            conn.execute("DELETE FROM engagements WHERE doc_id = ?", (doc_id,))
            conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))

    @_translate_sqlite_errors
    def delete_generation_traces(
        self,
        *,
        trace_ids: list[int] | None = None,
        prompt_text: str | None = None,
        evaluation_label: str | None = None,
    ) -> None:
        clauses: list[str] = []
        params: list[object] = []
        if trace_ids:
            placeholders = ",".join("?" for _ in trace_ids)
            clauses.append(f"id IN ({placeholders})")
            params.extend(trace_ids)
        if prompt_text is not None:
            clauses.append("prompt_text = ?")
            params.append(prompt_text)
        if evaluation_label is not None:
            clauses.append("evaluation_labels LIKE ?")
            params.append(f'%"{evaluation_label}"%')

        if not clauses:
            return

        with self._conn() as conn:
            conn.execute(
                f"DELETE FROM generation_traces WHERE {' OR '.join(clauses)}",
                params,
            )

    @_translate_sqlite_errors
    def all_documents(self) -> list[DocumentRow]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM documents").fetchall()
        return [dict(row) for row in rows]

    @_translate_sqlite_errors
    def retrieval_counts(self, since: float) -> list[RetrievalRow]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT doc_id, COUNT(*) AS cnt,
                       AVG(rank) AS avg_rank, AVG(score) AS avg_score
                FROM retrievals
                WHERE retrieved_at >= ?
                GROUP BY doc_id
                """,
                (since,),
            ).fetchall()
        return [dict(row) for row in rows]

    @_translate_sqlite_errors
    def query_counts(self, since: float) -> list[QueryRow]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT query_hash, COUNT(*) AS cnt,
                       AVG(rank) AS avg_rank, AVG(score) AS avg_score,
                       MIN(rank) AS min_rank, MAX(rank) AS max_rank,
                       MIN(score) AS min_score, MAX(score) AS max_score,
                       MIN(retrieved_at) AS first_retrieved_at,
                       MAX(retrieved_at) AS last_retrieved_at
                FROM retrievals
                WHERE retrieved_at >= ?
                GROUP BY query_hash
                ORDER BY query_hash
                """,
                (since,),
            ).fetchall()
        return [dict(row) for row in rows]

    @_translate_sqlite_errors
    def query_attempt_counts(self, since: float) -> list[QueryAttemptRow]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT query_hash, COUNT(*) AS cnt,
                       SUM(CASE WHEN result_count > 0 THEN 1 ELSE 0 END) AS result_cnt,
                       MIN(attempted_at) AS first_attempted_at,
                       MAX(attempted_at) AS last_attempted_at
                FROM query_attempts
                WHERE attempted_at >= ?
                GROUP BY query_hash
                ORDER BY query_hash
                """,
                (since,),
            ).fetchall()
        return [dict(row) for row in rows]

    @_translate_sqlite_errors
    def engagement_counts(self, since: float) -> list[EngagementRow]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT doc_id, COUNT(*) AS cnt
                FROM engagements
                WHERE engaged_at >= ?
                GROUP BY doc_id
                """,
                (since,),
            ).fetchall()
        return [dict(row) for row in rows]

    @_translate_sqlite_errors
    def engagement_event_counts(self, since: float) -> list[EngagementEventRow]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT event_type, COUNT(*) AS cnt
                FROM engagements
                WHERE engaged_at >= ?
                GROUP BY event_type
                ORDER BY event_type
                """,
                (since,),
            ).fetchall()
        return [dict(row) for row in rows]

    @_translate_sqlite_errors
    def generation_traces(self, since: float) -> list[GenerationTraceRow]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id AS trace_id,
                       prompt_text,
                       retrieved_context_refs,
                       final_answer_text,
                       evaluation_labels,
                       captured_at
                FROM generation_traces
                WHERE captured_at >= ?
                ORDER BY captured_at, id
                """,
                (since,),
            ).fetchall()

        traces: list[GenerationTraceRow] = []
        for row in rows:
            trace = dict(row)
            trace["retrieved_context_refs"] = (
                json.loads(trace["retrieved_context_refs"])
                if isinstance(trace["retrieved_context_refs"], str)
                else list(trace["retrieved_context_refs"])
            )
            if trace["evaluation_labels"] is not None and isinstance(trace["evaluation_labels"], str):
                trace["evaluation_labels"] = json.loads(trace["evaluation_labels"])
            traces.append(trace)
        return traces

    @_translate_sqlite_errors
    def all_embeddings(self) -> list[EmbeddingRow]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT doc_id, filename, embedding_vec
                FROM documents
                WHERE embedding_vec IS NOT NULL
                """
            ).fetchall()
        return [dict(row) for row in rows]

    @_translate_sqlite_errors
    def close(self) -> None:
        return None
