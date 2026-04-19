"""Storage backend implementations and shared contracts."""

from .base import (
    DocumentRow,
    EmbeddingRow,
    EngagementRow,
    QueryAttemptRow,
    RetrievalRow,
    StorageBackend,
    StorageBackendError,
)
from .memory import InMemoryBackend
from .sqlite import SQLiteBackend

__all__ = [
    "AsyncPostgresBackend",
    "DocumentRow",
    "EmbeddingRow",
    "EngagementRow",
    "QueryAttemptRow",
    "RetrievalRow",
    "StorageBackend",
    "StorageBackendError",
    "InMemoryBackend",
    "PostgresBackend",
    "SQLiteBackend",
]


def __getattr__(name: str):
    if name == "AsyncPostgresBackend":
        from .postgres_async import AsyncPostgresBackend

        globals()["AsyncPostgresBackend"] = AsyncPostgresBackend
        return AsyncPostgresBackend
    if name == "PostgresBackend":
        from .postgres import PostgresBackend

        globals()["PostgresBackend"] = PostgresBackend
        return PostgresBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
