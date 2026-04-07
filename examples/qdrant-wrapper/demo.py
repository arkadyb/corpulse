"""
qdrant_demo.py — Sample app showcasing corpulse with a real Qdrant instance.

This script:
  1. Connects to a local Qdrant server
  2. Creates a collection and inserts sample documents
  3. Wraps the Qdrant client with QdrantCorpulseClient
  4. Runs queries — retrievals are tracked automatically
  5. Simulates user engagement
  6. Prints a corpus health report

Prerequisites:
  pip install "corpulse[qdrant] @ git+https://github.com/arkadyb/corpulse.git"

  # Start Qdrant locally (pick one):
  #   Option A — Docker (recommended):
  #     docker run -p 6333:6333 qdrant/qdrant
  #
  #   Option B — In-memory (no server needed, used by default below):
  #     No setup required. This demo uses ":memory:" mode.
"""

from pathlib import Path
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from corpulse import Corpulse, QdrantCorpulseClient


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Switch to "localhost" if you have Qdrant running via Docker.
# ":memory:" runs an embedded Qdrant — no server needed.
QDRANT_LOCATION = ":memory:"
COLLECTION_NAME = "knowledge_base"
VECTOR_DIM = 64


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

np.random.seed(42)

def random_vector(dim=VECTOR_DIM):
    """Generate a normalised random vector (simulates an embedding)."""
    v = np.random.randn(dim).astype(np.float32)
    return (v / np.linalg.norm(v)).tolist()

def similar_vector(base, noise=0.05):
    """Generate a vector close to `base` (simulates a near-duplicate)."""
    arr = np.array(base, dtype=np.float32)
    arr += np.random.randn(len(arr)).astype(np.float32) * noise
    return (arr / np.linalg.norm(arr)).tolist()


# ---------------------------------------------------------------------------
# 1. Set up Qdrant collection with sample documents
# ---------------------------------------------------------------------------

print("=" * 60)
print("CORPULSE  ×  QDRANT  —  Sample Application")
print("=" * 60)

client = QdrantClient(location=QDRANT_LOCATION)

if client.collection_exists(COLLECTION_NAME):
    client.delete_collection(COLLECTION_NAME)
client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
)

# Sample knowledge base — imagine these are chunked docs in a real RAG system
DOCUMENTS = [
    {"id": 1,  "filename": "getting-started.md",     "text": "How to install and configure the product"},
    {"id": 2,  "filename": "api-reference-v2.md",    "text": "REST API endpoints and authentication"},
    {"id": 3,  "filename": "api-reference-v1.md",    "text": "Legacy API docs (superseded by v2)"},
    {"id": 4,  "filename": "troubleshooting.md",     "text": "Common errors and how to fix them"},
    {"id": 5,  "filename": "setup-guide.md",         "text": "Step-by-step environment setup"},
    {"id": 6,  "filename": "setup-guide-copy.md",    "text": "Step-by-step environment setup (duplicate)"},
    {"id": 7,  "filename": "pricing-2023.md",        "text": "Outdated pricing table from last year"},
    {"id": 8,  "filename": "internal-draft.md",      "text": "Unfinished internal notes — never retrieved"},
    {"id": 9,  "filename": "security-overview.md",   "text": "Security best practices and compliance"},
    {"id": 10, "filename": "changelog.md",           "text": "Release history — rarely useful in search"},
]

# Generate embeddings (in production you'd use an embedding model)
base_vectors = {}
points = []
for doc in DOCUMENTS:
    # Make setup-guide and setup-guide-copy nearly identical
    if doc["filename"] == "setup-guide-copy.md":
        vec = similar_vector(base_vectors["setup-guide.md"], noise=0.02)
    else:
        vec = random_vector()
        base_vectors[doc["filename"]] = vec

    points.append(PointStruct(
        id=doc["id"],
        vector=vec,
        payload={"filename": doc["filename"], "text": doc["text"]},
    ))

client.upsert(collection_name=COLLECTION_NAME, points=points)
print(f"\n✓ Inserted {len(points)} documents into '{COLLECTION_NAME}' collection\n")


# ---------------------------------------------------------------------------
# 2. Wrap the client with corpulse
# ---------------------------------------------------------------------------

DB_PATH = "./qdrant_demo.db"
Path(DB_PATH).unlink(missing_ok=True)
corp = Corpulse(db_path=DB_PATH)
wrapped = QdrantCorpulseClient(client, corp)

print("✓ Wrapped QdrantClient with QdrantCorpulseClient")
print("  Every query_points() call now auto-logs retrievals.\n")


# ---------------------------------------------------------------------------
# 3. Run queries — retrievals are tracked automatically
# ---------------------------------------------------------------------------

print("-" * 60)
print("Running sample queries...")
print("-" * 60)

QUERIES = [
    ("how do I get started?",       base_vectors["getting-started.md"]),
    ("API authentication docs",     base_vectors["api-reference-v2.md"]),
    ("environment setup steps",     base_vectors["setup-guide.md"]),
    ("fix connection timeout error", base_vectors["troubleshooting.md"]),
    ("security compliance",         base_vectors["security-overview.md"]),
]

for query_text, query_vector in QUERIES:
    result = wrapped.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=3,
    )
    top_files = [p.payload["filename"] for p in result.points]
    print(f"  Q: \"{query_text}\"")
    print(f"     → {', '.join(top_files)}")

# Run a few more queries to build up retrieval history
for _ in range(20):
    query_text, query_vector = QUERIES[np.random.randint(len(QUERIES))]
    wrapped.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=3,
    )

print(f"\n✓ Ran {5 + 20} queries — all automatically tracked\n")


# ---------------------------------------------------------------------------
# 4. Simulate user engagement (some docs get opened, others don't)
# ---------------------------------------------------------------------------

print("Simulating user engagement...")

# Popular docs get high engagement
for _ in range(15):
    corp.log_engagement("1", event="opened")   # getting-started.md
    corp.log_engagement("2", event="opened")   # api-reference-v2.md

# Troubleshooting retrieved often but rarely opened (suspect)
for _ in range(2):
    corp.log_engagement("4", event="opened")

# Mark pricing doc source as updated (stale embedding)
corp.log_source_update("7")

print("✓ Engagement and source updates logged\n")


# ---------------------------------------------------------------------------
# 5. Register embeddings so duplicate detection works
# ---------------------------------------------------------------------------

for doc, point in zip(DOCUMENTS, points):
    vec_array = np.array(point.vector, dtype=np.float32)
    corp.register_document(
        doc_id=str(doc["id"]),
        filename=doc["filename"],
        embedding=vec_array,
    )


# ---------------------------------------------------------------------------
# 6. Print the corpus health report
# ---------------------------------------------------------------------------

print("=" * 60)
print("CORPUS HEALTH REPORT")
print("=" * 60)
print()

corp.report(window_days=30)

print()
print("-" * 60)
print("CLEANUP RECOMMENDATIONS")
print("-" * 60)
print()

corp.cleanup_report()

print()
print("-" * 60)
print("DETAILED FINDINGS")
print("-" * 60)

ghosts = corp.get_ghosts()
print(f"\nGhost documents ({len(ghosts)}):")
for g in ghosts:
    print(f"  · {g['filename']} — never retrieved, safe to remove")

dupes = corp.get_duplicates(threshold=0.85)
print(f"\nNear-duplicate pairs ({len(dupes)}):")
for d in dupes:
    print(f"  · {d['filename_a']}  ↔  {d['filename_b']}  (similarity: {d['similarity']:.2f})")

obsolete = corp.get_obsolete()
print(f"\nObsolete versions ({len(obsolete)}):")
for o in obsolete:
    print(f"  · {o['filename']}  → superseded by {o['superseded_by']}")

stale = corp.get_stale_embeddings()
print(f"\nStale embeddings ({len(stale)}):")
for s in stale:
    print(f"  · {s['filename']}  ({s['days_behind']}d behind source update)")

health = corp.corpus_health()
print(f"\nOverall health score:")
for k, v in health.items():
    print(f"  {k:<22}: {v}")

print(f"\n{'=' * 60}")
print(f"✓ Demo complete. Database written to {DB_PATH}")
print(f"{'=' * 60}")
