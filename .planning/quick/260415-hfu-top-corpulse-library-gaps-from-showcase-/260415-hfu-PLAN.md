---
type: quick-plan
mode: quick
autonomous: true
files_modified:
  - corpulse/integrations/qdrant.py
  - corpulse/core.py
  - corpulse/async_core.py
  - corpulse/backends/base.py
  - corpulse/backends/sqlite.py
  - corpulse/backends/memory.py
  - corpulse/backends/postgres.py
  - corpulse/backends/postgres_async.py
  - tests/test_qdrant_wrapper.py
  - tests/test_backend_contract.py
  - tests/test_core_backend_integration.py
  - tests/test_async_core_integration.py
  - tests/test_postgres_backend.py
  - tests/test_async_postgres_backend.py
must_haves:
  truths:
    - "AsyncQdrantCorpulseClient works with both sync Corpulse and AsyncCorpulse by awaiting coroutine-based log_retrieval methods and retaining the sync fallback."
    - "Corpulse exposes a public delete_document API in both sync and async forms, backed by every supported storage backend."
    - "Deleting a document removes its related retrieval and engagement history so consumers no longer need raw SQL against internal tables."
    - "Targeted regression tests cover the showcase-discovered async Qdrant failure mode and backend delete parity."
  artifacts:
    - path: "corpulse/integrations/qdrant.py"
      provides: "Async wrapper compatibility for async and sync Corpulse retrieval logging"
    - path: "corpulse/core.py"
      provides: "Public sync delete_document API"
    - path: "corpulse/async_core.py"
      provides: "Public async delete_document API"
    - path: "corpulse/backends/base.py"
      provides: "Shared storage delete_document contract"
    - path: "corpulse/backends/sqlite.py"
      provides: "SQLite delete implementation"
    - path: "corpulse/backends/memory.py"
      provides: "In-memory delete implementation"
    - path: "corpulse/backends/postgres.py"
      provides: "Sync Postgres delete implementation"
    - path: "corpulse/backends/postgres_async.py"
      provides: "Async Postgres delete implementation"
    - path: "tests/test_qdrant_wrapper.py"
      provides: "Async wrapper regression coverage for coroutine-based retrieval logging"
  key_links:
    - from: "corpulse/integrations/qdrant.py"
      to: "corpulse/async_core.py"
      via: "Async wrapper now recognizes and awaits AsyncCorpulse.log_retrieval"
    - from: "corpulse/core.py"
      to: "corpulse/backends/base.py"
      via: "New public delete method delegates through the shared storage contract"
    - from: "tests/test_backend_contract.py"
      to: "corpulse/backends/sqlite.py"
      via: "Contract parity now includes delete behavior across backends"
---

<objective>
Ship the two immediate showcase-driven library gaps:
1. Fix `AsyncQdrantCorpulseClient.search()` so it works with `AsyncCorpulse` instead of forcing callers to bypass the wrapper.
2. Add a public `delete_document` API so consumers can remove a document and its related history without issuing raw SQL.

Purpose: close the smallest, highest-leverage integration gaps in the core library before tackling larger SaaS-oriented multi-tenancy work.
Output: one library patch set covering async Qdrant logging compatibility, public delete APIs across sync/async corpulse and backends, and regression tests for both areas.
</objective>

<context>
@.planning/STATE.md
@.planning/phases/AUDIT.md
@corpulse/integrations/qdrant.py
@corpulse/core.py
@corpulse/async_core.py
@corpulse/backends/base.py
@corpulse/backends/sqlite.py
@corpulse/backends/memory.py
@corpulse/backends/postgres.py
@corpulse/backends/postgres_async.py
@tests/test_qdrant_wrapper.py
@tests/test_backend_contract.py
@tests/test_core_backend_integration.py
@tests/test_async_core_integration.py
@tests/test_postgres_backend.py
@tests/test_async_postgres_backend.py

<constraints>
- Keep scope to audit items #1 and #3 only.
- Preserve existing sync wrapper behavior for users passing a sync `Corpulse` into the async Qdrant wrapper.
- Make delete semantics consistent across all supported backends instead of adding a Postgres-only escape hatch.
- Do not touch multi-tenancy, FastAPI helpers, or indexing pipeline APIs in this quick task.
</constraints>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Fix async Qdrant retrieval logging compatibility</name>
  <files>corpulse/integrations/qdrant.py, tests/test_qdrant_wrapper.py</files>
  <behavior>
    - Async wrapper methods continue to work for sync `Corpulse` instances by running sync logging off-thread.
    - Async wrapper methods correctly await coroutine-based `log_retrieval` implementations such as `AsyncCorpulse`.
    - Search-path regression coverage proves the showcase failure mode is fixed.
  </behavior>
  <action>Update `AsyncQdrantCorpulseClient` to detect whether `corpulse.log_retrieval` is coroutine-based and either await it directly or fall back to the existing `asyncio.to_thread(...)` path for sync instances. Add a focused async wrapper test that exercises `search()` with an async `log_retrieval` consumer.</action>
  <verify>
    <automated>pytest tests/test_qdrant_wrapper.py -q</automated>
  </verify>
  <done>The async Qdrant wrapper no longer breaks when paired with `AsyncCorpulse`, and sync compatibility is preserved.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add public delete_document API through the storage contract</name>
  <files>corpulse/core.py, corpulse/async_core.py, corpulse/backends/base.py, corpulse/backends/sqlite.py, corpulse/backends/memory.py, corpulse/backends/postgres.py, corpulse/backends/postgres_async.py, tests/test_backend_contract.py, tests/test_core_backend_integration.py, tests/test_async_core_integration.py, tests/test_postgres_backend.py, tests/test_async_postgres_backend.py</files>
  <behavior>
    - Sync and async corpulse instances expose `delete_document(doc_id)` as a public API.
    - Each backend removes the document row and dependent retrieval and engagement rows without raising on missing documents.
    - Contract and integration tests prove parity for delete behavior across supported backends.
  </behavior>
  <action>Extend the storage backend contract with `delete_document`, implement it for SQLite, in-memory, sync Postgres, and async Postgres, then surface public sync and async corpulse methods that delegate directly to the backend. Add regression tests for contract parity, public API delegation, and Postgres SQL sequencing.</action>
  <verify>
    <automated>pytest tests/test_backend_contract.py tests/test_core_backend_integration.py tests/test_async_core_integration.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py -q</automated>
  </verify>
  <done>Consumers can delete documents through the public library API without relying on internal tables or backend-specific SQL.</done>
</task>

</tasks>

<verification>
Run `pytest tests/test_backend_contract.py tests/test_core_backend_integration.py tests/test_async_core_integration.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_qdrant_wrapper.py -q` and confirm the changed surfaces pass, with only existing environment-gated live Postgres tests skipped.
</verification>

<success_criteria>
- `AsyncQdrantCorpulseClient.search()` and `query_points()` support async retrieval logging consumers without regressing sync usage.
- `Corpulse` and `AsyncCorpulse` expose public `delete_document` methods.
- The shared backend contract and all concrete backends implement delete semantics consistently.
- Targeted tests pass locally for the affected library surfaces.
</success_criteria>
