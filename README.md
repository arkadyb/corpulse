# corpulse

Corpus health analytics for RAG pipelines. Track which documents help, which ones don't, and which ones are just noise.

---

## The Problem

Your vector database grows over time. Documents get added, re-chunked, and updated. Old versions linger. Near-identical content gets indexed twice. Outdated files keep surfacing in results. Without tracking, you're building on top of noise. corpulse surfaces these issues automatically.

---

## What corpulse is (and isn't)

corpulse measures **corpus health** — which documents are retrieved, how often, and whether users act on them.

It does **not** measure answer quality, faithfulness, or relevance. For that, see tools like Ragas or DeepEval.

Think of it as a fitness tracker for your document corpus, not a grade on your answers.

---

## Installation

```bash
# Core library (GitHub install — not yet on PyPI)
pip install "git+https://github.com/arkadyb/corpulse"

# With Qdrant wrapper support
pip install "corpulse[qdrant] @ git+https://github.com/arkadyb/corpulse.git"
```

Requires Python 3.10+. The `[qdrant]` extra installs `qdrant-client>=1.7`.

---

## Quickstart: Manual API

```python
from corpulse import Corpulse

corp = Corpulse()  # writes to ./corpulse.db

# After your vector DB search returns results
results = [
    {"doc_id": "abc123", "filename": "guide.md", "score": 0.91},
    {"doc_id": "def456", "filename": "faq.md",   "score": 0.87},
]
corp.log_retrieval(results, query="how to install?")

# When user acts on a result
corp.log_engagement("abc123", event="opened")

# Print corpus health table
corp.report()
```

`report()` pretty-prints with [tabulate](https://pypi.org/project/tabulate/) if installed, falls back to plain text otherwise.

---

## Quickstart: Qdrant Wrapper

**Before (manual instrumentation):**

```python
from qdrant_client import QdrantClient
from corpulse import Corpulse

client = QdrantClient(":memory:")
corp = Corpulse()

result = client.query_points(collection_name="docs", query=[0.1, 0.2, ...], limit=5)
# Must manually extract results and call log_retrieval
records = [
    {"doc_id": str(p.id), "filename": p.payload.get("filename", str(p.id)), "score": p.score}
    for p in result.points
]
corp.log_retrieval(records, query="how to install?")
```

**After (automatic via wrapper):**

```python
from qdrant_client import QdrantClient
from corpulse import Corpulse, QdrantCorpulseClient

client = QdrantClient(":memory:")
corp = Corpulse()
wrapped = QdrantCorpulseClient(client, corp)

result = wrapped.query_points(collection_name="docs", query=[0.1, 0.2, ...], limit=5)
# log_retrieval() called automatically — result is unchanged
```

**Async variant:**

```python
import asyncio
from qdrant_client import AsyncQdrantClient
from corpulse import Corpulse, AsyncQdrantCorpulseClient

async def main():
    client = AsyncQdrantClient(":memory:")
    corp = Corpulse()
    wrapped = AsyncQdrantCorpulseClient(client, corp)

    result = await wrapped.query_points(
        collection_name="docs", query=[0.1, 0.2, ...], limit=5
    )
    # log_retrieval() called automatically

asyncio.run(main())
```

**Constructor parameters:**

- `payload_id_field` — payload key to use as document ID (default: `None`, uses Qdrant point ID)
- `payload_filename_key` — payload key for filename (default: `"filename"`)

---

## Async usage

corpulse ships a fully async interface via `AsyncCorpulse`. It returns structured data instead of printing, making it ideal for web services and async pipelines.

```python
import asyncio
from corpulse import AsyncCorpulse
from corpulse.backends import AsyncPostgresBackend

async def main():
    backend = await AsyncPostgresBackend.create(
        "postgresql://user:pass@localhost/mydb"
    )
    async with AsyncCorpulse(backend=backend) as corp:
        # Ingest: called after every vector DB query in your RAG pipeline
        await corp.log_retrieval(
            [{"doc_id": "abc123", "filename": "guide.md", "score": 0.91}],
            query="how to install?",
        )
        await corp.log_engagement("abc123", event="opened")

        ghosts = await corp.get_ghosts()
        print(f"Ghost docs: {len(ghosts)}")

        report = await corp.report(window_days=30)
        print(report["summary"])
        print(report["rows"][:3])

        cleanup = await corp.cleanup_report()
        print(cleanup["ghosts"])
        print(cleanup["suspects"])

asyncio.run(main())
```

`AsyncCorpulse.report()` and `AsyncCorpulse.cleanup_report()` return dictionaries with structured payloads, so you can log them, send them over HTTP, or render them in your own UI without parsing stdout.

## Generation trace capture

corpulse also supports append-only trace capture for future generation metrics. Use it to store the prompt or query text, the retrieved context references you fed into generation, the final answer text, and optional evaluation labels.

```python
from corpulse import Corpulse

corp = Corpulse()
corp.log_generation_trace(
    prompt_text="Answer the user's question",
    retrieved_context_refs=[{"doc_id": "abc123", "chunk_id": "c-1"}],
    final_answer_text="Here is the response.",
    evaluation_labels=["grounded"],
)

traces = corp.get_generation_traces()
```

Trace records are read-only once written and do not change any existing corpus-health analytics.

---

## What It Measures

- Ghost documents — registered but never retrieved within a time window
- Near-duplicates — embedding pairs above a cosine similarity threshold (requires scikit-learn)
- Obsolete versions — e.g. `api-v1.md` superseded by `api-v2.md`
- Stale embeddings — source file updated but embedding not refreshed
- Low-engagement suspects — retrieved often but users rarely act on them
- Mean Reciprocal Rank — retrieval-order quality proxy based on existing ranks plus engagement overlap
- User Acceptance Rate — share of engagement rows whose `event_type` is one of `opened`, `clicked`, `copied`, or `thumbs_up`
- Generation trace capture — append-only prompt/query text, retrieved context refs, final answer text, and optional labels for future generation metrics

---

## Configuration

```python
corp = Corpulse(
    db_path="./corpulse.db",          # SQLite database path
    ghost_threshold_days=30,         # Days before flagging as ghost
    duplicate_threshold=0.92,        # Cosine similarity threshold
    stale_threshold_days=14,         # Days of source-vs-embedding lag
    obsolete_pattern=r"v\d+",        # Regex for version detection in filenames
    top_k_report=20,                 # Documents shown in report()
)
```

---

## Analysis Methods

All analysis methods use the configured lookback window. If you do not pass `window_days`, corpulse uses `ghost_threshold_days`.

| Method | What it measures | Example use |
|--------|------------------|-------------|
| `get_ghosts()` | Documents that were registered but not retrieved during the lookback window. | Find files that exist in the index but never show up in search, such as a stale draft nobody clicks. |
| `get_duplicates()` | Pairs of documents whose embeddings are above the configured cosine similarity threshold. | Spot near-identical files like `api-v1.md` and `api-v1-copy.md` that are both being indexed. |
| `get_obsolete()` | Older documents that appear to have been superseded by a newer filename version. | Detect versioned docs such as `guide-v1.md` that should probably be replaced by `guide-v2.md`. |
| `get_stale_embeddings()` | Documents whose source file timestamp is newer than the stored embedding timestamp. | Catch a document that was edited yesterday but still has an embedding from last week. |
| `get_suspects()` | Documents with high retrieval volume but low engagement rate. | Identify pages that are frequently returned by search but rarely opened or acted on. |
| `mean_reciprocal_rank()` | A retrieval-order quality proxy based on retrieval rank and whether the document was engaged with. Higher is better. | Use it to check whether documents that users actually interact with tend to appear near the top of results. |
| `acceptance_rate()` | The share of engagement events whose normalized `event_type` is in the accepted allowlist: `opened`, `clicked`, `copied`, or `thumbs_up`. | If you log 80 total engagement events and 60 are opens/clicks/copies/thumbs-up, the acceptance rate is `0.75`. |
| `corpus_health()` | A summary of corpus noise: ghosts, obsolete docs, stale embeddings, duplicates, plus a bloat warning and recommendation. | Get a quick “how healthy is my index?” snapshot before deciding whether cleanup is urgent. |
| `to_dataframe()` | A per-document pandas DataFrame with retrievals, engagements, engagement rate, and status. | Load the full stats into a notebook or BI tool to sort by retrievals and inspect outliers. |
| `report()` | A human-readable corpus health report printed to stdout. | Run it in a CLI job or cron task to print a quick snapshot without writing custom formatting code. |
| `cleanup_report()` | A prioritized cleanup payload with ghosts, obsolete docs, stale embeddings, and suspects. | Feed it into a maintenance workflow that decides what to delete, refresh, or review first. |

---

## License

MPL 2.0 — see [LICENSE](LICENSE) for details.
