---
phase: 11-shared-report-helpers
plan: 02
type: execute
wave: 1
depends_on:
  - 11-01
files_modified:
  - corpulse/core.py
  - tests/test_report_helpers.py
autonomous: true
requirements:
  - REPORT-HELPERS-01
must_haves:
  truths:
    - "`corpulse/core.py` exposes pure helper functions for dataframe rows, report rows, report summary, and cleanup payload assembly."
    - "The helper tests verify the exact payload shapes and preserve the known rounded-vs-unrounded low-engagement divergence."
    - "The sync reporting methods can consume the extracted payload shapes without introducing new formatting logic in this plan."
  artifacts:
    - path: "corpulse/core.py"
      provides: "Shared pure payload builders for sync and async report surfaces"
      contains: "def _build_dataframe_rows("
    - path: "corpulse/core.py"
      provides: "Shared report row/status formatter data"
      contains: "def _build_report_rows("
    - path: "corpulse/core.py"
      provides: "Shared cleanup payload builder"
      contains: "def _build_cleanup_payload("
    - path: "tests/test_report_helpers.py"
      provides: "Unit coverage for all four helpers"
      contains: "def test_build_cleanup_payload"
  key_links:
    - from: "tests/test_report_helpers.py::test_build_dataframe_rows"
      to: "corpulse.core._build_dataframe_rows"
      via: "direct helper import"
      pattern: "_build_dataframe_rows"
    - from: "tests/test_report_helpers.py::test_build_report_rows"
      to: "corpulse.core._build_report_rows"
      via: "direct helper import"
      pattern: "_build_report_rows"
    - from: "tests/test_report_helpers.py::test_build_cleanup_payload"
      to: "corpulse.core._build_cleanup_payload"
      via: "direct helper import"
      pattern: "_build_cleanup_payload"
---

<objective>
Extract the shared report payload builders into `corpulse/core.py` and lock them down with focused unit tests before the sync methods are rewired. This plan creates the reusable contracts that Phase 12 will depend on, while keeping formatter behavior validation in the later plan.

Purpose: Deliver REPORT-HELPERS-01 with concrete, testable helper contracts and no ambiguity for the Phase 12 async consumer.
Output: Four new private helpers in `corpulse/core.py`, `_STATUS_ICON` at module scope, and helper-specific tests in `tests/test_report_helpers.py`.
</objective>

<execution_context>
@/Users/arkady/.codex/get-shit-done/workflows/execute-plan.md
@/Users/arkady/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/11-shared-report-helpers/11-RESEARCH.md
@.planning/phases/11-shared-report-helpers/11-VALIDATION.md
@.planning/phases/11-shared-report-helpers/11-01-characterization-tests-PLAN.md
@corpulse/core.py
@corpulse/async_core.py
@tests/test_report_helpers.py

<interfaces>
Create these exact helper signatures in `corpulse/core.py`:
```python
def _build_dataframe_rows(
    all_docs: list[dict[str, Any]],
    r_map: dict[str, dict[str, Any]],
    e_map: dict[str, int],
    ghost_ids: set[str],
    obsolete_ids: set[str],
    stale_ids: set[str],
) -> list[dict[str, Any]]: ...

def _build_report_rows(
    all_docs: list[dict[str, Any]],
    r_map: dict[str, dict[str, Any]],
    e_map: dict[str, int],
    ghost_ids: set[str],
    obsolete_ids: set[str],
    stale_ids: set[str],
    top_k: int,
) -> list[dict[str, Any]]: ...

def _build_report_summary(
    all_docs: list[dict[str, Any]],
    window_days: int,
    health: dict[str, Any],
) -> dict[str, Any]: ...

def _build_cleanup_payload(
    health: dict[str, Any],
    ghosts: list[dict[str, Any]],
    obsolete: list[dict[str, Any]],
    stale: list[dict[str, Any]],
    suspects: list[dict[str, Any]],
    ghost_threshold_days: int,
) -> dict[str, Any]: ...
```

Use the module-level constant:
```python
_STATUS_ICON = {
    "ghost": "👻 ghost",
    "obsolete": "⚠  obsolete",
    "stale": "🕓 stale emb.",
    "low_engagement": "◌  low eng.",
    "healthy": "✓  healthy",
}
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add focused unit tests for the shared report helper contracts</name>
  <files>tests/test_report_helpers.py</files>
  <read_first>
    - tests/test_report_helpers.py
    - corpulse/core.py
    - corpulse/async_core.py
    - .planning/phases/11-shared-report-helpers/11-RESEARCH.md
    - .planning/phases/11-shared-report-helpers/11-VALIDATION.md
  </read_first>
  <acceptance_criteria>
    - `tests/test_report_helpers.py` imports `_build_dataframe_rows`, `_build_report_rows`, `_build_report_summary`, and `_build_cleanup_payload`.
    - `tests/test_report_helpers.py` defines `test_build_dataframe_rows`, `test_build_report_rows`, `test_build_report_summary`, and `test_build_cleanup_payload`.
    - `grep -q "status_display" tests/test_report_helpers.py` exits 0.
    - `grep -q "low_engagement" tests/test_report_helpers.py` exits 0.
    - `pytest tests/test_report_helpers.py::test_build_dataframe_rows tests/test_report_helpers.py::test_build_report_rows tests/test_report_helpers.py::test_build_report_summary tests/test_report_helpers.py::test_build_cleanup_payload -x -q` exits 0.
  </acceptance_criteria>
  <behavior>
    - `test_build_dataframe_rows` asserts helper rows include `doc_id`, `filename`, `retrievals`, `engagements`, `engagement_rate`, and `status`, and that the low-engagement check uses the rounded `rate < 0.15` behavior from `to_dataframe()`.
    - `test_build_report_rows` asserts rows are sorted by retrieval count descending, trimmed to `top_k`, include `status_display`, and preserve the unrounded `(eng / ret) < 0.15` low-engagement behavior from `report()`.
    - `test_build_report_summary` asserts the summary dict contains `total_docs`, `window_days`, `bloat_warning`, `noise_pct`, `ghosts`, `obsolete`, `duplicates`, `stale`, and `recommendation`.
    - `test_build_cleanup_payload` asserts each section dict has `count`, `top5`, and `overflow`, including zero-count sections with empty lists and overflow `0`.
  </behavior>
  <action>
Extend `tests/test_report_helpers.py` with four direct helper tests mapped to validation rows 11-02-01 through 11-02-04.

Import the helpers directly from `corpulse.core`. Reuse `_report_fixture_backend()` to derive `all_docs`, `r_map`, `e_map`, `ghost_ids`, `obsolete_ids`, `stale_ids`, `health`, `ghosts`, `obsolete`, `stale`, and `suspects` through the existing sync `Corpulse` analysis methods, then pass those pre-fetched values into the helper functions. Do not call the helper functions with a backend object.

Make the assertions concrete:
- dataframe rows must have exactly the keys `doc_id`, `filename`, `retrievals`, `engagements`, `engagement_rate`, `status`
- report rows must have exactly the keys `filename`, `retrievals`, `engagement_rate`, `status`, `status_display`
- report rows must include `_STATUS_ICON` values such as `👻 ghost` and `◌  low eng.`
- cleanup payload must include top-level keys `total_docs`, `noise_pct`, `bloat_warning`, `recommendation`, `ghost_threshold_days`, `ghosts`, `obsolete`, `stale`, `suspects`
- each section dict must include `count`, `top5`, and `overflow`

Add one explicit boundary assertion proving the helpers preserve the pre-existing divergence: create a synthetic one-document input with `ret = 20` and `eng = 3`, so the rounded dataframe rate is `0.15` but the raw report ratio is `0.149999...`; assert `_build_dataframe_rows(...)[0]["status"] != "low_engagement"` while `_build_report_rows(..., top_k=1)[0]["status"] == "low_engagement"`.
  </action>
  <verify>
    <automated>pytest tests/test_report_helpers.py::test_build_dataframe_rows tests/test_report_helpers.py::test_build_report_rows tests/test_report_helpers.py::test_build_report_summary tests/test_report_helpers.py::test_build_cleanup_payload -x -q</automated>
  </verify>
  <done>The helper contract tests exist and pass, including the explicit assertion for the rounded-vs-unrounded low-engagement divergence.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement the shared helper builders and module-level status icon constant in core.py</name>
  <files>corpulse/core.py</files>
  <read_first>
    - corpulse/core.py
    - tests/test_report_helpers.py
    - corpulse/async_core.py
    - .planning/phases/11-shared-report-helpers/11-RESEARCH.md
  </read_first>
  <acceptance_criteria>
    - `grep -q "^_STATUS_ICON = {" corpulse/core.py` exits 0.
    - `grep -q "^def _build_dataframe_rows(" corpulse/core.py` exits 0.
    - `grep -q "^def _build_report_rows(" corpulse/core.py` exits 0.
    - `grep -q "^def _build_report_summary(" corpulse/core.py` exits 0.
    - `grep -q "^def _build_cleanup_payload(" corpulse/core.py` exits 0.
    - `grep -q 'status_display' corpulse/core.py` exits 0.
    - `pytest tests/test_report_helpers.py::test_build_dataframe_rows tests/test_report_helpers.py::test_build_report_rows tests/test_report_helpers.py::test_build_report_summary tests/test_report_helpers.py::test_build_cleanup_payload -x -q` exits 0.
  </acceptance_criteria>
  <behavior>
    - The new helper functions are pure: they accept already-fetched inputs and return dict/list payloads without printing, importing optional dependencies, or calling backend methods.
    - `_build_dataframe_rows` preserves the rounded `rate < 0.15` condition used by the current dataframe path.
    - `_build_report_rows` preserves the unrounded `(e_map.get(did, 0) / ret) < 0.15` condition, stable retrieval-count sorting, and `top_k` trimming used by the current report path.
    - `_build_cleanup_payload` always returns all four section dicts, even when some counts are zero.
  </behavior>
  <action>
Modify `corpulse/core.py` near the existing helper section.

Add the module-level `_STATUS_ICON` constant with exactly these mappings:
`ghost -> "👻 ghost"`, `obsolete -> "⚠  obsolete"`, `stale -> "🕓 stale emb."`, `low_engagement -> "◌  low eng."`, `healthy -> "✓  healthy"`.

Implement the four helper functions exactly as specified in `11-RESEARCH.md`:
- `_build_dataframe_rows(...)` returns unsorted row dicts with float `engagement_rate`
- `_build_report_rows(...)` returns rows already sorted by retrieval count descending and trimmed to `top_k`, with string `engagement_rate` values like `"50%"` or `"—"` and a `status_display` key populated from `_STATUS_ICON`
- `_build_report_summary(...)` returns the summary dict with `noise_pct = health["noise_estimate"] * 100`
- `_build_cleanup_payload(...)` returns the top-level metadata plus section dicts where `top5` is `items[:5]` and `overflow` is `max(0, len(items) - 5)`

Keep the functions pure. Do not call `self`, `self.db`, `tabulate`, `pandas`, `print`, or any backend method from inside these helpers.

Do not refactor `Corpulse.to_dataframe()`, `Corpulse.report()`, or `Corpulse.cleanup_report()` yet in this plan beyond adding helper definitions and constants. The sync method rewiring belongs to Plan 03.
  </action>
  <verify>
    <automated>pytest tests/test_report_helpers.py::test_build_dataframe_rows tests/test_report_helpers.py::test_build_report_rows tests/test_report_helpers.py::test_build_report_summary tests/test_report_helpers.py::test_build_cleanup_payload -x -q</automated>
  </verify>
  <done>`corpulse/core.py` contains the four helper builders plus `_STATUS_ICON`, all helper tests pass, and the helpers expose the exact payload shapes that Phase 12 will reuse.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| sync method internals -> shared helper layer | Existing in-process analytics data is transformed into structured payloads that later sync and async callers will consume. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-11-02-01 | Tampering | helper status classification logic | mitigate | Add direct unit tests for both helper paths and explicitly assert the rounded-vs-unrounded threshold divergence so the refactor cannot silently normalize behavior. |
| T-11-02-02 | Repudiation | helper payload contract | mitigate | Pin exact key names and payload shapes in tests for all four helpers, making later drift grep- and pytest-detectable. |
| T-11-02-03 | DoS | helper implementation | accept | Helpers operate on already-fetched in-memory lists and dicts; no new loops beyond the existing reporting work are introduced. |
</threat_model>

<verification>
1. `pytest tests/test_report_helpers.py::test_build_dataframe_rows tests/test_report_helpers.py::test_build_report_rows tests/test_report_helpers.py::test_build_report_summary tests/test_report_helpers.py::test_build_cleanup_payload -x -q`
2. `pytest tests/test_report_helpers.py -q`
</verification>

<success_criteria>
- `corpulse/core.py` exports the four new private helper functions and `_STATUS_ICON`.
- `tests/test_report_helpers.py` contains passing helper-focused unit tests.
- The shared payload contracts are ready for both sync formatter rewiring and later async reuse.
</success_criteria>

<output>
After completion, create `.planning/phases/11-shared-report-helpers/11-02-SUMMARY.md`.
</output>
