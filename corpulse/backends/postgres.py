from __future__ import annotations

import json
from collections.abc import Callable
import re
from typing import Any

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
    QueryAttemptRow,
    QueryRow,
    RagRequestComponent,
    RagRequestTimings,
    RagRequestTraceRow,
    RetrievalRow,
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
    query_attempts = _qualified_name("query_attempts", schema=schema, prefix=prefix)
    engagements = _qualified_name("engagements", schema=schema, prefix=prefix)
    generation_traces = _qualified_name("generation_traces", schema=schema, prefix=prefix)
    rag_request_traces = _qualified_name("rag_request_traces", schema=schema, prefix=prefix)
    retrievals_doc_idx = _index_name("idx_retrievals_doc", prefix=prefix)
    retrievals_time_idx = _index_name("idx_retrievals_time", prefix=prefix)
    query_attempts_query_idx = _index_name("idx_query_attempts_query", prefix=prefix)
    query_attempts_time_idx = _index_name("idx_query_attempts_time", prefix=prefix)
    engagements_doc_idx = _index_name("idx_engagements_doc", prefix=prefix)
    generation_traces_time_idx = _index_name("idx_generation_traces_time", prefix=prefix)
    rag_request_traces_time_idx = _index_name("idx_rag_request_traces_time", prefix=prefix)
    rag_request_traces_session_idx = _index_name("idx_rag_request_traces_session", prefix=prefix)
    rag_request_traces_query_idx = _index_name("idx_rag_request_traces_query", prefix=prefix)

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
        f"""CREATE TABLE IF NOT EXISTS {query_attempts} (
    id BIGSERIAL PRIMARY KEY,
    query_hash TEXT NOT NULL,
    result_count INTEGER NOT NULL,
    attempted_at DOUBLE PRECISION NOT NULL
);""",
        f"""CREATE TABLE IF NOT EXISTS {engagements} (
    id BIGSERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    engaged_at DOUBLE PRECISION NOT NULL
);""",
        f"""CREATE TABLE IF NOT EXISTS {generation_traces} (
    id BIGSERIAL PRIMARY KEY,
    prompt_text TEXT NOT NULL,
    retrieved_context_refs TEXT NOT NULL,
    final_answer_text TEXT NOT NULL,
    evaluation_labels TEXT DEFAULT NULL,
    captured_at DOUBLE PRECISION NOT NULL
);""",
        f"""CREATE TABLE IF NOT EXISTS {rag_request_traces} (
    id BIGSERIAL PRIMARY KEY,
    request_id TEXT DEFAULT NULL,
    session_id TEXT DEFAULT NULL,
    query_text TEXT DEFAULT NULL,
    query_hash TEXT DEFAULT NULL,
    input_token_count INTEGER DEFAULT NULL,
    output_token_count INTEGER DEFAULT NULL,
    components TEXT NOT NULL,
    timings TEXT NOT NULL,
    timeout BOOLEAN NOT NULL,
    error TEXT DEFAULT NULL,
    captured_at DOUBLE PRECISION NOT NULL
);""",
    ]
    indexes = [
        f"CREATE INDEX IF NOT EXISTS {retrievals_doc_idx} ON {retrievals}(doc_id);",
        f"CREATE INDEX IF NOT EXISTS {retrievals_time_idx} ON {retrievals}(retrieved_at);",
        f"CREATE INDEX IF NOT EXISTS {query_attempts_query_idx} ON {query_attempts}(query_hash);",
        f"CREATE INDEX IF NOT EXISTS {query_attempts_time_idx} ON {query_attempts}(attempted_at);",
        f"CREATE INDEX IF NOT EXISTS {engagements_doc_idx} ON {engagements}(doc_id);",
        f"CREATE INDEX IF NOT EXISTS {generation_traces_time_idx} ON {generation_traces}(captured_at);",
        f"CREATE INDEX IF NOT EXISTS {rag_request_traces_time_idx} ON {rag_request_traces}(captured_at);",
        f"CREATE INDEX IF NOT EXISTS {rag_request_traces_session_idx} ON {rag_request_traces}(session_id);",
        f"CREATE INDEX IF NOT EXISTS {rag_request_traces_query_idx} ON {rag_request_traces}(query_hash);",
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
            "Install it with: pip install corpulse[postgres]"
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

    def insert_query_attempt(
        self,
        query_hash: str,
        result_count: int,
        attempted_at: float,
    ) -> None:
        self._run(
            lambda conn: conn.execute(
                f"""
                INSERT INTO {self._t("query_attempts")} (query_hash, result_count, attempted_at)
                VALUES (%s, %s, %s)
                """,
                (query_hash, result_count, attempted_at),
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

    def insert_generation_trace(
        self,
        prompt_text: str,
        retrieved_context_refs: list[dict[str, object]],
        final_answer_text: str,
        evaluation_labels: list[str] | None,
        captured_at: float,
    ) -> None:
        self._run(
            lambda conn: conn.execute(
                f"""
                INSERT INTO {self._t("generation_traces")} (
                    prompt_text,
                    retrieved_context_refs,
                    final_answer_text,
                    evaluation_labels,
                    captured_at
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    prompt_text,
                    json.dumps(retrieved_context_refs),
                    final_answer_text,
                    json.dumps(evaluation_labels) if evaluation_labels is not None else None,
                    captured_at,
                ),
            )
        )

    def insert_rag_request_trace(
        self,
        request_id: str | None,
        session_id: str | None,
        query_text: str | None,
        query_hash: str | None,
        input_token_count: int | None,
        output_token_count: int | None,
        components: list[RagRequestComponent],
        timings: RagRequestTimings,
        timeout: bool,
        error: str | None,
        captured_at: float,
    ) -> None:
        self._run(
            lambda conn: conn.execute(
                f"""
                INSERT INTO {self._t("rag_request_traces")} (
                    request_id,
                    session_id,
                    query_text,
                    query_hash,
                    input_token_count,
                    output_token_count,
                    components,
                    timings,
                    timeout,
                    error,
                    captured_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    request_id,
                    session_id,
                    query_text,
                    query_hash,
                    input_token_count,
                    output_token_count,
                    json.dumps(components),
                    json.dumps(timings),
                    timeout,
                    error,
                    captured_at,
                ),
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

    def delete_generation_traces(
        self,
        *,
        trace_ids: list[int] | None = None,
        prompt_text: str | None = None,
        evaluation_label: str | None = None,
    ) -> None:
        clauses = []
        params: list[Any] = []
        if trace_ids:
            placeholders = []
            for trace_id in trace_ids:
                placeholders.append(f"%s")
                params.append(trace_id)
            clauses.append(f"id IN ({', '.join(placeholders)})")
        if prompt_text is not None:
            clauses.append("prompt_text = %s")
            params.append(prompt_text)
        if evaluation_label is not None:
            clauses.append("evaluation_labels LIKE %s")
            params.append(f'%"{evaluation_label}"%')

        if not clauses:
            return

        def operation(conn):
            conn.execute(
                f"DELETE FROM {self._t('generation_traces')} WHERE {' OR '.join(clauses)}",
                tuple(params),
            )

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

    def query_counts(self, since: float) -> list[QueryRow]:
        return self._run(
            lambda conn: [
                dict(row)
                for row in conn.execute(
                    f"""
                    SELECT query_hash, COUNT(*) AS cnt,
                           AVG(rank) AS avg_rank, AVG(score) AS avg_score,
                           MIN(rank) AS min_rank, MAX(rank) AS max_rank,
                           MIN(score) AS min_score, MAX(score) AS max_score,
                           MIN(retrieved_at) AS first_retrieved_at,
                           MAX(retrieved_at) AS last_retrieved_at
                    FROM {self._t("retrievals")}
                    WHERE retrieved_at >= %s
                    GROUP BY query_hash
                    ORDER BY query_hash
                    """,
                    (since,),
                ).fetchall()
            ]
        )

    def query_attempt_counts(self, since: float) -> list[QueryAttemptRow]:
        return self._run(
            lambda conn: [
                dict(row)
                for row in conn.execute(
                    f"""
                    SELECT query_hash, COUNT(*) AS cnt,
                           SUM(CASE WHEN result_count > 0 THEN 1 ELSE 0 END) AS result_cnt,
                           MIN(attempted_at) AS first_attempted_at,
                           MAX(attempted_at) AS last_attempted_at
                    FROM {self._t("query_attempts")}
                    WHERE attempted_at >= %s
                    GROUP BY query_hash
                    ORDER BY query_hash
                    """,
                    (since,),
                ).fetchall()
            ]
        )

    def engagement_event_counts(self, since: float) -> list[EngagementEventRow]:
        return self._run(
            lambda conn: [
                dict(row)
                for row in conn.execute(
                    f"""
                    SELECT event_type, COUNT(*) AS cnt
                    FROM {self._t("engagements")}
                    WHERE engaged_at >= %s
                    GROUP BY event_type
                    ORDER BY event_type
                    """,
                    (since,),
                ).fetchall()
            ]
        )

    def generation_traces(self, since: float) -> list[GenerationTraceRow]:
        rows = self._run(
            lambda conn: [
                dict(row)
                for row in conn.execute(
                    f"""
                    SELECT id AS trace_id,
                           prompt_text,
                           retrieved_context_refs,
                           final_answer_text,
                           evaluation_labels,
                           captured_at
                    FROM {self._t("generation_traces")}
                    WHERE captured_at >= %s
                    ORDER BY captured_at, id
                    """,
                    (since,),
                ).fetchall()
            ]
        )
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

    def rag_request_traces(self, since: float) -> list[RagRequestTraceRow]:
        rows = self._run(
            lambda conn: [
                dict(row)
                for row in conn.execute(
                    f"""
                    SELECT id AS trace_id,
                           request_id,
                           session_id,
                           query_text,
                           query_hash,
                           input_token_count,
                           output_token_count,
                           components,
                           timings,
                           timeout,
                           error,
                           captured_at
                    FROM {self._t("rag_request_traces")}
                    WHERE captured_at >= %s
                    ORDER BY captured_at, id
                    """,
                    (since,),
                ).fetchall()
            ]
        )
        traces: list[RagRequestTraceRow] = []
        for row in rows:
            trace = dict(row)
            trace["components"] = (
                json.loads(trace["components"])
                if isinstance(trace["components"], str)
                else list(trace["components"])
            )
            trace["timings"] = (
                json.loads(trace["timings"])
                if isinstance(trace["timings"], str)
                else dict(trace["timings"])
            )
            if isinstance(trace["timeout"], str):
                trace["timeout"] = trace["timeout"].lower() in {"t", "true", "1"}
            else:
                trace["timeout"] = bool(trace["timeout"])
            traces.append(trace)
        return traces

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
