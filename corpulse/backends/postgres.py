from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import (
    DocumentRow,
    EmbeddingRow,
    EngagementRow,
    RetrievalRow,
    StorageBackend,
    StorageBackendError,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    filename TEXT,
    embedding_vec BYTEA,
    embedded_at DOUBLE PRECISION,
    source_updated_at DOUBLE PRECISION DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS retrievals (
    id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    rank INTEGER,
    score DOUBLE PRECISION,
    retrieved_at DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS engagements (
    id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    engaged_at DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_retrievals_doc ON retrievals(doc_id);
CREATE INDEX IF NOT EXISTS idx_retrievals_time ON retrievals(retrieved_at);
CREATE INDEX IF NOT EXISTS idx_engagements_doc ON engagements(doc_id);
"""


def _load_psycopg_pool() -> tuple[Any, Any, type[BaseException]]:
    try:
        from psycopg.rows import dict_row
        import psycopg
        from psycopg_pool import ConnectionPool
    except ImportError as exc:
        raise ImportError(
            "psycopg_pool is required to use PostgresBackend. "
            "Install corpulse[postgres]."
        ) from exc

    return ConnectionPool, dict_row, psycopg.Error


class PostgresBackend(StorageBackend):
    def __init__(self, conninfo: str, *, min_size: int = 1, max_size: int = 10):
        connection_pool, dict_row, error_cls = _load_psycopg_pool()
        self._error_cls = error_cls
        self._pool = connection_pool(
            conninfo=conninfo,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        self._closed = False
        self._pool.wait()
        self._init()

    def _run(self, operation: Callable[[Any], Any]):
        try:
            with self._pool.connection() as conn:
                return operation(conn)
        except self._error_cls as exc:
            raise StorageBackendError(str(exc)) from exc

    def _init(self) -> None:
        self._run(lambda conn: conn.execute(SCHEMA))

    def upsert_document(
        self,
        doc_id: str,
        filename: str,
        embedding: bytes | None = None,
        embedded_at: float | None = None,
    ) -> None:
        self._run(
            lambda conn: conn.execute(
                """
                INSERT INTO documents (doc_id, filename, embedding_vec, embedded_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (doc_id) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    embedding_vec = COALESCE(EXCLUDED.embedding_vec, documents.embedding_vec),
                    embedded_at = COALESCE(EXCLUDED.embedded_at, documents.embedded_at)
                """,
                (doc_id, filename, embedding, embedded_at),
            )
        )

    def insert_retrieval(
        self,
        doc_id: str,
        query_hash: str,
        rank: int,
        score: float,
        retrieved_at: float,
    ) -> None:
        self._run(
            lambda conn: conn.execute(
                """
                INSERT INTO retrievals (doc_id, query_hash, rank, score, retrieved_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (doc_id, query_hash, rank, score, retrieved_at),
            )
        )

    def insert_engagement(
        self,
        doc_id: str,
        event_type: str,
        engaged_at: float,
    ) -> None:
        self._run(
            lambda conn: conn.execute(
                """
                INSERT INTO engagements (doc_id, event_type, engaged_at)
                VALUES (%s, %s, %s)
                """,
                (doc_id, event_type, engaged_at),
            )
        )

    def update_source_timestamp(self, doc_id: str, updated_at: float) -> None:
        self._run(
            lambda conn: conn.execute(
                """
                UPDATE documents SET source_updated_at = %s WHERE doc_id = %s
                """,
                (updated_at, doc_id),
            )
        )

    def delete_document(self, doc_id: str) -> None:
        def operation(conn):
            conn.execute("DELETE FROM retrievals WHERE doc_id = %s", (doc_id,))
            conn.execute("DELETE FROM engagements WHERE doc_id = %s", (doc_id,))
            conn.execute("DELETE FROM documents WHERE doc_id = %s", (doc_id,))

        self._run(operation)

    def all_documents(self) -> list[DocumentRow]:
        return self._run(
            lambda conn: [
                dict(row)
                for row in conn.execute("SELECT * FROM documents").fetchall()
            ]
        )

    def retrieval_counts(self, since: float) -> list[RetrievalRow]:
        return self._run(
            lambda conn: [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT doc_id, COUNT(*) AS cnt,
                           AVG(rank) AS avg_rank, AVG(score) AS avg_score
                    FROM retrievals
                    WHERE retrieved_at >= %s
                    GROUP BY doc_id
                    """,
                    (since,),
                ).fetchall()
            ]
        )

    def engagement_counts(self, since: float) -> list[EngagementRow]:
        return self._run(
            lambda conn: [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT doc_id, COUNT(*) AS cnt
                    FROM engagements
                    WHERE engaged_at >= %s
                    GROUP BY doc_id
                    """,
                    (since,),
                ).fetchall()
            ]
        )

    def all_embeddings(self) -> list[EmbeddingRow]:
        return self._run(
            lambda conn: [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT doc_id, filename, embedding_vec
                    FROM documents
                    WHERE embedding_vec IS NOT NULL
                    """
                ).fetchall()
            ]
        )

    def close(self) -> None:
        if self._closed:
            return
        self._pool.close()
        self._closed = True
