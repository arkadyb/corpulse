# Phase 18: Indexing Pipeline MVP - Research

**Researched:** 2026-04-15
**Domain:** Async Indexing Pipelines / RAG Orchestration
**Confidence:** HIGH

## Summary

Phase 18 ships a minimal async indexing pipeline (`corpulse.pipelines.indexing.index_document`) that orchestrates the flow from source document to search-ready vectors and Corpulse-registered metadata. The pipeline is designed around provider-agnostic protocols (`Parser`, `Chunker`, `Embedder`) to ensure flexibility across different LLM and parsing backends.

Key features include:
- **Resilient Embedding:** Integrated retry logic with exponential backoff for embedding calls.
- **Transactional Rollback:** Automatic deletion of Qdrant points if the subsequent registration in Corpulse fails, preventing "ghost" data in the vector database.
- **Standardized Ingestion:** Use of deterministic UUID generation for chunks and mean-embedding registration for document-level analytics.

**Primary recommendation:** Use `typing.Protocol` for interface definitions and a simple `try-except` block around the Qdrant and Corpulse calls to manage rollback of vector points.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-01 | `index_document(...)` orchestration flow. | Verified `AsyncCorpulse` and Qdrant client APIs for integration. |
| PIPE-02 | Retry logic for embedding failures. | Standard async retry patterns identified (exponential backoff). |
| PIPE-03 | Qdrant rollback on failure. | Verified `delete_document_points` helper in `corpulse.integrations.qdrant`. |
| PIPE-04 | Minimal result contract. | Defined `IndexingResult` dataclass with specified fields. |
| PIPE-05 | Pipeline tests using fakes. | `pytest-asyncio` and `unittest.mock` confirmed as standard stack. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `qdrant-client` | 1.17.1 | Vector database interaction | Primary vector DB integration for Corpulse v1.3. |
| `AsyncCorpulse` | 0.1.0 | Document registration and health tracking | Core library for analytics. |
| `typing.Protocol` | 3.10+ | Interface definitions | Decouples orchestration from specific provider implementations. |
| `dataclasses` | 3.7+ | Result contract | Lightweight, typed data structure for function returns. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| `numpy` | >=1.24 | Vector averaging | Calculating mean document embedding from chunks. |
| `tenacity` | (Optional) | Robust retry logic | If complex retry policies (jitter, max time) are needed. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `typing.Protocol` | ABC (Abstract Base Class) | Protocols are structurally typed and don't require explicit inheritance. |
| `tenacity` | Hand-rolled `asyncio.sleep` loop | Hand-rolled avoids a new dependency but is more error-prone for complex logic. |

## Architecture Patterns

### Recommended Project Structure
```
corpulse/
├── pipelines/
│   ├── __init__.py
│   └── indexing.py        # index_document and Protocols
```

### Pattern 1: Protocol-Driven Orchestration
The pipeline receives instances of `Parser`, `Chunker`, and `Embedder`. This allows the same pipeline to handle PDF parsing via `Tesseract` or `PyMuPDF` and embedding via `OpenAI` or `HuggingFace` without modification.

### Anti-Patterns to Avoid
- **Hard-coding Chunk IDs:** Always use `corpulse.integrations.qdrant.chunk_id` to ensure deterministic, stable IDs that match future deletion/update operations.
- **Ignoring Partial Failures:** Upserting to Qdrant without a `try-except` around subsequent steps leads to inconsistent states (vectors exist but document is unknown to Corpulse).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chunk ID Generation | Custom string hashing | `qdrant.chunk_id(doc_id, index)` | Stability via UUIDv5 and standard namespace. |
| Qdrant Point Deletion | Manual filter building | `qdrant.delete_document_points` | Handles both sync and async clients and consistent filters. |
| Retries | Complex recursion | `tenacity` or standard loop | Recursion hits stack limits; loops are clearer for retry logic. |

## Common Pitfalls

### Pitfall 1: Missing Payload for Deletion
**What goes wrong:** `delete_document_points` fails to find anything to delete.
**Why it happens:** The `doc_id` was not included in the payload during `upsert`.
**How to avoid:** Ensure every `PointStruct` has `payload={"doc_id": doc_id, ...}`.

### Pitfall 2: Async Client Confusion
**What goes wrong:** `client.upsert` or `client.delete` are called but not awaited.
**Why it happens:** Passing an `AsyncQdrantClient` to a function expecting a sync client (or vice versa).
**How to avoid:** Use `inspect.iscoroutinefunction` or strictly type for `AsyncQdrantClient`.

### Pitfall 3: Large Document Timeouts
**What goes wrong:** Processing a 1000-page document times out the `index_document` call.
**Why it happens:** Single-batch embedding and upsert.
**How to avoid:** For MVP, keep it simple but document that batching for very large files is a future optimization.

## Code Examples

### Protocols and Result Contract
```python
from typing import Any, Protocol, runtime_checkable
from dataclasses import dataclass

@dataclass
class IndexingResult:
    doc_id: str
    chunk_count: int
    duration_ms: float

@runtime_checkable
class Parser(Protocol):
    async def parse(self, source: Any) -> str: ...

@runtime_checkable
class Chunker(Protocol):
    async def chunk(self, text: str) -> list[str]: ...

@runtime_checkable
class Embedder(Protocol):
    async def embed(self, chunks: list[str]) -> list[list[float]]: ...
```

### Minimal Retry Pattern (No dependency)
```python
async def with_retry(coro_func, *args, max_attempts=3, backoff_base=2):
    for attempt in range(max_attempts):
        try:
            return await coro_func(*args)
        except Exception:
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(backoff_base ** attempt)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sync ingestion | Full async pipeline | v1.3 | Non-blocking processing for web services. |
| Manual cleanup | Transactional Rollback | v1.3 (this phase) | Reliable vector DB state on application failure. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `tenacity` is preferred for retries. | Standard Stack | Minimal (can fall back to hand-rolled loop). |
| A2 | Corpulse duplicate detection needs mean-embeddings. | Architecture | MEDIUM: duplicate detection might be less accurate without it. |
| A3 | Qdrant `upsert` is idempotent. | Summary | LOW: standard Qdrant behavior. |

## Open Questions

1. **Should we support named vectors in the MVP? (RESOLVED)**
   - Decision: Add an optional `vector_name: str | None = None` parameter to `index_document` and the `Embedder` protocol to support named vectors in Qdrant collections.
2. **Should rollback also affect Corpulse? (RESOLVED)**
   - Decision: Rollback focuses on Qdrant points. If `register_document` fails, no document was successfully added to Corpulse, so no explicit Corpulse rollback is needed beyond ensuring the vector database is cleaned up.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `qdrant-client` | Vector Storage | ✓ | 1.17.1 | — |
| `AsyncCorpulse`| Registry | ✓ | 0.1.0 | — |
| `tenacity` | Retries | ✗ | — | Hand-rolled loop |
| `numpy` | Vector Math | ✓ | 1.26.4 | — |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/test_indexing_pipeline.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-01 | Full orchestration flow | integration | `pytest tests/test_indexing_pipeline.py::test_happy_path` | ❌ Wave 0 |
| PIPE-02 | Retry on embedding failure | unit | `pytest tests/test_indexing_pipeline.py::test_retry_logic` | ❌ Wave 0 |
| PIPE-03 | Rollback Qdrant on Corpulse failure | integration | `pytest tests/test_indexing_pipeline.py::test_rollback` | ❌ Wave 0 |

### Wave 0 Gaps
- [ ] `tests/test_indexing_pipeline.py` — New test file needed.
- [ ] Mocks/Fakes for `Parser`, `Chunker`, `Embedder`.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | Validate `doc_id` and `collection_name` before use. |
| V13 API and Web Service | yes | Ensure timeouts are handled for external LLM calls. |

### Known Threat Patterns for Indexing Pipeline

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Resource Exhaustion | Denial of Service | Rate limit indexing calls; bounded retries. |
| Data Leakage | Information Disclosure | Ensure `user_id` is sanitized in collection names (Phase 17). |

## Sources

### Primary (HIGH confidence)
- `corpulse/integrations/qdrant.py` - Verified `delete_document_points` and `chunk_id`.
- `corpulse/async_core.py` - Verified `register_document` and `delete_document`.
- `pyproject.toml` - Verified current dependencies and versions.

### Secondary (MEDIUM confidence)
- Qdrant documentation (external) - Verified `upsert` idempotency and filter-based deletion.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Core dependencies verified.
- Architecture: HIGH - Follows existing patterns in Phase 17.
- Pitfalls: HIGH - Common async/vector DB issues well-documented in training data.

**Research date:** 2026-04-15
**Valid until:** 2026-05-15
