from __future__ import annotations

import json
from typing import Any

from ._dsn import _normalize_postgres_dsn
from .base import (
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
    RetrievalRow,
)
from .postgres import build_schema_sql, _qualified_name, _validate_schema, _validate_table_prefix


def _load_asyncpg() -> tuple[Any, type[BaseException]]:
    try:
        import asyncpg
    except ImportError as exc:
        raise ImportError(
            "asyncpg is required to use AsyncPostgresBackend. "
            "Install corpulse[postgres-async]."
        ) from exc
    return asyncpg, asyncpg.PostgresError


class AsyncPostgresBackend:
    def __init__(
        self,
        pool,
        error_cls,
        *,
        schema: str | None = None,
        table_prefix: str = "",
    ):
        self._pool = pool
        self._error_cls = error_cls
        self._schema = _validate_schema(schema)
        self._table_prefix = _validate_table_prefix(table_prefix)
        self._closed = False

    @classmethod
    async def create(
        cls,
        dsn: str,
        *,
        min_size: int = 2,
        max_size: int = 10,
        schema: str | None = None,
        table_prefix: str = "",
    ) -> AsyncPostgresBackend:
        schema = _validate_schema(schema)
        table_prefix = _validate_table_prefix(table_prefix)
        asyncpg, error_cls = _load_asyncpg()
        pool = await asyncpg.create_pool(
            _normalize_postgres_dsn(dsn),
            min_size=min_size,
            max_size=max_size,
        )
        backend = cls(pool, error_cls, schema=schema, table_prefix=table_prefix)
        await backend._initialize()
        return backend

    def _t(self, name: str) -> str:
        return _qualified_name(name, schema=self._schema, prefix=self._table_prefix)

    async def _initialize(self) -> None:
        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    for statement in build_schema_sql(
                        schema=self._schema, prefix=self._table_prefix
                    ).split(";"):
                        statement = statement.strip()
                        if not statement:
                            continue
                        await conn.execute(statement)
        except self._error_cls as exc:
            raise StorageBackendError(str(exc)) from exc

    async def _execute(self, sql: str, *args) -> None:
        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(sql, *args)
        except self._error_cls as exc:
            raise StorageBackendError(str(exc)) from exc

    async def _fetch(self, sql: str, *args):
        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    return await conn.fetch(sql, *args)
        except self._error_cls as exc:
            raise StorageBackendError(str(exc)) from exc

    async def upsert_document(
        self,
        doc_id: str,
        filename: str,
        embedding: bytes | None = None,
        embedded_at: float | None = None,
    ) -> None:
        await self._execute(
            f"""
            INSERT INTO {self._t("documents")} (doc_id, filename, embedding_vec, embedded_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (doc_id) DO UPDATE SET
                filename = EXCLUDED.filename,
                embedding_vec = COALESCE(EXCLUDED.embedding_vec, {self._t("documents")}.embedding_vec),
                embedded_at = COALESCE(EXCLUDED.embedded_at, {self._t("documents")}.embedded_at)
            """,
            doc_id,
            filename,
            embedding,
            embedded_at,
        )

    async def insert_retrieval(
        self,
        doc_id: str,
        query_hash: str,
        rank: int,
        score: float,
        retrieved_at: float,
    ) -> None:
        await self._execute(
            f"""
            INSERT INTO {self._t("retrievals")} (doc_id, query_hash, rank, score, retrieved_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            doc_id,
            query_hash,
            rank,
            score,
            retrieved_at,
        )

    async def insert_query_attempt(
        self,
        query_hash: str,
        result_count: int,
        attempted_at: float,
    ) -> None:
        await self._execute(
            f"""
            INSERT INTO {self._t("query_attempts")} (query_hash, result_count, attempted_at)
            VALUES ($1, $2, $3)
            """,
            query_hash,
            result_count,
            attempted_at,
        )

    async def insert_engagement(
        self,
        doc_id: str,
        event_type: str,
        engaged_at: float,
    ) -> None:
        await self._execute(
            f"""
            INSERT INTO {self._t("engagements")} (doc_id, event_type, engaged_at)
            VALUES ($1, $2, $3)
            """,
            doc_id,
            event_type,
            engaged_at,
        )

    async def insert_generation_trace(
        self,
        prompt_text: str,
        retrieved_context_refs: list[dict[str, object]],
        final_answer_text: str,
        evaluation_labels: list[str] | None,
        captured_at: float,
    ) -> None:
        await self._execute(
            f"""
            INSERT INTO {self._t("generation_traces")} (
                prompt_text,
                retrieved_context_refs,
                final_answer_text,
                evaluation_labels,
                captured_at
            )
            VALUES ($1, $2, $3, $4, $5)
            """,
            prompt_text,
            json.dumps(retrieved_context_refs),
            final_answer_text,
            json.dumps(evaluation_labels) if evaluation_labels is not None else None,
            captured_at,
        )

    async def update_source_timestamp(self, doc_id: str, updated_at: float) -> None:
        await self._execute(
            f"""
            UPDATE {self._t("documents")} SET source_updated_at = $1 WHERE doc_id = $2
            """,
            updated_at,
            doc_id,
        )

    async def delete_document(self, doc_id: str) -> None:
        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        f"DELETE FROM {self._t('retrievals')} WHERE doc_id = $1",
                        doc_id,
                    )
                    await conn.execute(
                        f"DELETE FROM {self._t('engagements')} WHERE doc_id = $1",
                        doc_id,
                    )
                    await conn.execute(
                        f"DELETE FROM {self._t('documents')} WHERE doc_id = $1",
                        doc_id,
                    )
        except self._error_cls as exc:
            raise StorageBackendError(str(exc)) from exc

    async def delete_generation_traces(
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
                placeholders.append(f"${len(params) + 1}")
                params.append(trace_id)
            clauses.append(f"id IN ({', '.join(placeholders)})")
        if prompt_text is not None:
            clauses.append(f"prompt_text = ${len(params) + 1}")
            params.append(prompt_text)
        if evaluation_label is not None:
            placeholder = f"${len(params) + 1}"
            clauses.append(f"evaluation_labels LIKE {placeholder}")
            params.append(f'%"{evaluation_label}"%')

        if not clauses:
            return

        sql = f"DELETE FROM {self._t('generation_traces')} WHERE {' OR '.join(clauses)}"
        await self._execute(sql, *params)

    async def all_documents(self) -> list[DocumentRow]:
        rows = await self._fetch(f"SELECT * FROM {self._t('documents')}")
        return [dict(row) for row in rows]

    async def retrieval_counts(self, since: float) -> list[RetrievalRow]:
        rows = await self._fetch(
            f"""
            SELECT doc_id, COUNT(*) AS cnt, AVG(rank) AS avg_rank, AVG(score) AS avg_score
            FROM {self._t("retrievals")} WHERE retrieved_at >= $1 GROUP BY doc_id
            """,
            since,
        )
        return [dict(row) for row in rows]

    async def query_counts(self, since: float) -> list[QueryRow]:
        rows = await self._fetch(
            f"""
            SELECT query_hash, COUNT(*) AS cnt,
                   AVG(rank) AS avg_rank, AVG(score) AS avg_score,
                   MIN(rank) AS min_rank, MAX(rank) AS max_rank,
                   MIN(score) AS min_score, MAX(score) AS max_score,
                   MIN(retrieved_at) AS first_retrieved_at,
                   MAX(retrieved_at) AS last_retrieved_at
            FROM {self._t("retrievals")} WHERE retrieved_at >= $1
            GROUP BY query_hash
            ORDER BY query_hash
            """,
            since,
        )
        return [dict(row) for row in rows]

    async def query_attempt_counts(self, since: float) -> list[QueryAttemptRow]:
        rows = await self._fetch(
            f"""
            SELECT query_hash, COUNT(*) AS cnt,
                   SUM(CASE WHEN result_count > 0 THEN 1 ELSE 0 END) AS result_cnt,
                   MIN(attempted_at) AS first_attempted_at,
                   MAX(attempted_at) AS last_attempted_at
            FROM {self._t("query_attempts")} WHERE attempted_at >= $1
            GROUP BY query_hash
            ORDER BY query_hash
            """,
            since,
        )
        return [dict(row) for row in rows]

    async def engagement_counts(self, since: float) -> list[EngagementRow]:
        rows = await self._fetch(
            f"""
            SELECT doc_id, COUNT(*) AS cnt FROM {self._t("engagements")} WHERE engaged_at >= $1 GROUP BY doc_id
            """,
            since,
        )
        return [dict(row) for row in rows]

    async def engagement_event_counts(self, since: float) -> list[EngagementEventRow]:
        rows = await self._fetch(
            f"""
            SELECT event_type, COUNT(*) AS cnt
            FROM {self._t("engagements")}
            WHERE engaged_at >= $1
            GROUP BY event_type
            ORDER BY event_type
            """,
            since,
        )
        return [dict(row) for row in rows]

    async def generation_traces(self, since: float) -> list[GenerationTraceRow]:
        rows = await self._fetch(
            f"""
            SELECT id AS trace_id,
                   prompt_text,
                   retrieved_context_refs,
                   final_answer_text,
                   evaluation_labels,
                   captured_at
            FROM {self._t("generation_traces")}
            WHERE captured_at >= $1
            ORDER BY captured_at, id
            """,
            since,
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

    async def all_embeddings(self) -> list[EmbeddingRow]:
        rows = await self._fetch(
            f"""
            SELECT doc_id, filename, embedding_vec FROM {self._t("documents")} WHERE embedding_vec IS NOT NULL
            """
        )
        return [dict(row) for row in rows]

    async def close(self) -> None:
        if self._closed:
            return
        await self._pool.close()
        self._closed = True

    async def __aenter__(self) -> AsyncPostgresBackend:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
