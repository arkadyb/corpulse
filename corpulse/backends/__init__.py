"""Storage backend implementations and shared contracts."""

from .base import (
    DocumentRow,
    EmbeddingRow,
    EngagementRow,
    RetrievalRow,
    StorageBackend,
    StorageBackendError,
)
from .memory import InMemoryBackend
from .sqlite import SQLiteBackend

__all__ = [
    "DocumentRow",
    "EmbeddingRow",
    "EngagementRow",
    "RetrievalRow",
    "StorageBackend",
    "StorageBackendError",
    "InMemoryBackend",
    "PostgresBackend",
    "SQLiteBackend",
]


def __getattr__(name: str):
    if name == "PostgresBackend":
        from .postgres import PostgresBackend

        globals()["PostgresBackend"] = PostgresBackend
        return PostgresBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
