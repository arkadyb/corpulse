# Stack Research

**Domain:** Python library — Qdrant vector DB wrapper for RAG corpus analytics
**Researched:** 2026-03-24
**Confidence:** HIGH (all critical facts verified against PyPI/official docs)

## Context

This research covers only the new additions for the Qdrant wrapper milestone. The existing stack (SQLite, numpy, sklearn, pandas, tabulate) is not re-researched. The question is: what is needed to add a `QdrantMemento` wrapper that auto-captures queries and results from Qdrant without manual instrumentation?

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| qdrant-client | 1.17.1 | Qdrant Python client — the thing being wrapped | Only official client; Apache-2.0 licensed; ships `QdrantClient` (sync) and `AsyncQdrantClient` (async); Python 3.10+ (matches project constraint); actively maintained by Qdrant team; in-memory mode (`":memory:"`) enables zero-infrastructure testing |
| Python | 3.10+ | Runtime (align with project constraint) | qdrant-client 1.17.1 requires Python >=3.10; project already targets 3.10+; use of `str | None` unions (PEP 604) is already in the codebase |

### Wrapper Pattern

The wrapper is a composition-over-inheritance proxy: `QdrantMemento` holds a real `QdrantClient` internally, delegates all calls to it, and intercepts `query_points` / `search` to call `memento.log_retrieval()` automatically.

**Do not subclass `QdrantClient`.** The class is large, uses private internals, and subclassing breaks with client upgrades. Composition is the documented pattern for this type of instrumentation wrapper.

Key method to intercept: `query_points()` — this is the unified query API introduced in client 1.7.1 (server 1.6). The older `search()` method still exists but is soft-deprecated in favour of `query_points`. The wrapper must intercept both for backward compatibility.

Return type from both methods: `list[ScoredPoint]` (sync) or async equivalent.

`ScoredPoint` fields available to the wrapper:
- `.id` — Qdrant point ID (int or UUID string); use as `doc_id`
- `.score` — float similarity score; map to `log_retrieval`'s `score` field
- `.payload` — `dict | None`; can contain `filename` or other metadata; extract if present
- `.vector` — embedding array if `with_vectors=True` was passed; feed to `embedding` field of `log_retrieval`

### Build / Packaging

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| hatchling | latest (via `pip`) | Build backend for pyproject.toml | Standard modern choice for pure-Python libraries; no mandatory lock file; supports `[project.optional-dependencies]` cleanly; widely understood by contributors; lighter than Poetry for a library with no complex dependency graph |
| pyproject.toml (PEP 517/621) | — | Package declaration | The only standard format in 2025; replaces setup.py/setup.cfg entirely for pure-Python projects |

**Optional dependency groups for pyproject.toml:**

```toml
[project.optional-dependencies]
qdrant  = ["qdrant-client>=1.7.1"]
sklearn = ["scikit-learn>=1.0"]
pandas  = ["pandas>=1.3"]
reports = ["tabulate>=0.8"]
all     = [
    "qdrant-client>=1.7.1",
    "scikit-learn>=1.0",
    "pandas>=1.3",
    "tabulate>=0.8",
]
```

Minimum qdrant-client pin: `>=1.7.1` (when `query_points` was added). Not `>=1.17.1` — don't pin to latest; users may run older patch versions.

### Testing

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pytest | >=9.0 | Test runner | De facto standard; version 9.0 (Nov 2025) dropped Python 3.9 support, aligns with project's 3.10+ target; fixture system makes Qdrant in-memory setup clean |
| pytest-mock | >=3.12 | Mocking `QdrantClient` internals | Thin wrapper over `unittest.mock`; provides `mocker` fixture for easy patching; `create_autospec()` lets you mock `QdrantClient` with its real interface enforced |

**Testing strategy for the wrapper (no mock needed for unit tests):**

Use `QdrantClient(":memory:")` — the client's built-in in-memory mode. It runs a full local Qdrant instance in-process. This means wrapper tests can create real collections, insert real points, and call real `query_points()` without a running server or mocking. This is the correct approach — tests verify the wrapper's interception logic against the real client interface.

Reserve `pytest-mock` for testing edge cases (e.g., what happens when `payload` is `None`, when Qdrant raises an exception).

---

## Installation

```bash
# Library users: install with Qdrant extras
pip install "rag-memento[qdrant]"

# Development (from repo root)
pip install -e ".[qdrant,sklearn,pandas,reports]"

# Dev tools only
pip install pytest>=9.0 pytest-mock>=3.12
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Composition proxy (`QdrantMemento` wraps `QdrantClient`) | Subclass `QdrantClient` | Never — Qdrant client uses private internals and generated code; subclassing is fragile across versions |
| `QdrantClient(":memory:")` for tests | Docker + real Qdrant server | Integration/performance tests in CI; not needed for wrapper unit tests |
| hatchling build backend | setuptools | If you need C extensions or a custom build hook that hatchling can't handle; not applicable here |
| hatchling build backend | flit | If the package has literally zero optional deps and needs minimal config; flit lacks extras grouping flexibility |
| `query_points` as primary intercept point | `search` as primary intercept point | Never; `search` is deprecated; intercept both but document `query_points` as the primary API |
| Pin `qdrant-client>=1.7.1` | Pin `>=1.17.1` (latest) | Never pin to latest in a library; users need version flexibility |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `wrapt` or `objproxies` | These transparent proxy libraries add complexity for no gain; rag-memento only needs to intercept 2 methods (`search`, `query_points`), not every attribute access | Explicit composition: `QdrantMemento.__init__` takes a `QdrantClient` and delegates explicitly |
| Monkey-patching the real `QdrantClient` | Modifies global state; breaks if two parts of user code share a client; hard to test | Explicit wrapper class |
| `fastembed` extras from qdrant-client | rag-memento doesn't generate embeddings; it captures what Qdrant already returns | Use `with_vectors=True` in `query_points` to retrieve vectors that Qdrant already computed |
| Poetry as build/package manager | Introduces a lock file and Poetry-specific pyproject.toml format that complicates GitHub-only distribution and contributor onboarding | hatchling + pip; users install directly from GitHub with `pip install git+https://...` |
| `setup.py` / `setup.cfg` | Deprecated; no advantage for a pure-Python library | `pyproject.toml` with hatchling backend |

---

## Stack Patterns by Variant

**If the user's code uses sync `QdrantClient`:**
- Wrap with `QdrantMemento(client)` — intercept `search()` and `query_points()`
- No async needed; `log_retrieval` is synchronous SQLite write, fast enough in-band

**If the user's code uses `AsyncQdrantClient`:**
- Provide `AsyncQdrantMemento` that wraps `AsyncQdrantClient`
- Intercept `async def search()` and `async def query_points()` with `async def` overrides
- Call `self._memento.log_retrieval(...)` synchronously inside the async intercept (SQLite write is fast; no need to make the analytics layer async)
- This is a v2 concern; for the current milestone, sync-only is sufficient

**If the user stores `doc_id` as an integer Qdrant point ID:**
- `ScoredPoint.id` is `int | str`; call `str(point.id)` before passing to `log_retrieval`
- Document this clearly; rag-memento uses `TEXT` doc_id in SQLite

**If the user stores filename in Qdrant payload:**
- Look for `point.payload.get("filename")` or `point.payload.get("name")` or `point.payload.get("source")`
- Wrapper should accept a `payload_filename_key: str = "filename"` constructor argument to let users configure which payload field to use

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| qdrant-client>=1.7.1 | Python >=3.10 | `query_points` API added in 1.7.1 alongside Qdrant server 1.6; older client only has `search()` |
| qdrant-client 1.17.1 | Python 3.10–3.14 | Verified against PyPI (released 2026-03-13) |
| pytest>=9.0 | Python >=3.10 | pytest 9.0 dropped Python 3.9; aligns with project baseline |
| numpy (existing dep) | qdrant-client 1.17.x | qdrant-client bundles its own numpy usage; no conflict with rag-memento's existing numpy dep |

---

## Sources

- [qdrant-client PyPI](https://pypi.org/project/qdrant-client/) — version 1.17.1 confirmed (2026-03-13), Python >=3.10 requirement, optional extras (fastembed). **HIGH confidence.**
- [Qdrant Python Client docs — Quickstart](https://python-client.qdrant.tech/quickstart) — `search()` and `query_points()` method signatures, `ScoredPoint` fields (id, score, payload, vector), in-memory mode `":memory:"`. **HIGH confidence.**
- [qdrant_client.qdrant_client module docs](https://python-client.qdrant.tech/qdrant_client.qdrant_client) — `query_points`, `query_batch_points` signatures and return types. **HIGH confidence.**
- [Qdrant hybrid search article](https://qdrant.tech/articles/hybrid-search/) — confirms `query_points` introduced in client 1.7.1 as unified replacement for `search`. **HIGH confidence.**
- [Python Packaging User Guide — Writing pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — `[project.optional-dependencies]` syntax confirmed as current standard. **HIGH confidence.**
- [Python Build Backends in 2025 — Medium](https://medium.com/@dynamicy/python-build-backends-in-2025-what-to-use-and-why-uv-build-vs-hatchling-vs-poetry-core-94dd6b92248f) — hatchling vs uv_build vs poetry-core comparison. **MEDIUM confidence** (community article, not official).
- [pytest PyPI](https://pypi.org/project/pytest/) — version 9.0.2 confirmed as latest (2025-12-06), Python >=3.10 requirement. **HIGH confidence.**
- [pytest-mock GitHub](https://github.com/pytest-dev/pytest-mock) — current maintenance status confirmed. **HIGH confidence.**

---
*Stack research for: Qdrant wrapper addition to rag-memento*
*Researched: 2026-03-24*
