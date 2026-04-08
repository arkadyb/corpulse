from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from corpulse.backends import SQLiteBackend


@pytest.fixture
def sqlite_backend(tmp_path):
    with SQLiteBackend(str(tmp_path / "test.db")) as backend:
        yield backend
