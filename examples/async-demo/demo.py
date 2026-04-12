"""Runnable async corpulse demo with no external database dependency."""

from __future__ import annotations

import asyncio
import os
import random

import numpy as np

from corpulse import AsyncCorpulse
from corpulse.backends import AsyncPostgresBackend, InMemoryBackend

VECTOR_DIM = 32

random.seed(42)
np.random.seed(42)


class AsyncInMemoryBackend:
    """Thin async adapter around the synchronous InMemoryBackend."""

    def __init__(self) -> None:
        self._backend = InMemoryBackend()

    async def upsert_document(
        self,
        doc_id: str,
        filename: str,
        embedding: bytes | None = None,
        embedded_at: float | None = None,
    ) -> None:
        self._backend.upsert_document(doc_id, filename, embedding, embedded_at)

    async def insert_retrieval(
        self,
        doc_id: str,
        query_hash: str,
        rank: int,
        score: float,
        retrieved_at: float,
    ) -> None:
        self._backend.insert_retrieval(doc_id, query_hash, rank, score, retrieved_at)

    async def insert_engagement(
        self,
        doc_id: str,
        event_type: str,
        engaged_at: float,
    ) -> None:
        self._backend.insert_engagement(doc_id, event_type, engaged_at)

    async def update_source_timestamp(self, doc_id: str, updated_at: float) -> None:
        self._backend.update_source_timestamp(doc_id, updated_at)

    async def all_documents(self):
        return self._backend.all_documents()

    async def retrieval_counts(self, since: float):
        return self._backend.retrieval_counts(since)

    async def engagement_counts(self, since: float):
        return self._backend.engagement_counts(since)

    async def all_embeddings(self):
        return self._backend.all_embeddings()

    async def close(self) -> None:
        self._backend.close()


DOCUMENTS = [
    {"id": "1", "filename": "getting-started.md", "topic": "getting-started"},
    {"id": "2", "filename": "api-reference-v2.md", "topic": "api"},
    {"id": "3", "filename": "api-reference-v1.md", "topic": "api"},
    {"id": "4", "filename": "troubleshooting.md", "topic": "troubleshooting"},
    {"id": "5", "filename": "setup-guide.md", "topic": "setup"},
    {"id": "6", "filename": "setup-guide-copy.md", "topic": "setup"},
    {"id": "7", "filename": "pricing-2023.md", "topic": "pricing"},
    {"id": "8", "filename": "internal-draft.md", "topic": "internal"},
]

QUERIES = [
    ("how do I get started?", [("1", "getting-started.md"), ("8", "internal-draft.md")]),
    ("API authentication docs", [("2", "api-reference-v2.md"), ("3", "api-reference-v1.md")]),
    ("environment setup steps", [("5", "setup-guide.md"), ("6", "setup-guide-copy.md")]),
    ("fix connection timeout error", [("4", "troubleshooting.md"), ("5", "setup-guide.md")]),
]


def random_vector(dim: int = VECTOR_DIM) -> np.ndarray:
    """Generate a normalized random embedding vector."""
    vector = np.random.randn(dim).astype(np.float32)
    return vector / np.linalg.norm(vector)


def similar_vector(base: np.ndarray, noise: float = 0.05) -> np.ndarray:
    """Generate a vector close to the provided base embedding."""
    vector = np.array(base, dtype=np.float32)
    vector += np.random.randn(len(vector)).astype(np.float32) * noise
    return vector / np.linalg.norm(vector)


async def build_backend():
    """Create the demo backend from env or a local in-memory adapter."""
    dsn = os.environ.get("CORPULSE_POSTGRES_TEST_CONNINFO")
    if dsn:
        return await AsyncPostgresBackend.create(dsn)
    return AsyncInMemoryBackend()


async def seed_corpus(corp: AsyncCorpulse) -> None:
    """Register documents and seed retrieval/engagement events."""
    topic_vectors: dict[str, np.ndarray] = {}
    for document in DOCUMENTS:
        topic = document["topic"]
        topic_vectors.setdefault(topic, random_vector())
        if document["filename"] == "setup-guide-copy.md":
            embedding = similar_vector(topic_vectors["setup"], noise=0.02)
        else:
            embedding = similar_vector(topic_vectors[topic], noise=0.03)

        await corp.register_document(document["id"], document["filename"], embedding=embedding)

    for query_text, result_docs in QUERIES:
        await corp.log_retrieval(
            [
                {"doc_id": doc_id, "filename": filename, "score": round(random.uniform(0.75, 0.97), 3)}
                for doc_id, filename in result_docs
            ],
            query=query_text,
        )

    for _ in range(12):
        query_text, result_docs = random.choice(QUERIES)
        await corp.log_retrieval(
            [
                {"doc_id": doc_id, "filename": filename, "score": round(random.uniform(0.75, 0.97), 3)}
                for doc_id, filename in result_docs
            ],
            query=query_text,
        )

    for _ in range(8):
        await corp.log_engagement("1", event="opened")
        await corp.log_engagement("2", event="opened")

    await corp.log_engagement("4", event="opened")
    await corp.log_source_update("7")


async def main() -> None:
    """Run the async corpulse demo end-to-end."""
    backend = await build_backend()
    async with AsyncCorpulse(backend=backend, ghost_threshold_days=30) as corp:
        await seed_corpus(corp)

        ghosts = await corp.get_ghosts()
        suspects = await corp.get_suspects()
        report = await corp.report(window_days=30)
        cleanup = await corp.cleanup_report()

        print("AsyncCorpulse demo")
        print("==================")
        print(f"Ghost docs: {len(ghosts)}")
        print(f"Low-engagement suspects: {len(suspects)}")
        print()
        print("Report summary:")
        print(report["summary"])
        print()
        print("Top report rows:")
        for row in report["rows"][:3]:
            print(row)
        print()
        print("Cleanup payload:")
        print(cleanup)


if __name__ == "__main__":
    asyncio.run(main())
