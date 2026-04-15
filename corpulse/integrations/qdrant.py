"""Qdrant vector database integration wrappers for corpulse.

Provides QdrantCorpulseClient (sync) and AsyncQdrantCorpulseClient (async).
Both intercept query_points() and search() to automatically call
Corpulse.log_retrieval() with normalized results, then return the original
Qdrant response object unmodified.

Lazy import: qdrant_client is NOT imported at module level so that
`import corpulse` succeeds without qdrant-client installed.
"""
from __future__ import annotations

import asyncio
import inspect
import re
import uuid
from collections.abc import Sequence

__all__ = [
    "QdrantCorpulseClient",
    "AsyncQdrantCorpulseClient",
    "collection_name_for_user",
    "chunk_id",
    "delete_document_points",
    "ensure_collection",
]

CORPULSE_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "corpulse.ai")


def collection_name_for_user(user_id: str, base: str = "corpulse") -> str:
    """Sanitize user_id and return a collection name compliant with Qdrant.

    Lowercase user_id, replace non-[a-z0-9_] with _, strip leading/trailing _.
    Return {base}_{sanitized}.
    """
    sanitized = re.sub(r"[^a-z0-9_]+", "_", user_id.lower()).strip("_")
    return f"{base}_{sanitized}"


def chunk_id(doc_id: str, chunk_index: int | str) -> str:
    """Return a deterministic UUIDv5 string for a document chunk.

    Uses a fixed corpulse.ai namespace to ensure stability across runs.
    """
    return str(uuid.uuid5(CORPULSE_NAMESPACE, f"{doc_id}:{chunk_index}"))


def _normalize_points(points, call_kwargs, payload_id_field, payload_filename_key):
    """Convert list[ScoredPoint] into list[dict] for Corpulse.log_retrieval().

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
        if isinstance(embedding, dict):
            requested_vector_name = None
            if isinstance(with_vectors, Sequence) and not isinstance(
                with_vectors, (str, bytes)
            ):
                requested_vector_name = next(iter(with_vectors), None)

            if requested_vector_name is not None:
                embedding = embedding.get(requested_vector_name)
            elif with_vectors is True:
                # Preserve deterministic unnamed behavior when the caller asks
                # for vectors generally rather than by a specific name.
                embedding = next(iter(embedding.values()), None)
            else:
                embedding = None

        records.append({
            "doc_id": doc_id,
            "filename": filename,
            "score": p.score,
            "embedding": embedding,
        })
    return records


class QdrantCorpulseClient:
    """Sync Qdrant wrapper that auto-logs retrievals to Corpulse.

    Wraps a QdrantClient via composition. Intercepts query_points() and
    search() to call corpulse.log_retrieval() after a successful upstream
    response. All other methods delegate transparently to the underlying
    client via __getattr__.

    Args:
        client: A configured QdrantClient instance.
        corpulse: A Corpulse instance to log retrievals to.
        payload_id_field: Payload key to use as doc_id. When None (default),
            the point's integer/UUID ID is used directly.
        payload_filename_key: Payload key to use as filename. Default "filename".
    """

    def __init__(
        self,
        client,
        corpulse,
        *,
        payload_id_field=None,
        payload_filename_key="filename",
    ):
        # Assign _client FIRST to prevent __getattr__ recursion (Pitfall 5)
        self._client = client
        self._corpulse = corpulse
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
        """Log successful query_points() results, then return the upstream response."""
        result = self._client.query_points(collection_name=collection_name, **kwargs)
        # Access .points — result is QueryResponse, NOT list[ScoredPoint] (Pitfall 2)
        if result.points:
            records = _normalize_points(
                result.points,
                kwargs,
                self._payload_id_field,
                self._payload_filename_key,
            )
            self._corpulse.log_retrieval(records, query="")
        return result

    def search(self, collection_name, **kwargs):
        """Log successful search() results and return the upstream object unchanged.

        The wrapper delegates directly to ``self._client.search(...)``.
        If the configured client does not expose ``search()``, the resulting
        ``AttributeError`` propagates naturally. No compatibility shim or
        result emulation is added here.
        """
        # search() returns the client's native list response shape when available.
        result = self._client.search(collection_name=collection_name, **kwargs)
        if result:
            records = _normalize_points(
                result,
                kwargs,
                self._payload_id_field,
                self._payload_filename_key,
            )
            self._corpulse.log_retrieval(records, query="")
        return result

    def __getattr__(self, name):
        return getattr(self._client, name)


class AsyncQdrantCorpulseClient:
    """Async Qdrant wrapper that auto-logs retrievals to Corpulse.

    Wraps an AsyncQdrantClient via composition. Intercepts async query_points()
    and search() to call corpulse.log_retrieval() via asyncio.to_thread()
    after a successful upstream response. All other methods delegate
    transparently via __getattr__.

    Args:
        client: A configured AsyncQdrantClient instance.
        corpulse: A Corpulse instance to log retrievals to.
        payload_id_field: Payload key to use as doc_id. When None (default),
            the point's integer/UUID ID is used directly.
        payload_filename_key: Payload key to use as filename. Default "filename".
    """

    def __init__(
        self,
        client,
        corpulse,
        *,
        payload_id_field=None,
        payload_filename_key="filename",
    ):
        # Assign _client FIRST to prevent __getattr__ recursion (Pitfall 5)
        self._client = client
        self._corpulse = corpulse
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
        """Log successful async query_points() results, then return the upstream response."""
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
            await self._log_retrieval(records)
        return result

    async def search(self, collection_name, **kwargs):
        """Log successful async search() results and return the upstream object unchanged.

        The wrapper delegates directly to ``self._client.search(...)``.
        If the configured client does not expose ``search()``, the resulting
        ``AttributeError`` propagates naturally. No compatibility shim or
        result emulation is added here.
        """
        # search() returns the client's native list response shape when available.
        result = await self._client.search(collection_name=collection_name, **kwargs)
        if result:
            records = _normalize_points(
                result,
                kwargs,
                self._payload_id_field,
                self._payload_filename_key,
            )
            await self._log_retrieval(records)
        return result

    async def _log_retrieval(self, records) -> None:
        log_retrieval = self._corpulse.log_retrieval
        if inspect.iscoroutinefunction(log_retrieval):
            await log_retrieval(records, query="")
            return
        await asyncio.to_thread(log_retrieval, records, "")

    def __getattr__(self, name):
        return getattr(self._client, name)


def delete_document_points(
    client,
    collection_name: str,
    doc_id: str | int,
    payload_id_field: str | None = "doc_id",
):
    """Delete all points associated with a document.

    If payload_id_field is None, deletes the point with the given doc_id.
    Otherwise, filters points where payload_id_field matches doc_id.

    Supports both sync and async clients.
    """
    from qdrant_client import models

    if payload_id_field is None:
        points_selector = models.PointIdsList(points=[doc_id])
    else:
        points_selector = models.Filter(
            must=[
                models.FieldCondition(
                    key=payload_id_field,
                    match=models.MatchValue(value=doc_id),
                )
            ]
        )

    return client.delete(
        collection_name=collection_name,
        points_selector=points_selector,
    )


def ensure_collection(
    client,
    collection_name: str,
    vectors_config,
    payload_indexes: list[str] | None = None,
):
    """Ensure a collection exists and has required payload indexes.

    Calls client.collection_exists(), client.create_collection(), and
    client.create_payload_index() as needed.

    Supports both sync and async clients. Returns a coroutine if the client
    is async, otherwise performs operations synchronously.
    """
    from qdrant_client import models

    def _sync_flow():
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=vectors_config,
            )
        if payload_indexes:
            for field in payload_indexes:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )

    async def _async_flow():
        if not await client.collection_exists(collection_name):
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=vectors_config,
            )
        if payload_indexes:
            for field in payload_indexes:
                await client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )

    if inspect.iscoroutinefunction(client.collection_exists):
        return _async_flow()
    return _sync_flow()
