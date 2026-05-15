from __future__ import annotations

import importlib.util
import os

import pytest

from corpulse.backends.base import StorageBackendError

try:
    from corpulse.backends.postgres_async import AsyncPostgresBackend
except ImportError:
    AsyncPostgresBackend = None


pytestmark = pytest.mark.skipif(
    AsyncPostgresBackend is None,
    reason="AsyncPostgresBackend not yet implemented",
)


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.split())


class FakeAsyncpgError(Exception):
    pass


class FakeAsyncpgConnection:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self.rows: dict[str, list[dict]] = {}
        self.error: Exception | None = None

    async def execute(self, sql, *args):
        normalized = _normalize_sql(sql)
        self.calls.append((normalized, args))
        if self.error is not None:
            raise self.error

    async def fetch(self, sql, *args):
        normalized = _normalize_sql(sql)
        self.calls.append((normalized, args))
        if self.error is not None:
            raise self.error
        return self.rows.get(normalized, [])

    def transaction(self):
        return _FakeTransaction()


class _FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None


class _FakeAcquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        return None


class FakeAsyncpgPool:
    def __init__(self, conn=None):
        self.conn = conn or FakeAsyncpgConnection()
        self.closed = False
        self.create_pool_kwargs = {}
        self.acquire_calls = 0

    def acquire(self):
        self.acquire_calls += 1
        return _FakeAcquire(self.conn)

    async def close(self):
        self.closed = True


class FakeAsyncpgModule:
    PostgresError = FakeAsyncpgError

    def __init__(self, pool=None):
        self.pool = pool or FakeAsyncpgPool()
        self.create_pool_calls = []

    async def create_pool(self, dsn, *, min_size, max_size):
        self.create_pool_calls.append(
            {"dsn": dsn, "min_size": min_size, "max_size": max_size}
        )
        self.pool.create_pool_kwargs = {
            "dsn": dsn,
            "min_size": min_size,
            "max_size": max_size,
        }
        return self.pool


def _install_fake_asyncpg(monkeypatch, pool=None):
    fake_module = FakeAsyncpgModule(pool=pool)
    monkeypatch.setattr(
        "corpulse.backends.postgres_async._load_asyncpg",
        lambda: (fake_module, FakeAsyncpgError),
    )
    return fake_module


async def _build_backend(monkeypatch, pool=None, **kwargs):
    fake_module = _install_fake_asyncpg(monkeypatch, pool=pool)
    backend = await AsyncPostgresBackend.create("postgresql://test", **kwargs)
    return backend, fake_module


@pytest.mark.parametrize(
    ("input_dsn", "expected"),
    [
        ("postgresql+asyncpg://test", "postgresql://test"),
        (
            "postgresql+asyncpg://u:p%40x@h/db?sslmode=require",
            "postgresql://u:p%40x@h/db?sslmode=require",
        ),
        ("postgresql://u:p@h/db", "postgresql://u:p@h/db"),
        ("postgres+asyncpg://u@[::1]:5432/db", "postgres://u@[::1]:5432/db"),
    ],
)
async def test_dsn_normalization_async(monkeypatch, input_dsn, expected):
    fake_module = _install_fake_asyncpg(monkeypatch)

    backend = await AsyncPostgresBackend.create(input_dsn)

    assert fake_module.create_pool_calls == [
        {"dsn": expected, "min_size": 2, "max_size": 10}
    ]
    await backend.close()


async def test_async_postgres_backend_requires_asyncpg(monkeypatch):
    def raising_loader():
        raise ImportError("Install it with: pip install corpulse[postgres-async]")

    monkeypatch.setattr("corpulse.backends.postgres_async._load_asyncpg", raising_loader)

    with pytest.raises(ImportError, match=r"pip install corpulse\[postgres-async\]"):
        await AsyncPostgresBackend.create("postgresql://test")


async def test_async_postgres_backend_creates_pool(monkeypatch):
    backend, fake_module = await _build_backend(monkeypatch)

    assert fake_module.create_pool_calls == [
        {"dsn": "postgresql://test", "min_size": 2, "max_size": 10}
    ]
    await backend.close()


async def test_async_postgres_backend_custom_pool_size(monkeypatch):
    backend, fake_module = await _build_backend(monkeypatch, min_size=5, max_size=20)

    assert fake_module.create_pool_calls == [
        {"dsn": "postgresql://test", "min_size": 5, "max_size": 20}
    ]
    await backend.close()


@pytest.mark.parametrize(
    ("kwargs", "field"),
    [
        ({"schema": "bad-name"}, "schema"),
        ({"schema": "tenant.one"}, "schema"),
        ({"table_prefix": "tenant-"}, "table_prefix"),
        ({"table_prefix": "1tenant_"}, "table_prefix"),
    ],
)
async def test_async_postgres_backend_rejects_invalid_tenancy_identifiers_before_pool_init(
    monkeypatch, kwargs, field
):
    loader_calls = 0

    def fake_loader():
        nonlocal loader_calls
        loader_calls += 1
        raise AssertionError("asyncpg loader should not run")

    monkeypatch.setattr("corpulse.backends.postgres_async._load_asyncpg", fake_loader)

    with pytest.raises(ValueError, match=field):
        await AsyncPostgresBackend.create("postgresql://test", **kwargs)

    assert loader_calls == 0


async def test_async_postgres_backend_initializes_schema(monkeypatch):
    backend, fake_module = await _build_backend(monkeypatch)

    assert fake_module.pool.conn.calls
    assert any("CREATE TABLE IF NOT EXISTS documents" in sql for sql, _ in fake_module.pool.conn.calls)
    assert any("CREATE TABLE IF NOT EXISTS query_attempts" in sql for sql, _ in fake_module.pool.conn.calls)
    assert any("CREATE TABLE IF NOT EXISTS generation_traces" in sql for sql, _ in fake_module.pool.conn.calls)
    assert any("CREATE TABLE IF NOT EXISTS rag_request_traces" in sql for sql, _ in fake_module.pool.conn.calls)
    await backend.close()


async def test_async_postgres_backend_uses_schema_qualified_names(monkeypatch):
    backend, fake_module = await _build_backend(monkeypatch, schema="tenant_alpha")

    await backend.upsert_document("d1", "f1.md", b"vec", 1.0)
    await backend.insert_retrieval("d1", "h", 1, 0.9, 25.0)
    await backend.insert_query_attempt("h", 1, 24.0)
    await backend.insert_engagement("d1", "opened", 30.0)
    await backend.insert_generation_trace("prompt", [{"doc_id": "d1"}], "answer", ["grounded"], 31.0)
    await backend.insert_rag_request_trace(
        "req-1",
        "session-1",
        "What is happening?",
        "hash-1",
        123,
        45,
        [{"type": "system_prompt", "token_count": 12, "refs": None, "content_hash": "sp-1", "metadata": {"scope": "system"}}],
        {"ttft_ms": 210.0, "tpot_ms": 18.0, "retrieval_ms": 42.0},
        False,
        None,
        32.0,
    )
    await backend.update_source_timestamp("d1", 40.0)
    await backend.delete_document("d1")
    await backend.all_documents()
    await backend.query_attempt_counts(0.0)
    await backend.query_counts(0.0)
    await backend.engagement_event_counts(0.0)
    await backend.generation_traces(0.0)
    await backend.rag_request_traces(0.0)

    executed_sql = "\n".join(sql for sql, _ in fake_module.pool.conn.calls)
    assert "CREATE SCHEMA IF NOT EXISTS tenant_alpha" in executed_sql
    assert "INSERT INTO tenant_alpha.documents" in executed_sql
    assert "INSERT INTO tenant_alpha.retrievals" in executed_sql
    assert "INSERT INTO tenant_alpha.query_attempts" in executed_sql
    assert "INSERT INTO tenant_alpha.engagements" in executed_sql
    assert "INSERT INTO tenant_alpha.generation_traces" in executed_sql
    assert "INSERT INTO tenant_alpha.rag_request_traces" in executed_sql
    assert "UPDATE tenant_alpha.documents SET source_updated_at = $1 WHERE doc_id = $2" in executed_sql
    assert "DELETE FROM tenant_alpha.retrievals WHERE doc_id = $1" in executed_sql
    assert "SELECT * FROM tenant_alpha.documents" in executed_sql
    assert "FROM tenant_alpha.query_attempts WHERE attempted_at >= $1 GROUP BY query_hash" in executed_sql
    assert "FROM tenant_alpha.retrievals WHERE retrieved_at >= $1 GROUP BY query_hash" in executed_sql
    assert "FROM tenant_alpha.engagements WHERE engaged_at >= $1 GROUP BY event_type ORDER BY event_type" in executed_sql
    assert "FROM tenant_alpha.generation_traces WHERE captured_at >= $1 ORDER BY captured_at, id" in executed_sql
    assert "FROM tenant_alpha.rag_request_traces WHERE captured_at >= $1 ORDER BY captured_at, id" in executed_sql
    await backend.close()


async def test_async_postgres_backend_uses_prefixed_names(monkeypatch):
    backend, fake_module = await _build_backend(monkeypatch, table_prefix="tenant_abc_")

    await backend.upsert_document("d1", "f1.md", b"vec", 1.0)
    await backend.insert_retrieval("d1", "h", 1, 0.9, 25.0)
    await backend.insert_query_attempt("h", 1, 24.0)
    await backend.insert_engagement("d1", "opened", 30.0)
    await backend.insert_generation_trace("prompt", [{"doc_id": "d1"}], "answer", ["grounded"], 31.0)
    await backend.insert_rag_request_trace(
        "req-1",
        "session-1",
        "What is happening?",
        "hash-1",
        123,
        45,
        [{"type": "system_prompt", "token_count": 12, "refs": None, "content_hash": "sp-1", "metadata": {"scope": "system"}}],
        {"ttft_ms": 210.0, "tpot_ms": 18.0, "retrieval_ms": 42.0},
        False,
        None,
        32.0,
    )
    await backend.all_embeddings()
    await backend.query_attempt_counts(0.0)
    await backend.query_counts(0.0)
    await backend.engagement_event_counts(0.0)
    await backend.generation_traces(0.0)
    await backend.rag_request_traces(0.0)

    executed_sql = "\n".join(sql for sql, _ in fake_module.pool.conn.calls)
    assert "CREATE TABLE IF NOT EXISTS tenant_abc_documents" in executed_sql
    assert "INSERT INTO tenant_abc_documents" in executed_sql
    assert "INSERT INTO tenant_abc_retrievals" in executed_sql
    assert "INSERT INTO tenant_abc_query_attempts" in executed_sql
    assert "INSERT INTO tenant_abc_engagements" in executed_sql
    assert "INSERT INTO tenant_abc_generation_traces" in executed_sql
    assert "INSERT INTO tenant_abc_rag_request_traces" in executed_sql
    assert "FROM tenant_abc_documents WHERE embedding_vec IS NOT NULL" in executed_sql
    assert "FROM tenant_abc_query_attempts WHERE attempted_at >= $1 GROUP BY query_hash" in executed_sql
    assert "FROM tenant_abc_retrievals WHERE retrieved_at >= $1 GROUP BY query_hash" in executed_sql
    assert "FROM tenant_abc_engagements WHERE engaged_at >= $1 GROUP BY event_type ORDER BY event_type" in executed_sql
    assert "FROM tenant_abc_generation_traces WHERE captured_at >= $1 ORDER BY captured_at, id" in executed_sql
    assert "FROM tenant_abc_rag_request_traces WHERE captured_at >= $1 ORDER BY captured_at, id" in executed_sql
    await backend.close()


async def test_async_postgres_backend_prefix_only_mode_rewrites_all_query_paths(monkeypatch):
    pool = FakeAsyncpgPool()
    pool.conn.rows[_normalize_sql("SELECT * FROM tenant_abc_documents")] = [
        {"doc_id": "tenant-doc", "filename": "tenant.md"}
    ]
    pool.conn.rows[
        _normalize_sql(
            """
            SELECT doc_id, COUNT(*) AS cnt, AVG(rank) AS avg_rank, AVG(score) AS avg_score
            FROM tenant_abc_retrievals WHERE retrieved_at >= $1 GROUP BY doc_id
            """
        )
    ] = [{"doc_id": "tenant-doc", "cnt": 1, "avg_rank": 1.0, "avg_score": 0.75}]
    pool.conn.rows[
        _normalize_sql(
            """
            SELECT query_hash, COUNT(*) AS cnt,
                   SUM(CASE WHEN result_count > 0 THEN 1 ELSE 0 END) AS result_cnt,
                   MIN(attempted_at) AS first_attempted_at,
                   MAX(attempted_at) AS last_attempted_at
            FROM tenant_abc_query_attempts WHERE attempted_at >= $1
            GROUP BY query_hash
            ORDER BY query_hash
            """
        )
    ] = [
        {
            "query_hash": "hash",
            "cnt": 1,
            "result_cnt": 1,
            "first_attempted_at": 1.5,
            "last_attempted_at": 1.5,
        }
    ]
    pool.conn.rows[
        _normalize_sql(
            """
            SELECT query_hash, COUNT(*) AS cnt,
                   AVG(rank) AS avg_rank, AVG(score) AS avg_score,
                   MIN(rank) AS min_rank, MAX(rank) AS max_rank,
                   MIN(score) AS min_score, MAX(score) AS max_score,
                   MIN(retrieved_at) AS first_retrieved_at,
                   MAX(retrieved_at) AS last_retrieved_at
            FROM tenant_abc_retrievals WHERE retrieved_at >= $1
            GROUP BY query_hash
            ORDER BY query_hash
            """
        )
    ] = [
        {
            "query_hash": "hash",
            "cnt": 1,
            "avg_rank": 1.0,
            "avg_score": 0.75,
            "min_rank": 1,
            "max_rank": 1,
            "min_score": 0.75,
            "max_score": 0.75,
            "first_retrieved_at": 2.0,
            "last_retrieved_at": 2.0,
        }
    ]
    pool.conn.rows[
        _normalize_sql(
            """
            SELECT doc_id, COUNT(*) AS cnt FROM tenant_abc_engagements WHERE engaged_at >= $1 GROUP BY doc_id
            """
        )
    ] = [{"doc_id": "tenant-doc", "cnt": 1}]
    pool.conn.rows[
        _normalize_sql(
            """
            SELECT event_type, COUNT(*) AS cnt
            FROM tenant_abc_engagements
            WHERE engaged_at >= $1
            GROUP BY event_type
            ORDER BY event_type
            """
        )
    ] = [{"event_type": "opened", "cnt": 1}]
    pool.conn.rows[
        _normalize_sql(
            """
            SELECT id AS trace_id,
                   prompt_text,
                   retrieved_context_refs,
                   final_answer_text,
                   evaluation_labels,
                   captured_at
            FROM tenant_abc_generation_traces
            WHERE captured_at >= $1
            ORDER BY captured_at, id
            """
        )
    ] = [
        {
            "trace_id": 1,
            "prompt_text": "prompt-1",
            "retrieved_context_refs": '[{"doc_id": "tenant-doc", "rank": 1}]',
            "final_answer_text": "answer-1",
            "evaluation_labels": '["grounded"]',
            "captured_at": 4.0,
        }
    ]
    pool.conn.rows[
        _normalize_sql(
            """
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
            FROM tenant_abc_rag_request_traces
            WHERE captured_at >= $1
            ORDER BY captured_at, id
            """
        )
    ] = [
        {
            "trace_id": 1,
            "request_id": "req-1",
            "session_id": "session-1",
            "query_text": "What is happening?",
            "query_hash": "hash-1",
            "input_token_count": 123,
            "output_token_count": 45,
            "components": '[{"type": "system_prompt", "token_count": 12, "refs": null, "content_hash": "sp-1", "metadata": {"scope": "system"}}]',
            "timings": '{"ttft_ms": 210.0, "tpot_ms": 18.0, "retrieval_ms": 42.0}',
            "timeout": False,
            "error": None,
            "captured_at": 3.5,
        }
    ]
    pool.conn.rows[
        _normalize_sql(
            """
            SELECT doc_id, filename, embedding_vec FROM tenant_abc_documents WHERE embedding_vec IS NOT NULL
            """
        )
    ] = [{"doc_id": "tenant-doc", "filename": "tenant.md", "embedding_vec": b"vec"}]
    backend, fake_module = await _build_backend(monkeypatch, pool=pool, table_prefix="tenant_abc_")

    await backend.upsert_document("tenant-doc", "tenant.md", b"vec", 1.0)
    await backend.insert_retrieval("tenant-doc", "hash", 1, 0.75, 2.0)
    await backend.insert_query_attempt("hash", 1, 1.5)
    await backend.insert_engagement("tenant-doc", "opened", 3.0)
    await backend.insert_generation_trace("prompt-1", [{"doc_id": "tenant-doc", "rank": 1}], "answer-1", ["grounded"], 4.0)
    await backend.insert_rag_request_trace(
        "req-1",
        "session-1",
        "What is happening?",
        "hash-1",
        123,
        45,
        [{"type": "system_prompt", "token_count": 12, "refs": None, "content_hash": "sp-1", "metadata": {"scope": "system"}}],
        {"ttft_ms": 210.0, "tpot_ms": 18.0, "retrieval_ms": 42.0},
        False,
        None,
        3.5,
    )
    await backend.update_source_timestamp("tenant-doc", 4.0)
    await backend.delete_document("tenant-doc")

    assert await backend.all_documents() == [{"doc_id": "tenant-doc", "filename": "tenant.md"}]
    assert await backend.retrieval_counts(0.0) == [
        {"doc_id": "tenant-doc", "cnt": 1, "avg_rank": 1.0, "avg_score": 0.75}
    ]
    assert await backend.query_attempt_counts(0.0) == [
        {
            "query_hash": "hash",
            "cnt": 1,
            "result_cnt": 1,
            "first_attempted_at": 1.5,
            "last_attempted_at": 1.5,
        }
    ]
    assert await backend.query_counts(0.0) == [
        {
            "query_hash": "hash",
            "cnt": 1,
            "avg_rank": 1.0,
            "avg_score": 0.75,
            "min_rank": 1,
            "max_rank": 1,
            "min_score": 0.75,
            "max_score": 0.75,
            "first_retrieved_at": 2.0,
            "last_retrieved_at": 2.0,
        }
    ]
    assert await backend.engagement_counts(0.0) == [{"doc_id": "tenant-doc", "cnt": 1}]
    assert await backend.engagement_event_counts(0.0) == [
        {"event_type": "opened", "cnt": 1}
    ]
    assert await backend.generation_traces(0.0) == [
        {
            "trace_id": 1,
            "prompt_text": "prompt-1",
            "retrieved_context_refs": [{"doc_id": "tenant-doc", "rank": 1}],
            "final_answer_text": "answer-1",
            "evaluation_labels": ["grounded"],
            "captured_at": 4.0,
        }
    ]
    assert await backend.rag_request_traces(0.0) == [
        {
            "trace_id": 1,
            "request_id": "req-1",
            "session_id": "session-1",
            "query_text": "What is happening?",
            "query_hash": "hash-1",
            "input_token_count": 123,
            "output_token_count": 45,
            "components": [
                {
                    "type": "system_prompt",
                    "token_count": 12,
                    "refs": None,
                    "content_hash": "sp-1",
                    "metadata": {"scope": "system"},
                }
            ],
            "timings": {
                "ttft_ms": 210.0,
                "tpot_ms": 18.0,
                "retrieval_ms": 42.0,
            },
            "timeout": False,
            "error": None,
            "captured_at": 3.5,
        }
    ]
    assert await backend.all_embeddings() == [
        {"doc_id": "tenant-doc", "filename": "tenant.md", "embedding_vec": b"vec"}
    ]

    executed_sql = "\n".join(sql for sql, _ in fake_module.pool.conn.calls)
    assert "INSERT INTO tenant_abc_documents" in executed_sql
    assert "INSERT INTO tenant_abc_retrievals" in executed_sql
    assert "INSERT INTO tenant_abc_query_attempts" in executed_sql
    assert "INSERT INTO tenant_abc_engagements" in executed_sql
    assert "INSERT INTO tenant_abc_generation_traces" in executed_sql
    assert "INSERT INTO tenant_abc_rag_request_traces" in executed_sql
    assert "UPDATE tenant_abc_documents SET source_updated_at = $1 WHERE doc_id = $2" in executed_sql
    assert "DELETE FROM tenant_abc_retrievals WHERE doc_id = $1" in executed_sql
    assert "DELETE FROM tenant_abc_engagements WHERE doc_id = $1" in executed_sql
    assert "DELETE FROM tenant_abc_documents WHERE doc_id = $1" in executed_sql
    assert "SELECT * FROM tenant_abc_documents" in executed_sql
    assert "FROM tenant_abc_retrievals WHERE retrieved_at >= $1 GROUP BY doc_id" in executed_sql
    assert "FROM tenant_abc_engagements WHERE engaged_at >= $1 GROUP BY doc_id" in executed_sql
    assert "FROM tenant_abc_engagements WHERE engaged_at >= $1 GROUP BY event_type ORDER BY event_type" in executed_sql
    assert "FROM tenant_abc_generation_traces WHERE captured_at >= $1 ORDER BY captured_at, id" in executed_sql
    assert "FROM tenant_abc_rag_request_traces WHERE captured_at >= $1 ORDER BY captured_at, id" in executed_sql
    assert "FROM tenant_abc_documents WHERE embedding_vec IS NOT NULL" in executed_sql
    assert "tenant_abc.documents" not in executed_sql
    await backend.close()

async def test_async_postgres_backend_upsert_document(monkeypatch):
    backend, fake_module = await _build_backend(monkeypatch)

    await backend.upsert_document("d1", "f1.md", b"vec", 1.0)

    assert any("ON CONFLICT (doc_id)" in sql and args == ("d1", "f1.md", b"vec", 1.0) for sql, args in fake_module.pool.conn.calls)
    await backend.close()


async def test_async_postgres_backend_insert_retrieval(monkeypatch):
    backend, fake_module = await _build_backend(monkeypatch)

    await backend.insert_retrieval("d1", "h", 1, 0.9, 25.0)

    assert any("INSERT INTO retrievals" in sql and args == ("d1", "h", 1, 0.9, 25.0) for sql, args in fake_module.pool.conn.calls)
    await backend.close()


async def test_async_postgres_backend_insert_query_attempt(monkeypatch):
    backend, fake_module = await _build_backend(monkeypatch)

    await backend.insert_query_attempt("h", 0, 25.0)

    assert any(
        "INSERT INTO query_attempts" in sql and args == ("h", 0, 25.0)
        for sql, args in fake_module.pool.conn.calls
    )
    await backend.close()


async def test_async_postgres_backend_insert_engagement(monkeypatch):
    backend, fake_module = await _build_backend(monkeypatch)

    await backend.insert_engagement("d1", "opened", 30.0)

    assert any("INSERT INTO engagements" in sql and args == ("d1", "opened", 30.0) for sql, args in fake_module.pool.conn.calls)
    await backend.close()


async def test_async_postgres_backend_insert_generation_trace(monkeypatch):
    backend, fake_module = await _build_backend(monkeypatch)

    await backend.insert_generation_trace(
        "prompt",
        [{"doc_id": "d1"}],
        "answer",
        ["grounded"],
        30.0,
    )
    await backend.insert_rag_request_trace(
        "req-1",
        "session-1",
        "What is happening?",
        "hash-1",
        123,
        45,
        [{"type": "system_prompt", "token_count": 12, "refs": None, "content_hash": "sp-1", "metadata": {"scope": "system"}}],
        {"ttft_ms": 210.0, "tpot_ms": 18.0, "retrieval_ms": 42.0},
        False,
        None,
        31.0,
    )

    assert any(
        "INSERT INTO generation_traces" in sql
        and args == ("prompt", '[{"doc_id": "d1"}]', "answer", '["grounded"]', 30.0)
        for sql, args in fake_module.pool.conn.calls
    )
    assert any(
        "INSERT INTO rag_request_traces" in sql
        and args == (
            "req-1",
            "session-1",
            "What is happening?",
            "hash-1",
            123,
            45,
            '[{"type": "system_prompt", "token_count": 12, "refs": null, "content_hash": "sp-1", "metadata": {"scope": "system"}}]',
            '{"ttft_ms": 210.0, "tpot_ms": 18.0, "retrieval_ms": 42.0}',
            False,
            None,
            31.0,
        )
        for sql, args in fake_module.pool.conn.calls
    )
    await backend.close()


async def test_async_postgres_backend_update_source_timestamp(monkeypatch):
    backend, fake_module = await _build_backend(monkeypatch)

    await backend.update_source_timestamp("d1", 40.0)

    assert any("UPDATE documents SET source_updated_at = $1 WHERE doc_id = $2" in sql and args == (40.0, "d1") for sql, args in fake_module.pool.conn.calls)
    await backend.close()


async def test_async_postgres_backend_delete_document(monkeypatch):
    backend, fake_module = await _build_backend(monkeypatch)

    await backend.delete_document("d1")

    assert fake_module.pool.conn.calls[-3:] == [
        ("DELETE FROM retrievals WHERE doc_id = $1", ("d1",)),
        ("DELETE FROM engagements WHERE doc_id = $1", ("d1",)),
        ("DELETE FROM documents WHERE doc_id = $1", ("d1",)),
    ]
    await backend.close()


async def test_async_postgres_backend_all_documents(monkeypatch):
    pool = FakeAsyncpgPool()
    pool.conn.rows[_normalize_sql("SELECT * FROM documents")] = [
        {
            "doc_id": "doc-1",
            "filename": "doc-1.md",
            "embedding_vec": b"vec",
            "embedded_at": 12.5,
            "source_updated_at": 40.0,
        }
    ]
    backend, _ = await _build_backend(monkeypatch, pool=pool)

    assert await backend.all_documents() == [
        {
            "doc_id": "doc-1",
            "filename": "doc-1.md",
            "embedding_vec": b"vec",
            "embedded_at": 12.5,
            "source_updated_at": 40.0,
        }
    ]
    await backend.close()


async def test_async_postgres_backend_retrieval_counts(monkeypatch):
    pool = FakeAsyncpgPool()
    pool.conn.rows[
        _normalize_sql(
            """
            SELECT doc_id, COUNT(*) AS cnt, AVG(rank) AS avg_rank, AVG(score) AS avg_score
            FROM retrievals WHERE retrieved_at >= $1 GROUP BY doc_id
            """
        )
    ] = [{"doc_id": "doc-1", "cnt": 1, "avg_rank": 1.0, "avg_score": 0.9}]
    backend, _ = await _build_backend(monkeypatch, pool=pool)

    assert await backend.retrieval_counts(0.0) == [
        {"doc_id": "doc-1", "cnt": 1, "avg_rank": 1.0, "avg_score": 0.9}
    ]
    await backend.close()


async def test_async_postgres_backend_query_attempt_counts(monkeypatch):
    pool = FakeAsyncpgPool()
    pool.conn.rows[
        _normalize_sql(
            """
            SELECT query_hash, COUNT(*) AS cnt,
                   SUM(CASE WHEN result_count > 0 THEN 1 ELSE 0 END) AS result_cnt,
                   MIN(attempted_at) AS first_attempted_at,
                   MAX(attempted_at) AS last_attempted_at
            FROM query_attempts WHERE attempted_at >= $1
            GROUP BY query_hash
            ORDER BY query_hash
            """
        )
    ] = [
        {
            "query_hash": "hash",
            "cnt": 2,
            "result_cnt": 1,
            "first_attempted_at": 20.0,
            "last_attempted_at": 21.0,
        }
    ]
    backend, _ = await _build_backend(monkeypatch, pool=pool)

    assert await backend.query_attempt_counts(0.0) == [
        {
            "query_hash": "hash",
            "cnt": 2,
            "result_cnt": 1,
            "first_attempted_at": 20.0,
            "last_attempted_at": 21.0,
        }
    ]
    await backend.close()


async def test_async_postgres_backend_engagement_counts(monkeypatch):
    pool = FakeAsyncpgPool()
    pool.conn.rows[
        _normalize_sql(
            """
            SELECT doc_id, COUNT(*) AS cnt FROM engagements WHERE engaged_at >= $1 GROUP BY doc_id
            """
        )
    ] = [{"doc_id": "doc-1", "cnt": 1}]
    backend, _ = await _build_backend(monkeypatch, pool=pool)

    assert await backend.engagement_counts(0.0) == [{"doc_id": "doc-1", "cnt": 1}]
    await backend.close()


async def test_async_postgres_backend_engagement_event_counts(monkeypatch):
    pool = FakeAsyncpgPool()
    pool.conn.rows[
        _normalize_sql(
            """
            SELECT event_type, COUNT(*) AS cnt
            FROM engagements
            WHERE engaged_at >= $1
            GROUP BY event_type
            ORDER BY event_type
            """
        )
    ] = [
        {"event_type": "clicked", "cnt": 2},
        {"event_type": "opened", "cnt": 1},
    ]
    backend, _ = await _build_backend(monkeypatch, pool=pool)

    assert await backend.engagement_event_counts(0.0) == [
        {"event_type": "clicked", "cnt": 2},
        {"event_type": "opened", "cnt": 1},
    ]
    await backend.close()


async def test_async_postgres_backend_all_embeddings(monkeypatch):
    pool = FakeAsyncpgPool()
    pool.conn.rows[
        _normalize_sql(
            """
            SELECT doc_id, filename, embedding_vec FROM documents WHERE embedding_vec IS NOT NULL
            """
        )
    ] = [{"doc_id": "doc-1", "filename": "doc-1.md", "embedding_vec": b"vec"}]
    backend, _ = await _build_backend(monkeypatch, pool=pool)

    assert await backend.all_embeddings() == [
        {"doc_id": "doc-1", "filename": "doc-1.md", "embedding_vec": b"vec"}
    ]
    await backend.close()


async def test_async_postgres_backend_translates_driver_errors(monkeypatch):
    pool = FakeAsyncpgPool()
    backend, _ = await _build_backend(monkeypatch, pool=pool)
    pool.conn.error = FakeAsyncpgError("boom")

    with pytest.raises(StorageBackendError, match="boom") as exc_info:
        await backend.all_documents()

    assert isinstance(exc_info.value.__cause__, FakeAsyncpgError)
    await backend.close()


async def test_async_postgres_backend_close_idempotent(monkeypatch):
    backend, fake_module = await _build_backend(monkeypatch)

    await backend.close()
    await backend.close()

    assert fake_module.pool.closed is True


async def test_async_postgres_backend_async_context_manager(monkeypatch):
    fake_module = _install_fake_asyncpg(monkeypatch)
    backend = await AsyncPostgresBackend.create("postgresql://test")

    async with backend as active_backend:
        assert active_backend is backend

    assert fake_module.pool.closed is True


async def test_async_postgres_backend_uses_pool_acquire(monkeypatch):
    pool = FakeAsyncpgPool()
    backend, _ = await _build_backend(monkeypatch, pool=pool)

    await backend.upsert_document("d1", "f1.md", b"vec", 1.0)
    await backend.insert_retrieval("d1", "h", 1, 0.9, 25.0)
    await backend.insert_query_attempt("h", 1, 24.0)
    await backend.insert_engagement("d1", "opened", 30.0)
    await backend.update_source_timestamp("d1", 40.0)
    await backend.delete_document("d1")
    await backend.all_documents()
    await backend.query_attempt_counts(0.0)
    await backend.retrieval_counts(0.0)
    await backend.engagement_counts(0.0)
    await backend.engagement_event_counts(0.0)
    await backend.all_embeddings()

    assert pool.acquire_calls >= 10
    await backend.close()


@pytest.mark.skipif(
    not os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")
    or importlib.util.find_spec("asyncpg") is None,
    reason="requires CORPULSE_POSTGRES_TEST_CONNINFO and asyncpg",
)
async def test_live_async_postgres_backend_round_trip():
    from corpulse.backends import AsyncPostgresBackend as LiveBackend

    backend = await LiveBackend.create(os.environ["CORPULSE_POSTGRES_TEST_CONNINFO"])
    try:
        async with backend._pool.acquire() as conn:
            await conn.execute(
                "TRUNCATE engagements, retrievals, query_attempts, documents RESTART IDENTITY"
            )

        await backend.upsert_document("doc-1", "doc-1.md", embedding=b"vec", embedded_at=12.5)
        await backend.insert_retrieval("doc-1", "hash", 1, 0.9, 25.0)
        await backend.insert_query_attempt("hash", 1, 24.0)
        await backend.insert_engagement("doc-1", "opened", 30.0)
        await backend.update_source_timestamp("doc-1", 40.0)

        assert await backend.all_documents() == [
            {
                "doc_id": "doc-1",
                "filename": "doc-1.md",
                "embedding_vec": b"vec",
                "embedded_at": 12.5,
                "source_updated_at": 40.0,
            }
        ]
        assert await backend.retrieval_counts(0.0) == [
            {"doc_id": "doc-1", "cnt": 1, "avg_rank": 1.0, "avg_score": 0.9}
        ]
        assert await backend.query_attempt_counts(0.0) == [
            {
                "query_hash": "hash",
                "cnt": 1,
                "result_cnt": 1,
                "first_attempted_at": 24.0,
                "last_attempted_at": 24.0,
            }
        ]
        assert await backend.query_counts(0.0) == [
            {
                "query_hash": "hash",
                "cnt": 1,
                "avg_rank": 1.0,
                "avg_score": 0.9,
                "min_rank": 1,
                "max_rank": 1,
                "min_score": 0.9,
                "max_score": 0.9,
                "first_retrieved_at": 25.0,
                "last_retrieved_at": 25.0,
            }
        ]
        assert await backend.engagement_counts(0.0) == [{"doc_id": "doc-1", "cnt": 1}]
        assert await backend.engagement_event_counts(0.0) == [
            {"event_type": "opened", "cnt": 1}
        ]
        assert await backend.all_embeddings() == [
            {"doc_id": "doc-1", "filename": "doc-1.md", "embedding_vec": b"vec"}
        ]
    finally:
        async with backend._pool.acquire() as conn:
            await conn.execute(
                "TRUNCATE engagements, retrievals, query_attempts, documents RESTART IDENTITY"
            )
        await backend.close()


@pytest.mark.skipif(
    not os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")
    or importlib.util.find_spec("asyncpg") is None,
    reason="requires CORPULSE_POSTGRES_TEST_CONNINFO and asyncpg",
)
async def test_live_async_postgres_backend_schema_isolation():
    from corpulse.backends import AsyncPostgresBackend as LiveBackend

    conninfo = os.environ["CORPULSE_POSTGRES_TEST_CONNINFO"]
    schema_a = f"tenant_async_a_{os.getpid()}"
    schema_b = f"tenant_async_b_{os.getpid()}"
    backend_a = await LiveBackend.create(conninfo, schema=schema_a)
    backend_b = await LiveBackend.create(conninfo, schema=schema_b)

    try:
        await backend_a.upsert_document("doc-a", "a.md", embedding=b"a", embedded_at=1.0)
        await backend_a.insert_retrieval("doc-a", "hash-a", 1, 0.9, 2.0)
        await backend_a.insert_query_attempt("hash-a", 1, 1.5)
        await backend_b.upsert_document("doc-b", "b.md", embedding=b"b", embedded_at=3.0)
        await backend_b.insert_retrieval("doc-b", "hash-b", 1, 0.8, 4.0)
        await backend_b.insert_query_attempt("hash-b", 1, 3.5)

        assert [doc["doc_id"] for doc in await backend_a.all_documents()] == ["doc-a"]
        assert [doc["doc_id"] for doc in await backend_b.all_documents()] == ["doc-b"]
        assert [row["doc_id"] for row in await backend_a.retrieval_counts(0.0)] == ["doc-a"]
        assert [row["doc_id"] for row in await backend_b.retrieval_counts(0.0)] == ["doc-b"]
        assert [row["query_hash"] for row in await backend_a.query_attempt_counts(0.0)] == ["hash-a"]
        assert [row["query_hash"] for row in await backend_b.query_attempt_counts(0.0)] == ["hash-b"]
    finally:
        async with backend_a._pool.acquire() as conn:
            await conn.execute(f"DROP SCHEMA IF EXISTS {schema_a} CASCADE")
            await conn.execute(f"DROP SCHEMA IF EXISTS {schema_b} CASCADE")
        await backend_a.close()
        await backend_b.close()
