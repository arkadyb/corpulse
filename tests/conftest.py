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


def _async_backend_params() -> list[str]:
    params = []
    if (
        os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")
        and importlib.util.find_spec("asyncpg") is not None
    ):
        params.append("async_postgres")
    return params or ["skip"]


@pytest.fixture(params=_backend_params())
def backend(request, tmp_path):
    if request.param == "sqlite":
        with SQLiteBackend(str(tmp_path / "test.db")) as storage_backend:
            yield storage_backend
        return

    if request.param == "postgres":
        from corpulse.backends import PostgresBackend

        with PostgresBackend(os.environ["CORPULSE_POSTGRES_TEST_CONNINFO"]) as storage_backend:
            with storage_backend._pool.connection() as conn:
                conn.execute("TRUNCATE engagements, generation_traces, rag_request_traces, retrievals, query_attempts, documents RESTART IDENTITY")
            try:
                yield storage_backend
            finally:
                with storage_backend._pool.connection() as conn:
                    conn.execute("TRUNCATE engagements, generation_traces, rag_request_traces, retrievals, query_attempts, documents RESTART IDENTITY")
        return

    with InMemoryBackend() as storage_backend:
        yield storage_backend


@pytest.fixture(params=_async_backend_params())
async def async_backend(request):
    if request.param == "skip":
        pytest.skip("requires CORPULSE_POSTGRES_TEST_CONNINFO and asyncpg")

    from corpulse.backends import AsyncPostgresBackend

    backend = await AsyncPostgresBackend.create(
        os.environ["CORPULSE_POSTGRES_TEST_CONNINFO"]
    )
    async with backend._pool.acquire() as conn:
        await conn.execute("TRUNCATE engagements, generation_traces, rag_request_traces, retrievals, query_attempts, documents RESTART IDENTITY")
    try:
        yield backend
    finally:
        async with backend._pool.acquire() as conn:
            await conn.execute(
                "TRUNCATE engagements, generation_traces, rag_request_traces, retrievals, query_attempts, documents RESTART IDENTITY"
            )
        await backend.close()
