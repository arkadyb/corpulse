---
phase: 11-shared-report-helpers
plan: 03
type: execute
wave: 2
depends_on:
  - 11-02
files_modified:
  - corpulse/core.py
  - tests/test_report_helpers.py
autonomous: true
requirements:
  - REPORT-HELPERS-02
must_haves:
  truths:
    - "`Corpulse.to_dataframe()` delegates row assembly to `_build_dataframe_rows()` without changing its signature or pandas error behavior."
    - "`Corpulse.report()` and `Corpulse.cleanup_report()` format from shared payload helpers while preserving stdout byte-for-byte."
    - "Regression tests prove unchanged stdout, fallback formatting, and existing optional-dependency behavior."
  artifacts:
    - path: "corpulse/core.py"
      provides: "Sync methods wired through shared helpers"
      contains: "_build_report_summary("
    - path: "tests/test_report_helpers.py"
      provides: "Sync regression coverage after refactor"
      contains: "def test_report_stdout_unchanged"
    - path: "tests/test_report_helpers.py"
      provides: "Fallback and pandas guard coverage"
      contains: "def test_report_fallback_without_tabulate"
  key_links:
    - from: "corpulse/core.py::Corpulse.report"
      to: "corpulse.core._build_report_rows"
      via: "row payload generation"
      pattern: "_build_report_rows\\("
    - from: "corpulse/core.py::Corpulse.cleanup_report"
      to: "corpulse.core._build_cleanup_payload"
      via: "cleanup payload generation"
      pattern: "_build_cleanup_payload\\("
    - from: "tests/test_report_helpers.py::test_report_stdout_unchanged"
      to: "tests.test_report_helpers.EXPECTED_REPORT_OUTPUT"
      via: "snapshot comparison"
      pattern: "EXPECTED_REPORT_OUTPUT"
---

<objective>
Rewire the sync reporting surface to consume the shared helpers and prove that the public sync API stays backward-compatible. This is the final refactor step for Phase 11: the sync methods become thin formatters over shared structured payloads, with the baseline strings from Plan 01 guarding every output byte.

Purpose: Deliver REPORT-HELPERS-02 and close the phase with regression proof that sync behavior is unchanged.
Output: Refactored sync reporting methods in `corpulse/core.py` plus regression, fallback, and optional-dependency tests in `tests/test_report_helpers.py`.
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
@.planning/phases/11-shared-report-helpers/11-02-helper-extraction-PLAN.md
@corpulse/core.py
@tests/test_report_helpers.py

<interfaces>
Use these helper outputs as the formatter inputs:
```python
report_rows = _build_report_rows(...)
table_rows = [[r["filename"], r["retrievals"], r["engagement_rate"], r["status_display"]] for r in report_rows]

summary = _build_report_summary(all_docs, window_days, health)

payload = _build_cleanup_payload(
    health, ghosts, obsolete, stale, suspects, self.ghost_threshold_days
)
```

Preserve these public signatures exactly:
```python
def to_dataframe(self, window_days: int | None = None)
def report(self, window_days: int | None = None) -> None
def cleanup_report(self) -> None
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add regression tests for sync formatter parity, tabulate fallback, and pandas guard behavior</name>
  <files>tests/test_report_helpers.py</files>
  <read_first>
    - tests/test_report_helpers.py
    - corpulse/core.py
    - .planning/phases/11-shared-report-helpers/11-RESEARCH.md
    - .planning/phases/11-shared-report-helpers/11-VALIDATION.md
  </read_first>
  <acceptance_criteria>
    - `tests/test_report_helpers.py` defines `test_report_stdout_unchanged`, `test_cleanup_report_stdout_unchanged`, `test_to_dataframe_raises_without_pandas`, and `test_report_fallback_without_tabulate`.
    - `grep -q "pip install pandas to use to_dataframe()" tests/test_report_helpers.py` exits 0.
    - `grep -q "Run corpulse.cleanup_report() for a prioritised action list." tests/test_report_helpers.py` exits 0.
    - `pytest tests/test_report_helpers.py::test_report_stdout_unchanged tests/test_report_helpers.py::test_cleanup_report_stdout_unchanged tests/test_report_helpers.py::test_to_dataframe_raises_without_pandas tests/test_report_helpers.py::test_report_fallback_without_tabulate -x -q` exits 0.
  </acceptance_criteria>
  <behavior>
    - `test_report_stdout_unchanged` compares current `report(window_days=30)` stdout to `EXPECTED_REPORT_OUTPUT`.
    - `test_cleanup_report_stdout_unchanged` compares current `cleanup_report()` stdout to `EXPECTED_CLEANUP_OUTPUT`.
    - `test_to_dataframe_raises_without_pandas` monkeypatches the import path so `to_dataframe()` raises `RuntimeError("pip install pandas to use to_dataframe()")`.
    - `test_report_fallback_without_tabulate` forces the non-tabulate branch and asserts the plain-text header, status labels, and footer line are still present.
  </behavior>
  <action>
Extend `tests/test_report_helpers.py` with the four tests mapped to validation rows 11-03-01 through 11-03-04.

Implement the stdout regression tests using the same fixture and `capsys` approach as Plan 01, but after the refactor they become the permanent guardrails.

For `test_to_dataframe_raises_without_pandas`, patch the import mechanism for `pandas` so `Corpulse.to_dataframe()` hits the `except ImportError` branch and raises the exact message `pip install pandas to use to_dataframe()`.

For `test_report_fallback_without_tabulate`, patch the import mechanism for `tabulate` so `Corpulse.report(window_days=30)` takes the fallback branch. Assert the captured stdout contains all of these exact substrings:
- `Document`
- `Retrieved`
- `Engagement`
- `Status`
- `👻 ghosts:`
- `Run corpulse.cleanup_report() for a prioritised action list.`

Do not weaken the existing baseline constants. These tests must use the constants captured in Plan 01 rather than re-capturing output.
  </action>
  <verify>
    <automated>pytest tests/test_report_helpers.py::test_report_stdout_unchanged tests/test_report_helpers.py::test_cleanup_report_stdout_unchanged tests/test_report_helpers.py::test_to_dataframe_raises_without_pandas tests/test_report_helpers.py::test_report_fallback_without_tabulate -x -q</automated>
  </verify>
  <done>The regression, fallback, and pandas-guard tests exist and fail on output or exception drift rather than regenerating expectations.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Refactor sync methods to consume shared helpers without changing public behavior</name>
  <files>corpulse/core.py</files>
  <read_first>
    - corpulse/core.py
    - tests/test_report_helpers.py
    - .planning/phases/11-shared-report-helpers/11-RESEARCH.md
    - .planning/phases/11-shared-report-helpers/11-VALIDATION.md
  </read_first>
  <acceptance_criteria>
    - `rg -n "rows = _build_dataframe_rows\\(" corpulse/core.py` exits 0.
    - `rg -n "_build_report_rows\\(" corpulse/core.py` exits 0 inside `report()`.
    - `rg -n "_build_report_summary\\(" corpulse/core.py` exits 0 inside `report()`.
    - `rg -n "_build_cleanup_payload\\(" corpulse/core.py` exits 0 inside `cleanup_report()`.
    - `rg -n "def report\\(self, window_days: int \\| None = None\\) -> None:" corpulse/core.py` exits 0.
    - `rg -n "def cleanup_report\\(self\\) -> None:" corpulse/core.py` exits 0.
    - `pytest tests/test_report_helpers.py -q` exits 0.
    - `pytest tests/ -q` exits 0.
  </acceptance_criteria>
  <behavior>
    - `to_dataframe()` still raises the same pandas installation error and still returns `pd.DataFrame(rows).sort_values("retrievals", ascending=False)`.
    - `report()` still prints the same tabulate path and fallback path output as before the refactor.
    - `cleanup_report()` still prints the same headers, blank lines, section ordering, top-5 truncation, overflow lines, and trailing rule as before the refactor.
  </behavior>
  <action>
Refactor the three sync methods in `corpulse/core.py` so they delegate data assembly to the new helpers while preserving the current public signatures and stdout text exactly.

Make these concrete edits:
- in `to_dataframe()`, keep the `try: import pandas as pd` / `except ImportError: raise RuntimeError("pip install pandas to use to_dataframe()")` block unchanged, keep the backend reads unchanged, replace the inline row loop with `rows = _build_dataframe_rows(self.db.all_documents(), r_map, e_map, ghost_ids, obs, stale_ids)`, and keep the final return as `pd.DataFrame(rows).sort_values("retrievals", ascending=False)`
- in `report()`, keep the `tabulate` import guard, backend reads, and final `print()` structure, but replace the inline sorting/classification loop with `rows = _build_report_rows(all_docs, r_map, e_map, ghost_ids, obs, stale_ids, self.top_k_report)`, replace the inline `STATUS_ICON` dict with the shared `_STATUS_ICON`, compute `summary = _build_report_summary(all_docs, window_days or self.ghost_threshold_days, health)`, and build `table_rows = [[r["filename"], r["retrievals"], r["engagement_rate"], r["status_display"]] for r in rows]` before passing them to `tabulate` or the fallback formatter
- in `cleanup_report()`, keep all existing `print()` lines and spacing, but replace the inline slicing/count math with `payload = _build_cleanup_payload(health, ghosts, obsolete, stale, suspects, self.ghost_threshold_days)` and read all section values from that payload

Do not change:
- printed wording, punctuation, spacing, unicode glyphs, or blank lines
- the existing double-fetch behavior in `cleanup_report()`
- the optional dependency guards
- the method signatures

If a formatter line must change to read from a dict, keep the final rendered string identical to the pre-refactor output captured in Plan 01.
  </action>
  <verify>
    <automated>pytest tests/test_report_helpers.py -q && pytest tests/ -q</automated>
  </verify>
  <done>The sync reporting methods are thin formatters over shared helpers, the regression tests stay green, the public signatures remain unchanged, and the full suite passes.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| shared helper payloads -> sync stdout formatter | Structured data produced by the new helpers is rendered by the existing public sync methods; any drift here changes user-visible output and must be blocked. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-11-03-01 | Tampering | sync formatter output | mitigate | Keep the Plan 01 golden strings as immutable baselines and add explicit regression tests for both report surfaces. |
| T-11-03-02 | Repudiation | optional dependency behavior | mitigate | Add tests that force the pandas ImportError path and the tabulate fallback path, proving the public behavior remained unchanged after rewiring. |
| T-11-03-03 | DoS | full-suite regression surface | accept | The refactor keeps the same algorithmic complexity and reuses existing backend calls, including the known cleanup double-fetch pattern. |
</threat_model>

<verification>
1. `pytest tests/test_report_helpers.py -q`
2. `pytest tests/ -q`
</verification>

<success_criteria>
- `Corpulse.to_dataframe()`, `report()`, and `cleanup_report()` all delegate to shared helpers.
- Sync stdout remains byte-for-byte identical to the Wave 0 baselines.
- Fallback formatting and pandas error behavior remain covered and unchanged.
</success_criteria>

<output>
After completion, create `.planning/phases/11-shared-report-helpers/11-03-SUMMARY.md`.
</output>
