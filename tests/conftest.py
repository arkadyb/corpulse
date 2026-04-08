from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from corpulse.backends import InMemoryBackend, SQLiteBackend


@pytest.fixture
def sqlite_backend(tmp_path):
    with SQLiteBackend(str(tmp_path / "test.db")) as backend:
        yield backend


@pytest.fixture(params=["sqlite", "memory"])
def backend(request, tmp_path):
    if request.param == "sqlite":
        with SQLiteBackend(str(tmp_path / "test.db")) as storage_backend:
            yield storage_backend
        return

    with InMemoryBackend() as storage_backend:
        yield storage_backend
