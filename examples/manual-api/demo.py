"""
manual_api_demo.py — Showcases corpulse's manual API (no vector DB required).

Same knowledge base as qdrant_demo.py, but uses log_retrieval() directly
instead of wrapping a Qdrant client. Use this demo if you don't use Qdrant
or want to understand the core API before adding a wrapper.

This script:
  1. Registers 10 sample documents with embeddings
  2. Simulates retrieval events via log_retrieval()
  3. Simulates user engagement via log_engagement()
  4. Marks a document source as updated (stale embedding)
  5. Prints a corpus health report

Prerequisites:
  pip install "git+https://github.com/arkadyb/corpulse"
"""

import random
import numpy as np
from corpulse import Corpulse


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH = "./manual_api_demo.db"
VECTOR_DIM = 64

random.seed(42)
np.random.seed(42)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def random_vector(dim=VECTOR_DIM):
    """Generate a normalised random vector (simulates an embedding)."""
    v = np.random.randn(dim).astype(np.float32)
    return v / np.linalg.norm(v)

def similar_vector(base, noise=0.05):
    """Generate a vector close to `base` (simulates a near-duplicate)."""
    arr = np.array(base, dtype=np.float32)
    arr += np.random.randn(len(arr)).astype(np.float32) * noise
    return (arr / np.linalg.norm(arr))


# ---------------------------------------------------------------------------
# 1. Set up corpus — same 10 documents as qdrant_demo.py
# ---------------------------------------------------------------------------

print("=" * 60)
print("CORPULSE  —  Manual API Demo")
print("=" * 60)

corpulse_inst = Corpulse(db_path=DB_PATH)

DOCUMENTS = [
    {"id": "1",  "filename": "getting-started.md",     "topic": "getting-started"},
    {"id": "2",  "filename": "api-reference-v2.md",    "topic": "api"},
    {"id": "3",  "filename": "api-reference-v1.md",    "topic": "api"},            # obsolete
    {"id": "4",  "filename": "troubleshooting.md",     "topic": "troubleshooting"},
    {"id": "5",  "filename": "setup-guide.md",         "topic": "setup"},
    {"id": "6",  "filename": "setup-guide-copy.md",    "topic": "setup"},           # near-duplicate
    {"id": "7",  "filename": "pricing-2023.md",        "topic": "pricing"},         # stale embedding
    {"id": "8",  "filename": "internal-draft.md",      "topic": "internal"},        # ghost
    {"id": "9",  "filename": "security-overview.md",   "topic": "security"},
    {"id": "10", "filename": "changelog.md",           "topic": "changelog"},       # ghost
]

# Generate embeddings — same-topic docs get similar vectors
topic_vectors = {}
for doc in DOCUMENTS:
    topic = doc["topic"]
    if topic not in topic_vectors:
        topic_vectors[topic] = random_vector()

    if doc["filename"] == "setup-guide-copy.md":
        vec = similar_vector(topic_vectors["setup"], noise=0.02)
    else:
        vec = similar_vector(topic_vectors[topic], noise=0.03)

    corpulse_inst.register_document(doc["id"], doc["filename"], embedding=vec)

print(f"\n✓ Registered {len(DOCUMENTS)} documents with embeddings\n")


# ---------------------------------------------------------------------------
# 2. Simulate retrieval events via log_retrieval()
# ---------------------------------------------------------------------------

print("-" * 60)
print("Simulating retrieval events...")
print("-" * 60)

# Define which docs come back for which queries (mirrors qdrant_demo.py)
QUERIES = [
    ("how do I get started?",        [("1", "getting-started.md"),  ("9", "security-overview.md"),   ("8", "internal-draft.md")]),
    ("API authentication docs",      [("2", "api-reference-v2.md"), ("10", "changelog.md"),          ("4", "troubleshooting.md")]),
    ("environment setup steps",      [("5", "setup-guide.md"),      ("6", "setup-guide-copy.md"),    ("8", "internal-draft.md")]),
    ("fix connection timeout error", [("4", "troubleshooting.md"),  ("5", "setup-guide.md"),         ("6", "setup-guide-copy.md")]),
    ("security compliance",          [("9", "security-overview.md"),("1", "getting-started.md"),     ("8", "internal-draft.md")]),
]

# Run 25 queries — same count as qdrant_demo.py
for i, (query_text, result_docs) in enumerate(QUERIES):
    results = [
        {"doc_id": did, "filename": fname, "score": round(random.uniform(0.75, 0.97), 3)}
        for did, fname in result_docs
    ]
    corpulse_inst.log_retrieval(results, query=query_text)
    print(f"  Q: \"{query_text}\"")
    print(f"     → {', '.join(fname for _, fname in result_docs)}")

for _ in range(20):
    query_text, result_docs = random.choice(QUERIES)
    results = [
        {"doc_id": did, "filename": fname, "score": round(random.uniform(0.75, 0.97), 3)}
        for did, fname in result_docs
    ]
    corpulse_inst.log_retrieval(results, query=query_text)

print(f"\n✓ Logged {5 + 20} retrieval events\n")

# Note: docs "8" (internal-draft.md) and "10" (changelog.md) appear in results
# but docs "3" (api-reference-v1.md) and "7" (pricing-2023.md) are never
# retrieved — they become ghosts.


# ---------------------------------------------------------------------------
# 3. Simulate user engagement
# ---------------------------------------------------------------------------

print("Simulating user engagement...")

# Popular docs get high engagement
for _ in range(15):
    corpulse_inst.log_engagement("1", event="opened")   # getting-started.md
    corpulse_inst.log_engagement("2", event="opened")   # api-reference-v2.md

# Troubleshooting retrieved often but rarely opened (suspect)
for _ in range(2):
    corpulse_inst.log_engagement("4", event="opened")

# Mark pricing doc source as updated (stale embedding)
corpulse_inst.log_source_update("7")

print("✓ Engagement and source updates logged\n")


# ---------------------------------------------------------------------------
# 4. Print the corpus health report
# ---------------------------------------------------------------------------

print("=" * 60)
print("CORPUS HEALTH REPORT")
print("=" * 60)
print()

corpulse_inst.report(window_days=30)

print()
print("-" * 60)
print("CLEANUP RECOMMENDATIONS")
print("-" * 60)
print()

corpulse_inst.cleanup_report()

print()
print("-" * 60)
print("DETAILED FINDINGS")
print("-" * 60)

ghosts = corpulse_inst.get_ghosts()
print(f"\nGhost documents ({len(ghosts)}):")
for g in ghosts:
    print(f"  · {g['filename']} — never retrieved, safe to remove")

dupes = corpulse_inst.get_duplicates(threshold=0.85)
print(f"\nNear-duplicate pairs ({len(dupes)}):")
for d in dupes:
    print(f"  · {d['filename_a']}  ↔  {d['filename_b']}  (similarity: {d['similarity']:.2f})")

obsolete = corpulse_inst.get_obsolete()
print(f"\nObsolete versions ({len(obsolete)}):")
for o in obsolete:
    print(f"  · {o['filename']}  → superseded by {o['superseded_by']}")

stale = corpulse_inst.get_stale_embeddings()
print(f"\nStale embeddings ({len(stale)}):")
for s in stale:
    print(f"  · {s['filename']}  ({s['days_behind']}d behind source update)")

health = corpulse_inst.corpus_health()
print(f"\nOverall health score:")
for k, v in health.items():
    print(f"  {k:<22}: {v}")

print(f"\n{'=' * 60}")
print(f"✓ Demo complete. Database written to {DB_PATH}")
print(f"{'=' * 60}")
