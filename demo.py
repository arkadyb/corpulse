"""
demo.py — Simulates a realistic RAG corpus with all four problem types:
  - ghost docs (never retrieved)
  - obsolete versions (v1 alongside v2)
  - stale embeddings (source changed after embedding)
  - low-engagement docs (retrieved but ignored)
"""

import random
import time
import numpy as np
from rag_memento import Memento

random.seed(42)
np.random.seed(42)

memento = Memento(
    db_path="./demo_memento.db",
    ghost_threshold_days=30,
    duplicate_threshold=0.92,
    stale_threshold_days=14,
    top_k_report=15,
)

# ── helpers ───────────────────────────────────────────────────────────────────

def rand_vec(dim=64):
    v = np.random.randn(dim).astype(np.float32)
    return v / np.linalg.norm(v)

def near_vec(base, noise=0.05):
    v = base + np.random.randn(len(base)).astype(np.float32) * noise
    return v / np.linalg.norm(v)

def days_ago(n):
    return time.time() - n * 86_400


# ── corpus setup ──────────────────────────────────────────────────────────────

print("Setting up corpus...")

DOCS = [
    # (doc_id, filename, embedding_base_key, is_popular)
    ("doc_001", "onboarding-guide.md",      "onboarding",  True),
    ("doc_002", "api-reference-v2.md",      "api",         True),
    ("doc_003", "api-reference-v1.md",      "api",         True),   # obsolete
    ("doc_004", "setup-instructions.md",    "setup",       True),
    ("doc_005", "setup-instructions-2.md",  "setup",       True),   # near-duplicate
    ("doc_006", "pricing-policy.md",        "pricing",     False),  # stale embedding
    ("doc_007", "troubleshooting-faq.md",   "troubleshoot",False),  # low engagement
    ("doc_008", "security-overview.md",     "security",    False),
    ("doc_009", "release-notes-v1.md",      "release",     False),  # obsolete
    ("doc_010", "release-notes-v2.md",      "release",     False),
    ("doc_011", "legacy-setup-2021.md",     "legacy",      False),  # ghost
    ("doc_012", "internal-draft.md",        "internal",    False),  # ghost
    ("doc_013", "changelog.md",             "change",      False),  # ghost
]

# Generate base vectors per topic (docs in same topic are similar)
topic_vecs = {}
for _, _, topic, _ in DOCS:
    if topic not in topic_vecs:
        topic_vecs[topic] = rand_vec()

# Register all documents with embeddings
sixty_days_ago = days_ago(60)
for doc_id, filename, topic, _ in DOCS:
    vec = near_vec(topic_vecs[topic], noise=0.03)
    memento.register_document(doc_id, filename, embedding=vec)
    # Backdate the embedded_at for all docs
    memento.db.upsert_document(
        doc_id=doc_id,
        filename=filename,
        embedding=vec.tobytes(),
        embedded_at=sixty_days_ago,
    )

# Mark pricing-policy.md as updated recently (stale embedding)
memento.log_source_update("doc_006", updated_at=days_ago(5))

print(f"  Registered {len(DOCS)} documents\n")


# ── simulate 90 days of retrieval history ─────────────────────────────────────

print("Simulating retrieval history...")

QUERIES = [
    ("how to get started", ["doc_001", "doc_004", "doc_005"]),
    ("API endpoints list", ["doc_002", "doc_003", "doc_007"]),
    ("authentication setup", ["doc_001", "doc_002", "doc_008"]),
    ("pricing information",  ["doc_006", "doc_002"]),
    ("troubleshoot errors",  ["doc_007", "doc_001"]),
    ("security best practices", ["doc_008", "doc_002"]),
]

for day_offset in range(90, 0, -1):
    ts = days_ago(day_offset)
    # simulate 2-6 queries per day
    for _ in range(random.randint(2, 6)):
        query, base_results = random.choice(QUERIES)
        # shuffle rank slightly
        results = [
            {
                "doc_id":   did,
                "filename": next(f for d, f, _, _ in DOCS if d == did),
                "score":    round(random.uniform(0.75, 0.97), 3),
            }
            for did in base_results
        ]
        # Use raw db insert to backdate
        qhash = f"q{hash(query) % 10000:04d}"
        for rank, r in enumerate(results, 1):
            memento.db.upsert_document(r["doc_id"], r["filename"])
            memento.db.insert_retrieval(r["doc_id"], qhash, rank, r["score"], ts)

# Ghosts: doc_011, doc_012, doc_013 never inserted into retrievals — they just sit there

print(f"  Simulated retrieval events across 90 days\n")


# ── simulate engagement (users opening docs) ──────────────────────────────────

print("Simulating user engagement...")

# Popular docs get frequent engagement
HIGH_ENG  = {"doc_001": 0.60, "doc_002": 0.45, "doc_004": 0.40, "doc_008": 0.35}
LOW_ENG   = {"doc_003": 0.08, "doc_005": 0.10, "doc_006": 0.12, "doc_007": 0.08}

# Count retrievals per doc
for doc_id, eng_rate in {**HIGH_ENG, **LOW_ENG}.items():
    # Rough retrieval count from the last 30 days
    n = random.randint(20, 100)
    engagements = int(n * eng_rate)
    for _ in range(engagements):
        ts = days_ago(random.uniform(0, 30))
        memento.db.insert_engagement(doc_id, "opened", ts)

print(f"  Simulated engagement events\n")


# ── run all analysis ──────────────────────────────────────────────────────────

print("=" * 60)
print("ANALYSIS RESULTS")
print("=" * 60)

# 1. Full report
memento.report(window_days=30)

# 2. Detailed cleanup
memento.cleanup_report()

# 3. Specific queries
ghosts = memento.get_ghosts()
print(f"Ghost files ({len(ghosts)}):")
for g in ghosts:
    print(f"  · {g['filename']}")

print()
obsolete = memento.get_obsolete()
print(f"Obsolete files ({len(obsolete)}):")
for o in obsolete:
    print(f"  · {o['filename']}  →  superseded by {o['superseded_by']}")

print()
stale = memento.get_stale_embeddings()
print(f"Stale embeddings ({len(stale)}):")
for s in stale:
    print(f"  · {s['filename']}  ({s['days_behind']}d behind)")

print()
dupes = memento.get_duplicates(threshold=0.90)
print(f"Near-duplicate pairs ({len(dupes)}):")
for d in dupes:
    print(f"  · {d['filename_a']}  ↔  {d['filename_b']}  (sim={d['similarity']})")

print()
suspects = memento.get_suspects()
print(f"Re-chunk candidates ({len(suspects)}):")
for s in suspects:
    print(f"  · {s['filename']}  ({s['retrievals']} retrievals, {s['engagement_rate']*100:.0f}% engagement)")

print()
health = memento.corpus_health()
print("Corpus health summary:")
for k, v in health.items():
    print(f"  {k:<22}: {v}")

# 4. DataFrame export
print("\nDataFrame export (top 8 rows):")
df = memento.to_dataframe(window_days=30)
print(df.head(8).to_string(index=False))

print("\n✓ Demo complete. DB written to ./demo_memento.db")
