---
task: 260415-hyj
type: quick-task-summary
date_completed: 2026-04-15
commits:
  - 8742c4e
---

# Quick Task 260415-hyj Summary

Reviewed the six proposed specs against the current corpulse codebase. The result is not "implement in the suggested order." Two specs are easy additive wins, two are valuable but real backend refactors, and two need redesign because the proposed API shape conflicts with what the library already documents and tests.

## Current Constraints That Matter

1. The Postgres backends hardcode table names in both DDL and every DML query, so multi-tenancy requires a systematic refactor rather than a few optional constructor args.
2. `corpulse/integrations/qdrant.py` is intentionally lazy-imported so `import corpulse` works without `qdrant-client`; any helper additions must preserve that property.
3. `AsyncCorpulse.report()` and `AsyncCorpulse.cleanup_report()` are documented in `README.md` and asserted in `tests/test_async_core_integration.py` to return dictionaries today.
4. `cleanup_report()` is an analysis/reporting API, not a mutating cleanup API. Any proposed `CleanupResult` model that reports deleted documents is describing a different operation than the current method.

## Spec-by-Spec Recommendation

### Spec 1 — Multi-tenancy via `schema` / `table_prefix`

**Value:** High. This is the most important library-level SaaS readiness improvement because it removes the need for private schema bootstrapping in consumers.

**What it takes:**
- Add identifier validation helper(s) for `schema`, `table_prefix`, and probably `base table name`.
- Replace the current static `SCHEMA` string in `corpulse/backends/postgres.py` with a SQL builder that can emit optional `CREATE SCHEMA IF NOT EXISTS ...`, schema-qualified table names, and prefix-adjusted table and index names.
- Add a shared table-name helper on both Postgres backends, e.g. `_t("documents")`, and route every query through it.
- Refactor async Postgres to consume the same schema builder rather than splitting `SCHEMA` into statements from a static constant.
- Extend both sync and async backend tests with invalid identifier rejection, prefix-only SQL generation, and per-schema isolation.

**Rationale / best way:**
- The best implementation is a shared identifier-and-DDL layer in `corpulse/backends/postgres.py`, reused by `postgres_async.py`.
- Do not put `schema` or `table_prefix` into `StorageBackend` in `base.py`; those are Postgres-specific construction concerns, not cross-backend contract features.
- Expose `build_schema_sql(schema=None, prefix="")` from the Postgres module, not from the generic backend base.

**Risk:** Medium-high, but contained. The risk is mostly SQL string generation and keeping sync/async parity.

### Spec 2 — Qdrant tenant helpers

**Value:** Medium-high. These are useful generic recipes and complement the new `delete_document()` API well.

**What it takes:**
- Add additive helper functions for collection naming, deterministic chunk IDs, point deletion by payload filter, and idempotent collection creation.
- Preserve lazy import behavior with local imports or `TYPE_CHECKING` plus string annotations.
- Add focused tests for deterministic UUIDv5 output, user-ID sanitization, idempotent collection setup, and delete-by-filter semantics.

**Rationale / best way:**
- Keep this additive and separate from the wrapper classes.
- `collection_name_for_user()` should be strict and deterministic. Lowercase and replace all non `[a-z0-9_]` characters.
- `chunk_id()` is a clean UUIDv5 helper and low risk.
- `delete_document_points()` should count before delete only if you truly need a return count; otherwise return `None` and avoid the extra network call.
- `ensure_collection()` is best if it accepts optional vector config overrides rather than baking in one rigid schema forever.

**Risk:** Low-medium. The main trap is accidentally breaking lazy-import behavior or overfitting the helper surface to one showcase app.

### Spec 3 — `corpulse.fastapi` router helper

**Value:** Medium. Useful, but not the first thing the library needs.

**What it takes:**
- New `corpulse/fastapi/` package and optional dependency group.
- Response models for route schemas.
- A small router factory that wires a request-scoped `AsyncCorpulse` resolver into seven handlers.
- FastAPI tests with a dummy factory and route/schema assertions.

**Rationale / best way:**
- This should be optional and isolated, exactly as proposed.
- The router is reasonable only after the response-model story is settled.
- It should depend on models that match the current library semantics, not on Spec 6 as currently written.

**Risk:** Medium. The router code itself is easy; the real risk is freezing an HTTP-facing response surface before the library payload models are designed correctly.

### Spec 4 — Index pipeline skeleton

**Value:** Medium-high, but only after specs 1 and 2 are settled.

**What it takes:**
- New `corpulse/pipelines/indexing.py` with parser/chunker/embedder protocols and an orchestrator.
- Retry policy implementation for embeddings.
- Rollback integration with Qdrant delete helpers.
- Fakes-based tests for happy path and rollback behavior.

**Why the current spec needs adjustment first:**
- `corpulse.register_document(doc_id, filename, chunk_count)` does not match the current API. `register_document()` only accepts `doc_id`, `filename`, and optional embedding.
- `token_count` cannot be computed generically without a tokenizer contract. The current proposal has no tokenizer input.
- Storing full chunk text in payload is a product decision with potentially large storage cost; it should be explicit and likely optional.

**Best way:**
- Redesign this spec before implementation.
- Keep the first version minimal: return `doc_id`, `chunk_count`, and `duration_ms`; make `token_count` optional or drop it; call `corpulse.register_document(doc_id, filename)` only after successful vector upsert; use `delete_document_points()` for rollback.

**Risk:** High if implemented as written. Moderate if the API is narrowed first.

### Spec 5 — Native SQLAlchemy async DSN support

**Value:** High per unit effort. This is the cleanest immediate improvement.

**What it takes:**
- Add `_normalize_dsn()` helper(s) in Postgres sync and async modules.
- Normalize before creating pools.
- Add tests for passthrough and stripped-dialect forms.

**Rationale / best way:**
- Implement this first.
- Keep the helper tiny and regex-based as proposed.
- Apply it in both backends for symmetry, even though the practical pain is on async.

**Risk:** Low. This is pure input normalization with a narrow test surface.

### Spec 6 — Typed Pydantic return models for `report()` / `cleanup()`

**Value:** Potentially high, but the proposed shape is wrong for the current library.

**Why the current spec is not ready:**
- `AsyncCorpulse.report()` currently returns a structured report payload with `summary` and `rows`; the proposed `CorpusReport` model is a different aggregate-only shape.
- `cleanup_report()` currently returns an analysis payload about ghosts/obsolete/stale/suspects; the proposed `CleanupResult` describes a destructive cleanup operation with `deleted_documents`, `deleted_chunks`, and `dry_run`.
- README and tests explicitly describe dict payloads today. Replacing them with Pydantic models is a real public API change, not a transparent refactor.

**Best way:**
- Do not implement this spec as written.
- If typed models are desired, start with models that mirror the existing payloads exactly: `ReportSummary`, `ReportRow`, `CorpusReportPayload`, `CleanupSection`, and `CleanupReportPayload`.
- Add model-returning helpers first, while keeping `report()` and `cleanup_report()` returning dicts for backward compatibility.
- If you want a mutating cleanup API, design that separately as a new method such as `cleanup(...)`, not by overloading `cleanup_report()`.

**Risk:** High as written because it changes semantics, docs, tests, and likely downstream HTTP/UI assumptions.

## Recommended Implementation Order

1. **Spec 5 — DSN normalization**
2. **Spec 1 — Multi-tenancy**
3. **Spec 2 — Qdrant helpers**
4. **Spec 4 — Index pipeline skeleton, but only after redesign**
5. **Spec 6 — Typed models, but only after redesign**
6. **Spec 3 — FastAPI router helper**

### Why this order is better than the proposed one

- The proposed order puts typed models before multi-tenancy and before the payload semantics are even correct.
- The router helper depends less on Pydantic itself than on having the right payload model.
- The pipeline skeleton depends on tenant-safe Qdrant naming and deletion behavior, so it should not come before Specs 1 and 2.

## Final Recommendation

Implement **Spec 5** and **Spec 1** next. Those are the best library-level investments: they solve real integration pain, preserve the current public API shape, and reduce service-repo hacks.

Then add **Spec 2** as additive infrastructure. After that, pause and redesign **Spec 4** and **Spec 6** before writing code. Only once the typed payload story is correct should you ship **Spec 3** as an optional FastAPI extra.

## Verification

This quick task was a codebase-grounded implementation review. Verification was manual inspection of:
- `corpulse/backends/postgres.py`
- `corpulse/backends/postgres_async.py`
- `corpulse/integrations/qdrant.py`
- `corpulse/async_core.py`
- `pyproject.toml`
- `README.md`
- `tests/test_postgres_backend.py`
- `tests/test_async_postgres_backend.py`
- `tests/test_qdrant_wrapper.py`
- `tests/test_async_core_integration.py`
