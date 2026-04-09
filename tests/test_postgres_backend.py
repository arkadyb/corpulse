from __future__ import annotations

import importlib.util
import os

import pytest

from corpulse.backends.base import StorageBackendError
from corpulse.backends.postgres import PostgresBackend


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.split())


class FakePsycopgError(Exception):
    pass


class FakeCursor:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self):
        self.calls: list[tuple[str, tuple | None]] = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0
        self.rows: dict[str, list[dict]] = {}
        self.error: Exception | None = None

    def execute(self, sql: str, params=None):
        normalized = _normalize_sql(sql)
        self.calls.append((normalized, params))
        if self.error is not None:
            raise self.error
        return FakeCursor(self.rows.get(normalized, []))

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed += 1


class FakePsycopgModule:
    Error = FakePsycopgError

    def __init__(self, connection: FakeConnection):
        self.connection = connection
        self.connect_calls = []

    def connect(self, conninfo: str, row_factory):
        self.connect_calls.append((conninfo, row_factory))
        return self.connection


def test_postgres_backend_requires_psycopg(monkeypatch):
    def raising_loader():
        raise ImportError("Install corpulse[postgres].")

    monkeypatch.setattr("corpulse.backends.postgres._load_psycopg", raising_loader)

    with pytest.raises(ImportError, match=r"corpulse\[postgres\]"):
        PostgresBackend("postgresql://example")


def test_postgres_backend_initializes_schema_and_uses_lazy_driver(monkeypatch):
    connection = FakeConnection()
    psycopg = FakePsycopgModule(connection)
    dict_row = object()
    monkeypatch.setattr(
        "corpulse.backends.postgres._load_psycopg",
        lambda: (psycopg, dict_row, FakePsycopgError),
    )

    backend = PostgresBackend("postgresql://example")

    assert psycopg.connect_calls == [("postgresql://example", dict_row)]
    assert any("CREATE TABLE IF NOT EXISTS documents" in sql for sql, _ in connection.calls)
    assert connection.commits == 1
    backend.close()


def test_postgres_backend_translates_driver_errors(monkeypatch):
    connection = FakeConnection()
    psycopg = FakePsycopgModule(connection)
    monkeypatch.setattr(
        "corpulse.backends.postgres._load_psycopg",
        lambda: (psycopg, object(), FakePsycopgError),
    )
    backend = PostgresBackend("postgresql://example")
    connection.error = FakePsycopgError("boom")

    with pytest.raises(StorageBackendError, match="boom") as exc_info:
        backend.all_documents()

    assert isinstance(exc_info.value.__cause__, FakePsycopgError)
    assert connection.rollbacks == 1


def test_postgres_backend_returns_mapping_rows(monkeypatch):
    connection = FakeConnection()
    psycopg = FakePsycopgModule(connection)
    monkeypatch.setattr(
        "corpulse.backends.postgres._load_psycopg",
        lambda: (psycopg, object(), FakePsycopgError),
    )

    connection.rows[_normalize_sql("SELECT * FROM documents")] = [
        {
            "doc_id": "doc-1",
            "filename": "doc-1.md",
            "embedding_vec": b"vec",
            "embedded_at": 12.5,
            "source_updated_at": 40.0,
        }
    ]
    connection.rows[
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
    connection.rows[
        _normalize_sql(
            """
            SELECT doc_id, COUNT(*) AS cnt
            FROM engagements
            WHERE engaged_at >= %s
            GROUP BY doc_id
            """
        )
    ] = [{"doc_id": "doc-1", "cnt": 1}]
    connection.rows[
        _normalize_sql(
            """
            SELECT doc_id, filename, embedding_vec
            FROM documents
            WHERE embedding_vec IS NOT NULL
            """
        )
    ] = [{"doc_id": "doc-1", "filename": "doc-1.md", "embedding_vec": b"vec"}]

    backend = PostgresBackend("postgresql://example")

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


@pytest.mark.skipif(
    not os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")
    or importlib.util.find_spec("psycopg") is None,
    reason="requires CORPULSE_POSTGRES_TEST_CONNINFO and psycopg",
)
def test_live_postgres_backend_round_trip():
    from corpulse.backends import PostgresBackend as LivePostgresBackend

    with LivePostgresBackend(os.environ["CORPULSE_POSTGRES_TEST_CONNINFO"]) as backend:
        backend._conn.execute("TRUNCATE engagements, retrievals, documents RESTART IDENTITY")
        backend._conn.commit()

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
