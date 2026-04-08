import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tests.test_backend_contract as backend_contract_tests
from corpulse.backends import SQLiteBackend
from corpulse.core import Corpulse
from corpulse.db import DB


def test_backend_contract_module_exposes_active_parity_cases():
    expected = {
        "test_sqlite_backend_parity",
        "test_translated_runtime_error",
        "test_shared_backend_fixture_uses_sqlite_backend",
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


def test_corpulse_constructor_conflict_raises_value_error(tmp_path):
    backend = SQLiteBackend(str(tmp_path / "conflict.db"))

    with pytest.raises(ValueError, match="db_path|backend"):
        Corpulse(db_path=str(tmp_path / "other.db"), backend=backend)
