# Phase 17: Qdrant Tenant Helpers - Research

**Researched:** 2026-04-15
**Domain:** Qdrant Vector DB, Multi-tenancy, Indexing Primitives
**Confidence:** HIGH

## Summary

The goal of Phase 17 is to provide additive helper functions for Qdrant integration to make multi-tenancy and indexing easier. These helpers follow the existing lazy-import pattern and support both sync and async clients. They are designed to be standalone functions in `corpulse.integrations.qdrant` that take a client (or wrapped client) and perform common tasks like deterministic naming, chunk ID generation, document-level deletion, and idempotent collection setup.

**Primary recommendation:** Provide top-level functions `collection_name_for_user`, `chunk_id`, `delete_document_points`, and `ensure_collection` in `corpulse/integrations/qdrant.py`. Use a fixed project-wide UUID namespace (`corpulse.ai` via DNS) for deterministic chunk IDs and enforce `[a-z0-9_]` for sanitized collection names.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QDRT-HELP-01 | `collection_name_for_user(user_id, base="corpulse")` returns a deterministic, sanitized collection name using only `[a-z0-9_]`. | Qdrant allows `[a-z0-9_-.]` for names, but requirement restricts to `[a-z0-9_]`. Sanitization with `re` is verified. |
| QDRT-HELP-02 | `chunk_id(doc_id, chunk_index)` returns deterministic UUIDv5 identifiers for vector chunks. | `uuid.uuid5` with a fixed `CORPULSE_NAMESPACE` is standard for this purpose. |
| QDRT-HELP-03 | `delete_document_points(...)` removes Qdrant points for one document via payload filtering and exposes a clear result contract. | `client.delete()` supports `Filter` selectors. Both point-ID and payload-field selectors are supported. |
| QDRT-HELP-04 | `ensure_collection(...)` creates tenant-ready collections idempotently, including the required payload indexes. | `client.collection_exists()` and `client.create_payload_index()` provide the necessary idempotency primitives in Qdrant 1.8+. |
| QDRT-HELP-05 | Helper additions preserve the current lazy-import behavior of `corpulse.integrations.qdrant`. | Verified that importing `qdrant_client` inside functions satisfies this requirement. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| qdrant-client | 1.17.1 | Vector database client | Official client with full feature support [VERIFIED: pip show] |
| uuid | stdlib | Deterministic ID generation | Standard, robust, and zero-dependency [VERIFIED: stdlib] |
| re | stdlib | Input sanitization | Reliable for building safe identifiers [VERIFIED: stdlib] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| qdrant-server | 1.17.1 | Vector DB engine | Target environment for these helpers [VERIFIED: curl localhost:6333] |

**Version verification:** `qdrant-client` 1.17.1 was released around Feb 2025 and supports all required multi-tenancy features. [VERIFIED: PyPI]

## Architecture Patterns

### Recommended Project Structure
All additions live in `corpulse/integrations/qdrant.py` as top-level functions.

### Pattern 1: Lazy Import & Client Detection
To maintain the current behavior of not requiring `qdrant-client` on package import, all helpers that use Qdrant models import them inside the function body. Functions should handle both `QdrantClient` and `AsyncQdrantClient` (or their Corpulse wrappers) by using the client's own sync/async nature.

### Pattern 2: Deterministic Chunks (UUIDv5)
Use `uuid.uuid5` with a fixed `CORPULSE_NAMESPACE` derived from a project domain (`corpulse.ai`). This ensures that re-indexing the same document always yields the same chunk IDs, preventing duplicates even if documents are partially updated.

### Pattern 3: Idempotent Setup
`ensure_collection` follows a "check then create" pattern for collections and a "blind create" pattern for payload indexes (since Qdrant's `create_payload_index` is idempotent).

### Anti-Patterns to Avoid
- **Eager Imports:** Do NOT import `qdrant_client` or `models` at the module level.
- **Unsafe Names:** Do NOT use user input directly as collection names without regex sanitization.
- **Hand-rolled IDs:** Avoid using random IDs or non-namespaced hashes for chunks.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Collection sanitization | Complex regex replacements | `re.sub(r"[^a-z0-9_]+", "_", s.lower())` | Simple regex is safer and follows Qdrant rules. |
| Deterministic IDs | Custom hash truncation | `uuid.uuid5(namespace, name)` | Standard RFC 4122 compliant approach. |
| ID detection | `id.isnumeric()` etc | `isinstance(id, (int, str))` | Qdrant IDs can be integers or UUID strings. |

**Key insight:** Qdrant collection names are used directly in REST paths; strict sanitization is a security requirement (A11:2021 SSRF/Injection avoidance).

## Common Pitfalls

### Pitfall 1: Qdrant ID Types
**What goes wrong:** Assuming all Qdrant IDs are integers or all are UUIDs.
**Why it happens:** Qdrant supports both (64-bit uint and UUID strings), and libraries often only use one.
**How to avoid:** The helpers should accept both `int` and `str` and format them correctly.

### Pitfall 2: Async Client Awaitables
**What goes wrong:** Forgetting to `await` the result of a helper when using an async client.
**Why it happens:** Some helpers return results from the client directly.
**How to avoid:** If `client.delete()` returns a coroutine, the helper should return it as well. Users must `await` the helper if they passed an async client.

### Pitfall 3: Local Qdrant Indexes
**What goes wrong:** `create_payload_index` has no effect in local in-memory Qdrant.
**Why it happens:** The local storage implementation is simplified for unit testing. [CITED: qdrant-client docs]
**How to avoid:** Test suites should acknowledge the "Success" return code but note that local search performance won't reflect real index behavior.

## Code Examples

### `collection_name_for_user`
```python
def collection_name_for_user(user_id: str, base: str = "corpulse") -> str:
    # Sanitization logic: [a-z0-9_]
    sanitized = re.sub(r"[^a-z0-9_]+", "_", user_id.lower()).strip("_")
    return f"{base}_{sanitized}"
```

### `chunk_id`
```python
# Fixed namespace for the project
CORPULSE_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "corpulse.ai")

def chunk_id(doc_id: str | int, chunk_index: int) -> str:
    return str(uuid.uuid5(CORPULSE_NAMESPACE, f"{doc_id}:{chunk_index}"))
```

### `delete_document_points`
```python
def delete_document_points(client, collection_name, doc_id, payload_id_field="doc_id"):
    from qdrant_client import models
    if payload_id_field is None:
        selector = models.PointIdsList(points=[doc_id])
    else:
        selector = models.Filter(
            must=[
                models.FieldCondition(
                    key=payload_id_field,
                    match=models.MatchValue(value=doc_id),
                )
            ]
        )
    return client.delete(collection_name=collection_name, points_selector=selector)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Random IDs | Deterministic IDs | 1.0+ | Enables easy re-indexing and de-duplication [ASSUMED] |
| Global collection | Multi-tenancy via name | 1.0+ | Better security and scalability [ASSUMED] |
| Manual indexing | Idempotent helpers | 1.7+ | Reduced boilerplate for developers [CITED: qdrant.tech] |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `create_payload_index` is idempotent on server | Architecture | Minor (extra calls) |
| A2 | Users prefer `[a-z0-9_]` over `-` | collection_name | Minor (naming convention) |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.14.3 | — |
| qdrant-client | Integration | ✓ | 1.17.1 | — |
| Qdrant Server | Integration tests | ✓ | 1.17.1 | Use `:memory:` |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/test_qdrant_helpers.py` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QDRT-HELP-01 | Collection name sanitization | unit | `pytest -k collection_name` | ❌ |
| QDRT-HELP-02 | Deterministic chunk ID | unit | `pytest -k chunk_id` | ❌ |
| QDRT-HELP-03 | Document deletion by filter | integration | `pytest -k delete_document` | ❌ |
| QDRT-HELP-04 | Idempotent collection setup | integration | `pytest -k ensure_collection` | ❌ |

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V4 Access Control | yes | Tenant isolation via collection naming or payload filters |
| V5 Input Validation | yes | Regex sanitization for collection names [VERIFIED: re.sub] |

### Known Threat Patterns for Qdrant

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Collection name injection | Tampering | Sanitize user_id before formatting |
| Cross-tenant data leak | Disclosure | Mandatory filtering by tenant_id/doc_id |

## Sources

### Primary (HIGH confidence)
- [qdrant-client v1.17.1] - Verified version and features.
- [Python stdlib uuid/re] - Verified deterministic ID and regex patterns.
- [Local Environment] - Verified Python 3.14 and Qdrant Server availability.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified via local install and official docs.
- Architecture: HIGH - Follows existing project patterns and Qdrant best practices.
- Pitfalls: HIGH - Based on known Qdrant API transitions and multi-tenancy challenges.

**Research date:** 2026-04-15
**Valid until:** 2026-05-15
