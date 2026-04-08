import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tests.test_backend_contract as backend_contract_tests
from corpulse.core import Corpulse
from corpulse.db import DB


def test_backend_contract_module_stages_future_parity_cases():
    expected = {
        "test_sqlite_backend_parity_placeholder",
        "test_translated_runtime_error_placeholder",
        "test_shared_backend_fixture_placeholder",
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


@pytest.mark.skip(reason="Activate in 06-02/06-03 once concrete backends exist")
def test_corpulse_backend_injection_placeholder():
    assert False, "placeholder"


@pytest.mark.skip(reason="Activate in 06-02/06-03 once concrete backends exist")
def test_corpulse_lifecycle_delegation_placeholder():
    assert False, "placeholder"


@pytest.mark.skip(reason="Activate in 06-02/06-03 once concrete backends exist")
def test_corpulse_constructor_conflict_placeholder():
    assert False, "placeholder"
