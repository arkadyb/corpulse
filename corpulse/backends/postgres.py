from __future__ import annotations

from collections.abc import Callable
import re
from typing import Any

from .base import (
    DocumentRow,
    EmbeddingRow,
    EngagementRow,
    RetrievalRow,
    StorageBackend,
    StorageBackendError,
)
from ._dsn import _normalize_postgres_dsn

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(value: str | None, *, field: str, allow_none: bool = False) -> str | None:
    if value is None:
        if allow_none:
            return None
        raise ValueError(f"{field} cannot be None")
    if not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"invalid postgres identifier for {field}: {value!r}")
    return value


def _validate_schema(schema: str | None) -> str | None:
    return _validate_identifier(schema, field="schema", allow_none=True)


def _validate_table_prefix(table_prefix: str) -> str:
    if table_prefix == "":
        return table_prefix
    validated = _validate_identifier(table_prefix, field="table_prefix")
    assert validated is not None
    return validated


def _table_name(name: str, *, prefix: str = "") -> str:
    return f"{prefix}{name}"


def _qualified_name(name: str, *, schema: str | None = None, prefix: str = "") -> str:
    table_name = _table_name(name, prefix=prefix)
    return f"{schema}.{table_name}" if schema else table_name


def _index_name(name: str, *, prefix: str = "") -> str:
    return f"{prefix}{name}" if prefix else name


def build_schema_sql(schema: str | None = None, prefix: str = "") -> str:
    schema = _validate_schema(schema)
    prefix = _validate_table_prefix(prefix)

    documents = _qualified_name("documents", schema=schema, prefix=prefix)
    retrievals = _qualified_name("retrievals", schema=schema, prefix=prefix)
    engagements = _qualified_name("engagements", schema=schema, prefix=prefix)
    retrievals_doc_idx = _index_name("idx_retrievals_doc", prefix=prefix)
    retrievals_time_idx = _index_name("idx_retrievals_time", prefix=prefix)
    engagements_doc_idx = _index_name("idx_engagements_doc", prefix=prefix)

    tables = [
        f"""CREATE TABLE IF NOT EXISTS {documents} (
    doc_id TEXT PRIMARY KEY,
    filename TEXT,
    embedding_vec BYTEA,
    embedded_at DOUBLE PRECISION,
    source_updated_at DOUBLE PRECISION DEFAULT NULL
);""",
        f"""CREATE TABLE IF NOT EXISTS {retrievals} (
    id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    rank INTEGER,
    score DOUBLE PRECISION,
    retrieved_at DOUBLE PRECISION NOT NULL
);""",
        f"""CREATE TABLE IF NOT EXISTS {engagements} (
    id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    engaged_at DOUBLE PRECISION NOT NULL
);""",
    ]
    indexes = [
        f"CREATE INDEX IF NOT EXISTS {retrievals_doc_idx} ON {retrievals}(doc_id);",
        f"CREATE INDEX IF NOT EXISTS {retrievals_time_idx} ON {retrievals}(retrieved_at);",
        f"CREATE INDEX IF NOT EXISTS {engagements_doc_idx} ON {engagements}(doc_id);",
    ]

    sql_sections: list[str] = []
    if schema:
        sql_sections.append(f"CREATE SCHEMA IF NOT EXISTS {schema};")
    sql_sections.append("\n\n".join(tables))
    sql_sections.append("\n".join(indexes))
    return "\n" + "\n\n".join(sql_sections) + "\n"


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
    def __init__(
        self,
        conninfo: str,
        *,
        min_size: int = 1,
        max_size: int = 10,
        schema: str | None = None,
        table_prefix: str = "",
    ):
        self._schema = _validate_schema(schema)
        self._table_prefix = _validate_table_prefix(table_prefix)
        connection_pool, dict_row, error_cls = _load_psycopg_pool()
        self._error_cls = error_cls
        self._pool = connection_pool(
            conninfo=_normalize_postgres_dsn(conninfo),
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

    def _t(self, name: str) -> str:
        return _qualified_name(name, schema=self._schema, prefix=self._table_prefix)

    def _init(self) -> None:
        self._run(
            lambda conn: conn.execute(
                build_schema_sql(schema=self._schema, prefix=self._table_prefix)
            )
        )

    def upsert_document(
        self,
        doc_id: str,
        filename: str,
        embedding: bytes | None = None,
        embedded_at: float | None = None,
    ) -> None:
        self._run(
            lambda conn: conn.execute(
                f"""
                INSERT INTO {self._t("documents")} (doc_id, filename, embedding_vec, embedded_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (doc_id) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    embedding_vec = COALESCE(EXCLUDED.embedding_vec, {self._t("documents")}.embedding_vec),
                    embedded_at = COALESCE(EXCLUDED.embedded_at, {self._t("documents")}.embedded_at)
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
                f"""
                INSERT INTO {self._t("retrievals")} (doc_id, query_hash, rank, score, retrieved_at)
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
                f"""
                INSERT INTO {self._t("engagements")} (doc_id, event_type, engaged_at)
                VALUES (%s, %s, %s)
                """,
                (doc_id, event_type, engaged_at),
            )
        )

    def update_source_timestamp(self, doc_id: str, updated_at: float) -> None:
        self._run(
            lambda conn: conn.execute(
                f"""
                UPDATE {self._t("documents")} SET source_updated_at = %s WHERE doc_id = %s
                """,
                (updated_at, doc_id),
            )
        )

    def delete_document(self, doc_id: str) -> None:
        def operation(conn):
            conn.execute(f"DELETE FROM {self._t('retrievals')} WHERE doc_id = %s", (doc_id,))
            conn.execute(f"DELETE FROM {self._t('engagements')} WHERE doc_id = %s", (doc_id,))
            conn.execute(f"DELETE FROM {self._t('documents')} WHERE doc_id = %s", (doc_id,))

        self._run(operation)

    def all_documents(self) -> list[DocumentRow]:
        return self._run(
            lambda conn: [
                dict(row)
                for row in conn.execute(f"SELECT * FROM {self._t('documents')}").fetchall()
            ]
        )

    def retrieval_counts(self, since: float) -> list[RetrievalRow]:
        return self._run(
            lambda conn: [
                dict(row)
                for row in conn.execute(
                    f"""
                    SELECT doc_id, COUNT(*) AS cnt,
                           AVG(rank) AS avg_rank, AVG(score) AS avg_score
                    FROM {self._t("retrievals")}
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
                    f"""
                    SELECT doc_id, COUNT(*) AS cnt
                    FROM {self._t("engagements")}
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
                    f"""
                    SELECT doc_id, filename, embedding_vec
                    FROM {self._t("documents")}
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
