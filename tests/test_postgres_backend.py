from __future__ import annotations

import importlib.util
import os

import pytest

from corpulse.backends.base import StorageBackendError
from corpulse.backends.postgres import PostgresBackend, build_schema_sql


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.split())


class FakePsycopgError(Exception):
    pass


EXPECTED_DEFAULT_SCHEMA_SQL = """
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


class FakeCursor:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self):
        self.calls: list[tuple[str, tuple | None]] = []
        self.rows: dict[str, list[dict]] = {}
        self.error: Exception | None = None

    def execute(self, sql: str, params=None):
        normalized = _normalize_sql(sql)
        self.calls.append((normalized, params))
        if self.error is not None:
            raise self.error
        return FakeCursor(self.rows.get(normalized, []))


class FakePoolConnectionContext:
    def __init__(self, pool: FakeConnectionPool):
        self.pool = pool

    def __enter__(self):
        self.pool.checkout_count += 1
        if self.pool._queued_connections:
            self.connection = self.pool._queued_connections.pop(0)
        else:
            self.connection = FakeConnection()
        self.pool.connections.append(self.connection)
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnectionPool:
    def __init__(self, conninfo: str, min_size: int, max_size: int, kwargs: dict, open: bool):
        self.conninfo = conninfo
        self.min_size = min_size
        self.max_size = max_size
        self.kwargs = kwargs
        self.open = open
        self.wait_calls = 0
        self.close_calls = 0
        self.checkout_count = 0
        self.connections: list[FakeConnection] = []
        self._queued_connections: list[FakeConnection] = []

    def wait(self):
        self.wait_calls += 1

    def connection(self):
        return FakePoolConnectionContext(self)

    def close(self):
        self.close_calls += 1

    def queue_connection(self, connection: FakeConnection) -> None:
        self._queued_connections.append(connection)


class FakeConnectionPoolFactory:
    def __init__(self):
        self.calls: list[tuple[str, int, int, dict, bool]] = []
        self.pools: list[FakeConnectionPool] = []

    def __call__(self, conninfo: str, min_size: int, max_size: int, kwargs: dict, open: bool):
        self.calls.append((conninfo, min_size, max_size, kwargs, open))
        pool = FakeConnectionPool(conninfo, min_size, max_size, kwargs, open)
        self.pools.append(pool)
        return pool


def _make_backend(monkeypatch, pool_factory: FakeConnectionPoolFactory | None = None):
    if pool_factory is None:
        pool_factory = FakeConnectionPoolFactory()
    dict_row = object()
    monkeypatch.setattr(
        "corpulse.backends.postgres._load_psycopg_pool",
        lambda: (pool_factory, dict_row, FakePsycopgError),
    )
    return PostgresBackend("postgresql://example"), pool_factory, dict_row


@pytest.mark.parametrize(
    ("input_dsn", "expected"),
    [
        ("postgresql+psycopg://example", "postgresql://example"),
        ("postgresql+psycopg2://u:p@h/db", "postgresql://u:p@h/db"),
        ("postgresql://u:p@h/db", "postgresql://u:p@h/db"),
        ("host=localhost port=5432 dbname=foo", "host=localhost port=5432 dbname=foo"),
    ],
)
def test_dsn_normalization_sync(monkeypatch, input_dsn, expected):
    pool_factory = FakeConnectionPoolFactory()
    dict_row = object()
    monkeypatch.setattr(
        "corpulse.backends.postgres._load_psycopg_pool",
        lambda: (pool_factory, dict_row, FakePsycopgError),
    )

    backend = PostgresBackend(input_dsn)

    assert pool_factory.calls == [
        (expected, 1, 10, {"row_factory": dict_row}, True)
    ]
    backend.close()


def test_postgres_backend_requires_psycopg(monkeypatch):
    def raising_loader():
        raise ImportError("Install corpulse[postgres].")

    monkeypatch.setattr("corpulse.backends.postgres._load_psycopg_pool", raising_loader)

    with pytest.raises(ImportError, match=r"corpulse\[postgres\]"):
        PostgresBackend("postgresql://example")


def test_postgres_backend_initializes_schema_through_pool_checkout(monkeypatch):
    backend, pool_factory, dict_row = _make_backend(monkeypatch)

    assert pool_factory.calls == [
        ("postgresql://example", 1, 10, {"row_factory": dict_row}, True)
    ]
    pool = pool_factory.pools[0]
    assert pool.wait_calls == 1
    assert pool.checkout_count == 1
    assert len(pool.connections) == 1
    assert any(
        "CREATE TABLE IF NOT EXISTS documents" in sql for sql, _ in pool.connections[0].calls
    )

    backend.close()
    assert pool.close_calls == 1


def test_postgres_backend_accepts_pool_size_kwargs(monkeypatch):
    custom_factory = FakeConnectionPoolFactory()
    dict_row = object()
    monkeypatch.setattr(
        "corpulse.backends.postgres._load_psycopg_pool",
        lambda: (custom_factory, dict_row, FakePsycopgError),
    )
    custom_backend = PostgresBackend(
        "postgresql://custom",
        min_size=3,
        max_size=7,
    )

    assert custom_factory.calls == [
        ("postgresql://custom", 3, 7, {"row_factory": dict_row}, True)
    ]
    custom_backend.close()


def test_build_schema_sql_default_output_is_backward_compatible():
    assert build_schema_sql() == EXPECTED_DEFAULT_SCHEMA_SQL


def test_build_schema_sql_supports_schema_qualified_output():
    sql = build_schema_sql(schema="tenant_alpha")

    assert "CREATE SCHEMA IF NOT EXISTS tenant_alpha;" in sql
    assert "CREATE TABLE IF NOT EXISTS tenant_alpha.documents" in sql
    assert "CREATE TABLE IF NOT EXISTS tenant_alpha.retrievals" in sql
    assert "CREATE TABLE IF NOT EXISTS tenant_alpha.engagements" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_retrievals_doc ON tenant_alpha.retrievals(doc_id);" in sql


def test_build_schema_sql_supports_prefix_only_output():
    sql = build_schema_sql(prefix="tenant_abc_")

    assert "CREATE TABLE IF NOT EXISTS tenant_abc_documents" in sql
    assert "CREATE TABLE IF NOT EXISTS tenant_abc_retrievals" in sql
    assert "CREATE TABLE IF NOT EXISTS tenant_abc_engagements" in sql
    assert "CREATE INDEX IF NOT EXISTS tenant_abc_idx_retrievals_doc ON tenant_abc_retrievals(doc_id);" in sql
    assert "CREATE INDEX IF NOT EXISTS tenant_abc_idx_engagements_doc ON tenant_abc_engagements(doc_id);" in sql


@pytest.mark.parametrize(
    ("kwargs", "field"),
    [
        ({"schema": "bad-name"}, "schema"),
        ({"schema": "tenant.one"}, "schema"),
        ({"prefix": "tenant-"}, "table_prefix"),
        ({"prefix": "1tenant_"}, "table_prefix"),
    ],
)
def test_build_schema_sql_rejects_invalid_identifiers(kwargs, field):
    with pytest.raises(ValueError, match=field):
        build_schema_sql(**kwargs)


def test_postgres_backend_translates_driver_errors(monkeypatch):
    backend, pool_factory, _ = _make_backend(monkeypatch)
    pool = pool_factory.pools[0]
    error_connection = FakeConnection()
    error_connection.error = FakePsycopgError("boom")
    pool.queue_connection(error_connection)

    with pytest.raises(StorageBackendError, match="boom") as exc_info:
        backend.all_documents()

    assert isinstance(exc_info.value.__cause__, FakePsycopgError)


def test_postgres_backend_returns_mapping_rows(monkeypatch):
    backend, pool_factory, _ = _make_backend(monkeypatch)
    pool = pool_factory.pools[0]

    documents_conn = FakeConnection()
    documents_conn.rows[_normalize_sql("SELECT * FROM documents")] = [
        {
            "doc_id": "doc-1",
            "filename": "doc-1.md",
            "embedding_vec": b"vec",
            "embedded_at": 12.5,
            "source_updated_at": 40.0,
        }
    ]
    retrievals_conn = FakeConnection()
    retrievals_conn.rows[
        _normalize_sql(
            """
            SELECT doc_id, COUNT(*) AS cnt,
                   AVG(rank) AS avg_rank, AVG(score) AS avg_score
            FROM retrievals
            WHERE retrieved_at >= %s
            GROUP BY doc_id
            """
        )
    ] = [{"doc_id": "doc-1", "cnt": 1, "avg_rank": 1.0, "avg_score": 0.9}]
    engagements_conn = FakeConnection()
    engagements_conn.rows[
        _normalize_sql(
            """
            SELECT doc_id, COUNT(*) AS cnt
            FROM engagements
            WHERE engaged_at >= %s
            GROUP BY doc_id
            """
        )
    ] = [{"doc_id": "doc-1", "cnt": 1}]
    embeddings_conn = FakeConnection()
    embeddings_conn.rows[
        _normalize_sql(
            """
            SELECT doc_id, filename, embedding_vec
            FROM documents
            WHERE embedding_vec IS NOT NULL
            """
        )
    ] = [{"doc_id": "doc-1", "filename": "doc-1.md", "embedding_vec": b"vec"}]
    pool.queue_connection(documents_conn)
    pool.queue_connection(retrievals_conn)
    pool.queue_connection(engagements_conn)
    pool.queue_connection(embeddings_conn)

    assert backend.all_documents() == [
        {
            "doc_id": "doc-1",
            "filename": "doc-1.md",
            "embedding_vec": b"vec",
            "embedded_at": 12.5,
            "source_updated_at": 40.0,
        }
    ]
    assert backend.retrieval_counts(0.0) == [
        {"doc_id": "doc-1", "cnt": 1, "avg_rank": 1.0, "avg_score": 0.9}
    ]
    assert backend.engagement_counts(0.0) == [{"doc_id": "doc-1", "cnt": 1}]
    assert backend.all_embeddings() == [
        {"doc_id": "doc-1", "filename": "doc-1.md", "embedding_vec": b"vec"}
    ]


def test_postgres_backend_checks_out_a_connection_for_each_operation(monkeypatch):
    backend, pool_factory, _ = _make_backend(monkeypatch)
    pool = pool_factory.pools[0]

    backend.upsert_document("doc-1", "doc-1.md", embedding=b"vec", embedded_at=1.0)
    backend.insert_retrieval("doc-1", "hash", 1, 0.9, 2.0)
    backend.insert_engagement("doc-1", "opened", 3.0)
    backend.update_source_timestamp("doc-1", 4.0)
    backend.delete_document("doc-1")
    backend.all_documents()

    assert pool.checkout_count == 7
    assert not hasattr(backend, "_conn")


def test_postgres_backend_delete_document(monkeypatch):
    backend, pool_factory, _ = _make_backend(monkeypatch)
    pool = pool_factory.pools[0]

    backend.delete_document("doc-1")

    delete_calls = pool.connections[-1].calls[-3:]
    assert delete_calls == [
        ("DELETE FROM retrievals WHERE doc_id = %s", ("doc-1",)),
        ("DELETE FROM engagements WHERE doc_id = %s", ("doc-1",)),
        ("DELETE FROM documents WHERE doc_id = %s", ("doc-1",)),
    ]


@pytest.mark.skipif(
    not os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")
    or importlib.util.find_spec("psycopg") is None,
    reason="requires CORPULSE_POSTGRES_TEST_CONNINFO and psycopg",
)
def test_live_postgres_backend_round_trip():
    from corpulse.backends import PostgresBackend as LivePostgresBackend

    with LivePostgresBackend(os.environ["CORPULSE_POSTGRES_TEST_CONNINFO"]) as backend:
        with backend._pool.connection() as conn:
            conn.execute("TRUNCATE engagements, retrievals, documents RESTART IDENTITY")

        backend.upsert_document("doc-1", "doc-1.md", embedding=b"vec", embedded_at=12.5)
        backend.insert_retrieval("doc-1", "hash", 1, 0.9, 25.0)
        backend.insert_engagement("doc-1", "opened", 30.0)
        backend.update_source_timestamp("doc-1", 40.0)

        assert backend.all_documents() == [
            {
                "doc_id": "doc-1",
                "filename": "doc-1.md",
                "embedding_vec": b"vec",
                "embedded_at": 12.5,
                "source_updated_at": 40.0,
            }
        ]
        assert backend.retrieval_counts(0.0) == [
            {"doc_id": "doc-1", "cnt": 1, "avg_rank": 1.0, "avg_score": 0.9}
        ]
        assert backend.engagement_counts(0.0) == [{"doc_id": "doc-1", "cnt": 1}]
        assert backend.all_embeddings() == [
            {"doc_id": "doc-1", "filename": "doc-1.md", "embedding_vec": b"vec"}
        ]
