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

---

## What It Measures

- Ghost documents — registered but never retrieved within a time window
- Near-duplicates — embedding pairs above a cosine similarity threshold (requires scikit-learn)
- Obsolete versions — e.g. `api-v1.md` superseded by `api-v2.md`
- Stale embeddings — source file updated but embedding not refreshed
- Low-engagement suspects — retrieved often but users rarely act on them
- Mean Reciprocal Rank — retrieval-order quality proxy based on existing ranks plus engagement overlap
- User Acceptance Rate — share of engagement rows whose `event_type` is one of `opened`, `clicked`, `copied`, or `thumbs_up`

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

| Method | Returns |
|--------|---------|
| `get_ghosts()` | Documents never retrieved in threshold window |
| `get_duplicates()` | Embedding-similar document pairs |
| `get_obsolete()` | Documents superseded by newer versions |
| `get_stale_embeddings()` | Documents with outdated embeddings |
| `get_suspects()` | High-retrieval, low-engagement documents |
| `mean_reciprocal_rank()` | Retrieval-ordering proxy over retrieval rank and engagement overlap |
| `acceptance_rate()` | Share of accepted engagement rows in the lookback window |
| `corpus_health()` | Overall noise estimate and bloat warning |
| `to_dataframe()` | Full stats as pandas DataFrame |
| `report()` | Print corpus health table to stdout |
| `cleanup_report()` | Print prioritised action list |

---

## License

MPL 2.0 — see [LICENSE](LICENSE) for details.
