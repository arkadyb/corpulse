---
phase: 11-shared-report-helpers
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/test_report_helpers.py
autonomous: true
requirements:
  - REPORT-HELPERS-01
  - REPORT-HELPERS-02
must_haves:
  truths:
    - "A deterministic in-memory fixture exists that exercises ghosts, obsolete docs, stale embeddings, low-engagement suspects, and healthy docs in one corpus."
    - "The pre-refactor stdout of `Corpulse.report(window_days=30)` is pinned as `EXPECTED_REPORT_OUTPUT`."
    - "The pre-refactor stdout of `Corpulse.cleanup_report()` is pinned as `EXPECTED_CLEANUP_OUTPUT`."
    - "The characterization tests pass against unmodified `corpulse/core.py`, proving the golden strings were captured before the refactor."
  artifacts:
    - path: "tests/test_report_helpers.py"
      provides: "Deterministic fixture and golden-string regression tests for report helpers"
      contains: "_report_fixture_backend"
    - path: "tests/test_report_helpers.py"
      provides: "Pinned report baseline"
      contains: "EXPECTED_REPORT_OUTPUT"
    - path: "tests/test_report_helpers.py"
      provides: "Pinned cleanup baseline"
      contains: "EXPECTED_CLEANUP_OUTPUT"
  key_links:
    - from: "tests/test_report_helpers.py::test_baseline_capture_report_output"
      to: "corpulse.core.Corpulse.report"
      via: "capsys stdout capture"
      pattern: "capsys\\.readouterr\\(\\)\\.out"
    - from: "tests/test_report_helpers.py::test_baseline_capture_cleanup_output"
      to: "corpulse.core.Corpulse.cleanup_report"
      via: "capsys stdout capture"
      pattern: "capsys\\.readouterr\\(\\)\\.out"
---

<objective>
Create the Wave 0 safety net before `corpulse/core.py` changes. This plan adds the deterministic fixture and captures the current sync stdout exactly once so the later helper extraction and formatter refactor can prove byte-for-byte compatibility instead of asserting against freshly generated output.

Purpose: Satisfy the validation contract in `11-VALIDATION.md` and make REPORT-HELPERS-02 objectively testable.
Output: `tests/test_report_helpers.py` with fixture helpers, pinned output constants, and baseline snapshot tests.
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
@corpulse/core.py
@corpulse/backends/memory.py
@tests/test_analytics.py

<interfaces>
From corpulse/core.py:
```python
class Corpulse:
    def report(self, window_days: int | None = None) -> None: ...
    def cleanup_report(self) -> None: ...
```

From corpulse/backends/memory.py:
```python
class InMemoryBackend:
    def upsert_document(self, doc_id: str, filename: str, embedding=None, embedded_at=None) -> None: ...
    def insert_retrieval(self, doc_id: str, qhash: str, rank: int, score: float, ts: float) -> None: ...
    def insert_engagement(self, doc_id: str, event: str, ts: float) -> None: ...
    def update_source_timestamp(self, doc_id: str, updated_at: float) -> None: ...
```
`tests/test_analytics.py` already uses `monkeypatch.setattr(c_mod, "_now", lambda: FROZEN)` for deterministic time control.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create the deterministic fixture and pin both pre-refactor stdout baselines</name>
  <files>tests/test_report_helpers.py</files>
  <read_first>
    - tests/test_report_helpers.py
    - corpulse/core.py
    - corpulse/backends/memory.py
    - tests/test_analytics.py
    - .planning/phases/11-shared-report-helpers/11-RESEARCH.md
    - .planning/phases/11-shared-report-helpers/11-VALIDATION.md
  </read_first>
  <acceptance_criteria>
    - `tests/test_report_helpers.py` defines `FROZEN = 1_700_000_000.0`.
    - `tests/test_report_helpers.py` defines `_report_fixture_backend()`, `EXPECTED_REPORT_OUTPUT =`, and `EXPECTED_CLEANUP_OUTPUT =`.
    - `tests/test_report_helpers.py` contains `def test_baseline_capture_report_output` and `def test_baseline_capture_cleanup_output`.
    - `grep -q "corpulse — Corpus Health Report" tests/test_report_helpers.py` exits 0.
    - `grep -q "corpulse — Cleanup Report" tests/test_report_helpers.py` exits 0.
    - `! grep -q "PASTE CAPTURED STRING HERE" tests/test_report_helpers.py` exits 0.
    - `pytest tests/test_report_helpers.py::test_baseline_capture_report_output tests/test_report_helpers.py::test_baseline_capture_cleanup_output -x -q` exits 0.
    - `git diff --quiet -- corpulse/core.py` exits 0 after the task completes.
  </acceptance_criteria>
  <behavior>
    - `test_baseline_capture_report_output` fails if `Corpulse.report(window_days=30)` stdout differs by a single byte from `EXPECTED_REPORT_OUTPUT`.
    - `test_baseline_capture_cleanup_output` fails if `Corpulse.cleanup_report()` stdout differs by a single byte from `EXPECTED_CLEANUP_OUTPUT`.
    - The fixture includes at least 8 documents spanning ghosts, obsolete docs, stale embeddings, suspects, and healthy docs so every formatter branch is exercised.
  </behavior>
  <action>
Create `tests/test_report_helpers.py` as the Wave 0 characterization module for Phase 11. Use these exact names because the validation file references them directly: `FROZEN`, `_report_fixture_backend`, `EXPECTED_REPORT_OUTPUT`, `EXPECTED_CLEANUP_OUTPUT`, `test_baseline_capture_report_output`, and `test_baseline_capture_cleanup_output`.

Populate `_report_fixture_backend()` with an `InMemoryBackend` and deterministic documents that cover every category:
- ghosts: `ghost-a` / `ghost_a.md` and `ghost-b` / `ghost_b.md` with no recent retrievals
- obsolete pair 1: `api-v1` / `api-v1.md` superseded by `api-v2` / `api-v2.md`
- obsolete pair 2: `guide-v1` / `guide-v1.md` superseded by `guide-v2` / `guide-v2.md`
- stale doc: `stale-doc` / `stale.md` with `embedded_at = FROZEN - 50 * 86400` and `source_updated_at = FROZEN - 10 * 86400`
- suspect doc: `noisy-doc` / `noisy.md` with exactly 10 retrievals and 1 engagement inside the 30-day window
- healthy docs: `healthy-a` / `healthy_a.md` and `healthy-b` / `healthy_b.md` with retrievals and engagement rates above the low-engagement threshold

Freeze time with a pytest fixture that applies `monkeypatch.setattr(corpulse.core, "_now", lambda: FROZEN)`.

Write the file with placeholder constants first, then capture the actual strings from the unmodified code path using Python one-liners that import `_report_fixture_backend`, instantiate `Corpulse(backend=_report_fixture_backend())`, redirect `sys.stdout` to `io.StringIO()`, and print `repr(buf.getvalue())`. Replace the placeholders with those literal captured strings before running pytest.

Do not modify `corpulse/core.py` in this plan. If the tests fail, fix the fixture data or the captured constants rather than changing the implementation under test.
  </action>
  <verify>
    <automated>pytest tests/test_report_helpers.py::test_baseline_capture_report_output tests/test_report_helpers.py::test_baseline_capture_cleanup_output -x -q</automated>
  </verify>
  <done>`tests/test_report_helpers.py` exists, both expected-output constants are populated from real captures, both baseline snapshot tests pass, and `corpulse/core.py` remains unchanged.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test fixture -> sync stdout surface | Synthetic in-memory data crosses into the existing report formatter; the only observable output is captured stdout used for regression locking. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-11-01-01 | Tampering | `tests/test_report_helpers.py` golden constants | mitigate | Use captured literal strings from pre-refactor `corpulse/core.py` and keep `corpulse/core.py` unchanged in this plan; failing snapshot tests expose any accidental edits immediately. |
| T-11-01-02 | Information Disclosure | snapshot constants | accept | The constants contain only synthetic fixture filenames and counts; no production data or secrets are introduced. |
| T-11-01-03 | DoS | pytest command surface | accept | The task runs only local deterministic unit tests with an in-memory backend; runtime is bounded and no external service is contacted. |
</threat_model>

<verification>
1. `pytest tests/test_report_helpers.py -q`
2. `pytest tests/ -q`
3. `git diff --quiet -- corpulse/core.py`
</verification>

<success_criteria>
- Wave 0 baseline capture is complete before any refactor touches `corpulse/core.py`.
- The new test module contains deterministic fixture data plus both expected stdout constants.
- The characterization tests are green against the current implementation.
</success_criteria>

<output>
After completion, create `.planning/phases/11-shared-report-helpers/11-01-SUMMARY.md`.
</output>
