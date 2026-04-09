import sys
import importlib.util
import os
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tests.test_backend_contract as backend_contract_tests
from corpulse.backends import InMemoryBackend, SQLiteBackend
from corpulse.core import Corpulse
from corpulse.db import DB


def test_backend_contract_module_exposes_active_parity_cases():
    expected = {
        "test_backend_parity",
        "test_translated_runtime_error",
        "test_shared_backend_fixture_runs_for_sqlite_and_memory",
    }

    missing = [
        name for name in expected if not hasattr(backend_contract_tests, name)
    ]

    assert not missing, missing


def test_corpulse_default_constructor_uses_default_sqlite_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    corpulse = Corpulse()

    assert isinstance(corpulse.db, DB)
    assert corpulse.db.path == Path("./corpulse.db")
    assert corpulse.db.path.resolve() == tmp_path / "corpulse.db"
    assert corpulse.db.path.exists()


def test_corpulse_backend_injection_uses_explicit_backend(tmp_path):
    backend = SQLiteBackend(str(tmp_path / "explicit.db"))
    corpulse = Corpulse(backend=backend)

    assert corpulse.db is backend
    assert corpulse.db.path == tmp_path / "explicit.db"


def test_corpulse_lifecycle_delegation(tmp_path):
    backend = SQLiteBackend(str(tmp_path / "ctx.db"))

    with Corpulse(backend=backend) as corpulse:
        assert corpulse.db is backend

    corpulse.close()


def test_corpulse_inmemory_backend_records_retrievals_without_file_io():
    corpulse = Corpulse(backend=InMemoryBackend())

    corpulse.log_retrieval(
        [{"doc_id": "ghost", "filename": "ghost.md", "score": 0.2}],
        query="status",
    )
    corpulse.register_document("suspect", "suspect.md")
    for _ in range(5):
        corpulse.log_retrieval(
            [{"doc_id": "suspect", "filename": "suspect.md", "score": 0.9}],
            query="hot path",
        )

    assert corpulse.get_ghosts() == []
    suspects = corpulse.get_suspects()
    assert [item["doc_id"] for item in suspects] == ["suspect"]


def test_corpulse_inmemory_backend_context_manager_delegates_close():
    backend = InMemoryBackend()

    with Corpulse(backend=InMemoryBackend()) as corpulse:
        assert isinstance(corpulse.db, InMemoryBackend)

    with Corpulse(backend=backend) as corpulse:
        assert corpulse.db is backend

    assert backend._closed is True


def test_corpulse_constructor_conflict_raises_value_error(tmp_path):
    backend = SQLiteBackend(str(tmp_path / "conflict.db"))

    with pytest.raises(ValueError, match="db_path|backend"):
        Corpulse(db_path=str(tmp_path / "other.db"), backend=backend)


@pytest.mark.skipif(
    not os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")
    or importlib.util.find_spec("psycopg") is None,
    reason="requires CORPULSE_POSTGRES_TEST_CONNINFO and psycopg",
)
def test_corpulse_postgres_backend_records_retrievals_when_conninfo_available():
    from corpulse.backends import PostgresBackend

    with PostgresBackend(os.environ["CORPULSE_POSTGRES_TEST_CONNINFO"]) as backend:
        with backend._pool.connection() as conn:
            conn.execute("TRUNCATE engagements, retrievals, documents RESTART IDENTITY")

        corpulse = Corpulse(backend=backend)
        corpulse.log_retrieval(
            [{"doc_id": "ghost", "filename": "ghost.md", "score": 0.2}],
            query="status",
        )

        assert corpulse.get_ghosts() == []
