from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from corpulse.backends import InMemoryBackend, SQLiteBackend


@pytest.fixture
def sqlite_backend(tmp_path):
    with SQLiteBackend(str(tmp_path / "test.db")) as backend:
        yield backend


def _backend_params() -> list[str]:
    params = ["sqlite", "memory"]
    if (
        os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")
        and importlib.util.find_spec("psycopg") is not None
    ):
        params.append("postgres")
    return params


@pytest.fixture(params=_backend_params())
def backend(request, tmp_path):
    if request.param == "sqlite":
        with SQLiteBackend(str(tmp_path / "test.db")) as storage_backend:
            yield storage_backend
        return

    if request.param == "postgres":
        from corpulse.backends import PostgresBackend

        with PostgresBackend(os.environ["CORPULSE_POSTGRES_TEST_CONNINFO"]) as storage_backend:
            storage_backend._conn.execute(
                "TRUNCATE engagements, retrievals, documents RESTART IDENTITY"
            )
            storage_backend._conn.commit()
            try:
                yield storage_backend
            finally:
                storage_backend._conn.execute(
                    "TRUNCATE engagements, retrievals, documents RESTART IDENTITY"
                )
                storage_backend._conn.commit()
        return

    with InMemoryBackend() as storage_backend:
        yield storage_backend
