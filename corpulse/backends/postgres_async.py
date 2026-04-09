from __future__ import annotations

from typing import Any

from .base import (
    DocumentRow,
    EmbeddingRow,
    EngagementRow,
    RetrievalRow,
    StorageBackendError,
)
from .postgres import SCHEMA

_SCHEMA_STATEMENTS = [statement.strip() for statement in SCHEMA.split(";") if statement.strip()]


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
    def __init__(self, pool, error_cls):
        self._pool = pool
        self._error_cls = error_cls
        self._closed = False

    @classmethod
    async def create(
        cls,
        dsn: str,
        *,
        min_size: int = 2,
        max_size: int = 10,
    ) -> AsyncPostgresBackend:
        asyncpg, error_cls = _load_asyncpg()
        pool = await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)
        backend = cls(pool, error_cls)
        await backend._initialize()
        return backend

    async def _initialize(self) -> None:
        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    for statement in _SCHEMA_STATEMENTS:
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
            """
            INSERT INTO documents (doc_id, filename, embedding_vec, embedded_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (doc_id) DO UPDATE SET
                filename = EXCLUDED.filename,
                embedding_vec = COALESCE(EXCLUDED.embedding_vec, documents.embedding_vec),
                embedded_at = COALESCE(EXCLUDED.embedded_at, documents.embedded_at)
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
            """
            INSERT INTO retrievals (doc_id, query_hash, rank, score, retrieved_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            doc_id,
            query_hash,
            rank,
            score,
            retrieved_at,
        )

    async def insert_engagement(
        self,
        doc_id: str,
        event_type: str,
        engaged_at: float,
    ) -> None:
        await self._execute(
            """
            INSERT INTO engagements (doc_id, event_type, engaged_at)
            VALUES ($1, $2, $3)
            """,
            doc_id,
            event_type,
            engaged_at,
        )

    async def update_source_timestamp(self, doc_id: str, updated_at: float) -> None:
        await self._execute(
            """
            UPDATE documents SET source_updated_at = $1 WHERE doc_id = $2
            """,
            updated_at,
            doc_id,
        )

    async def all_documents(self) -> list[DocumentRow]:
        rows = await self._fetch("SELECT * FROM documents")
        return [dict(row) for row in rows]

    async def retrieval_counts(self, since: float) -> list[RetrievalRow]:
        rows = await self._fetch(
            """
            SELECT doc_id, COUNT(*) AS cnt, AVG(rank) AS avg_rank, AVG(score) AS avg_score
            FROM retrievals WHERE retrieved_at >= $1 GROUP BY doc_id
            """,
            since,
        )
        return [dict(row) for row in rows]

    async def engagement_counts(self, since: float) -> list[EngagementRow]:
        rows = await self._fetch(
            """
            SELECT doc_id, COUNT(*) AS cnt FROM engagements WHERE engaged_at >= $1 GROUP BY doc_id
            """,
            since,
        )
        return [dict(row) for row in rows]

    async def all_embeddings(self) -> list[EmbeddingRow]:
        rows = await self._fetch(
            """
            SELECT doc_id, filename, embedding_vec FROM documents WHERE embedding_vec IS NOT NULL
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
