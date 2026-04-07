# Manual API Demo

Demonstrates corpulse's core API without any vector database. Uses `log_retrieval()` and `log_engagement()` directly to track corpus health.

Use this example if you don't use Qdrant, or want to understand the core API before adding a wrapper.

## What it does

1. Registers 10 sample documents with embeddings
2. Simulates 25 retrieval events via `log_retrieval()`
3. Simulates user engagement via `log_engagement()`
4. Marks a document source as updated (stale embedding detection)
5. Prints a full corpus health report with cleanup recommendations

## Prerequisites

```bash
pip install "git+https://github.com/arkadyb/corpulse"
```

## Run

```bash
python demo.py
```

## Sample Output

```
============================================================
CORPULSE  —  Manual API Demo
============================================================

✓ Registered 10 documents with embeddings

------------------------------------------------------------
Simulating retrieval events...
------------------------------------------------------------
  Q: "how do I get started?"
     → getting-started.md, security-overview.md, internal-draft.md
  Q: "API authentication docs"
     → api-reference-v2.md, changelog.md, troubleshooting.md
  Q: "environment setup steps"
     → setup-guide.md, setup-guide-copy.md, internal-draft.md
  Q: "fix connection timeout error"
     → troubleshooting.md, setup-guide.md, setup-guide-copy.md
  Q: "security compliance"
     → security-overview.md, getting-started.md, internal-draft.md

✓ Logged 25 retrieval events

Simulating user engagement...
✓ Engagement and source updates logged

============================================================
CORPUS HEALTH REPORT
============================================================

  corpulse — Corpus Health Report
  10 documents · last 30 days · ⚠ corpus bloat detected (70% noise est.)
  Document                             Retrieved   Engagement  Status
  ──────────────────────────────────────────────────────────────────────
  internal-draft.md                           16           0%  ◌  low eng.
  setup-guide.md                              11           0%  ◌  low eng.
  setup-guide-copy.md                         11           0%  ◌  low eng.
  getting-started.md                          10         150%  ✓  healthy
  security-overview.md                        10           0%  ◌  low eng.
  troubleshooting.md                           9          22%  ✓  healthy
  api-reference-v2.md                          4         375%  ✓  healthy
  changelog.md                                 4           0%  ◌  low eng.
  api-reference-v1.md                          0            —  👻 ghost
  pricing-2023.md                              0            —  👻 ghost

  👻 ghosts: 2  💀 obsolete: 1  ⚠ duplicates: 4  🕓 stale: 0
  Run corpulse.cleanup_report() for a prioritised action list.

------------------------------------------------------------
CLEANUP RECOMMENDATIONS
------------------------------------------------------------

────────────────────────────────────────────────────────────
  corpulse — Cleanup Report
────────────────────────────────────────────────────────────
  Total documents : 10
  Noise estimate  : 50%
  ⚠  Consider pruning ~5 low-signal documents.

  👻  GHOSTS  (2 docs — never retrieved in 30d)
      · api-reference-v1.md
      · pricing-2023.md

  💀  OBSOLETE  (1 docs)
      · api-reference-v1.md  →  superseded by api-reference-v2.md

  🔁  RE-CHUNK CANDIDATES  (4 docs — high retrieval, low engagement)
      · internal-draft.md  (16 retrievals, 0% engagement)
      · setup-guide.md  (11 retrievals, 0% engagement)
      · setup-guide-copy.md  (11 retrievals, 0% engagement)
      · security-overview.md  (10 retrievals, 0% engagement)

------------------------------------------------------------
DETAILED FINDINGS
------------------------------------------------------------

Ghost documents (2):
  · api-reference-v1.md — never retrieved, safe to remove
  · pricing-2023.md — never retrieved, safe to remove

Near-duplicate pairs (2):
  · setup-guide.md  ↔  setup-guide-copy.md  (similarity: 0.97)
  · api-reference-v2.md  ↔  api-reference-v1.md  (similarity: 0.96)

Obsolete versions (1):
  · api-reference-v1.md  → superseded by api-reference-v2.md

Stale embeddings (0):

Overall health score:
  total_docs            : 10
  ghosts                : 2
  obsolete              : 1
  stale                 : 0
  duplicates            : 4
  noise_estimate        : 0.5
  bloat_warning         : True
  recommendation        : Consider pruning ~5 low-signal documents.

============================================================
✓ Demo complete. Database written to ./manual_api_demo.db
============================================================
```
