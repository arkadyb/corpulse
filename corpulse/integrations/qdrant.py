"""Qdrant vector database integration wrappers for corpulse.

Provides QdrantMementoClient (sync) and AsyncQdrantMementoClient (async).
Both intercept query_points() to automatically call Memento.log_retrieval()
with normalized results, then return the original Qdrant response unmodified.

Lazy import: qdrant_client is NOT imported at module level so that
`import corpulse` succeeds without qdrant-client installed.
"""
from __future__ import annotations

import asyncio

__all__ = ["QdrantMementoClient", "AsyncQdrantMementoClient"]


def _normalize_points(points, call_kwargs, payload_id_field, payload_filename_key):
    """Convert list[ScoredPoint] into list[dict] for Memento.log_retrieval().

    Args:
        points: list of ScoredPoint objects from a Qdrant QueryResponse.
        call_kwargs: the **kwargs dict passed to query_points() / search().
        payload_id_field: payload key to use as doc_id, or None to use point ID.
        payload_filename_key: payload key to use as filename.

    Returns:
        list of dicts with keys: doc_id, filename, score, embedding.
    """
    if not points:
        return []

    with_vectors = call_kwargs.get("with_vectors", False)
    records = []
    for p in points:
        payload = p.payload or {}

        if payload_id_field is None:
            doc_id = str(p.id)
        else:
            doc_id = payload.get(payload_id_field, str(p.id))

        filename = payload.get(payload_filename_key, doc_id)

        embedding = p.vector if with_vectors else None
        # Named vectors: p.vector is dict[str, list[float]] — extract first value
        if isinstance(embedding, dict):
            embedding = next(iter(embedding.values()), None)

        records.append({
            "doc_id": doc_id,
            "filename": filename,
            "score": p.score,
            "embedding": embedding,
        })
    return records


class QdrantMementoClient:
    """Sync Qdrant wrapper that auto-logs retrievals to Memento.

    Wraps a QdrantClient via composition. Intercepts query_points() and
    search() to call memento.log_retrieval() automatically. All other
    methods delegate transparently to the underlying client via __getattr__.

    Args:
        client: A configured QdrantClient instance.
        memento: A Memento instance to log retrievals to.
        payload_id_field: Payload key to use as doc_id. When None (default),
            the point's integer/UUID ID is used directly.
        payload_filename_key: Payload key to use as filename. Default "filename".
    """

    def __init__(
        self,
        client,
        memento,
        *,
        payload_id_field=None,
        payload_filename_key="filename",
    ):
        # Assign _client FIRST to prevent __getattr__ recursion (Pitfall 5)
        self._client = client
        self._memento = memento
        self._payload_id_field = payload_id_field
        self._payload_filename_key = payload_filename_key
        # Lazy import guard: raise early if qdrant-client is not installed
        try:
            from qdrant_client import QdrantClient  # noqa: F401
        except ImportError:
            raise ImportError(
                "Install qdrant-client: pip install corpulse[qdrant]"
            )

    def query_points(self, collection_name, **kwargs):
        """Intercept query_points(), log retrieval, return original response."""
        result = self._client.query_points(collection_name=collection_name, **kwargs)
        # Access .points — result is QueryResponse, NOT list[ScoredPoint] (Pitfall 2)
        if result.points:
            records = _normalize_points(
                result.points,
                kwargs,
                self._payload_id_field,
                self._payload_filename_key,
            )
            self._memento.log_retrieval(records, query="")
        return result

    def search(self, collection_name, **kwargs):
        """Intercept search() for qdrant-client <1.16.0 users.

        Note: search() was removed in qdrant-client 1.16.0. On current
        versions this raises AttributeError from the underlying client,
        which propagates naturally. No emulation of removed behavior.
        search() returned list[ScoredPoint] directly (not QueryResponse).
        """
        result = self._client.search(collection_name=collection_name, **kwargs)
        if result:
            records = _normalize_points(
                result,
                kwargs,
                self._payload_id_field,
                self._payload_filename_key,
            )
            self._memento.log_retrieval(records, query="")
        return result

    def __getattr__(self, name):
        return getattr(self._client, name)


class AsyncQdrantMementoClient:
    """Async Qdrant wrapper that auto-logs retrievals to Memento.

    Wraps an AsyncQdrantClient via composition. Intercepts async query_points()
    and search() to call memento.log_retrieval() via asyncio.to_thread().
    All other methods delegate transparently via __getattr__.

    Args:
        client: A configured AsyncQdrantClient instance.
        memento: A Memento instance to log retrievals to.
        payload_id_field: Payload key to use as doc_id. When None (default),
            the point's integer/UUID ID is used directly.
        payload_filename_key: Payload key to use as filename. Default "filename".
    """

    def __init__(
        self,
        client,
        memento,
        *,
        payload_id_field=None,
        payload_filename_key="filename",
    ):
        # Assign _client FIRST to prevent __getattr__ recursion (Pitfall 5)
        self._client = client
        self._memento = memento
        self._payload_id_field = payload_id_field
        self._payload_filename_key = payload_filename_key
        # Lazy import guard: raise early if qdrant-client is not installed
        try:
            from qdrant_client import AsyncQdrantClient  # noqa: F401
        except ImportError:
            raise ImportError(
                "Install qdrant-client: pip install corpulse[qdrant]"
            )

    async def query_points(self, collection_name, **kwargs):
        """Intercept async query_points(), log retrieval, return original response."""
        result = await self._client.query_points(
            collection_name=collection_name, **kwargs
        )
        # Access .points — result is QueryResponse, NOT list[ScoredPoint] (Pitfall 2)
        if result.points:
            records = _normalize_points(
                result.points,
                kwargs,
                self._payload_id_field,
                self._payload_filename_key,
            )
            await asyncio.to_thread(self._memento.log_retrieval, records, "")
        return result

    async def search(self, collection_name, **kwargs):
        """Intercept async search() for qdrant-client <1.16.0 users.

        Note: search() was removed in qdrant-client 1.16.0. On current
        versions this raises AttributeError from the underlying client.
        search() returned list[ScoredPoint] directly (not QueryResponse).
        """
        result = await self._client.search(collection_name=collection_name, **kwargs)
        if result:
            records = _normalize_points(
                result,
                kwargs,
                self._payload_id_field,
                self._payload_filename_key,
            )
            await asyncio.to_thread(self._memento.log_retrieval, records, "")
        return result

    def __getattr__(self, name):
        return getattr(self._client, name)
