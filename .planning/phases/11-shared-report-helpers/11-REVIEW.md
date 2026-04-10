---
phase: 11-shared-report-helpers
reviewed: 2026-04-10T07:45:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - corpulse/core.py
  - tests/test_report_helpers.py
  - .planning/phases/11-shared-report-helpers/11-01-SUMMARY.md
  - .planning/phases/11-shared-report-helpers/11-02-SUMMARY.md
  - .planning/phases/11-shared-report-helpers/11-03-SUMMARY.md
  - .planning/phases/11-shared-report-helpers/11-VALIDATION.md
findings:
  critical: 0
  warning: 2
  info: 0
  total: 2
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-04-10T07:45:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the Phase 11 helper extraction and sync formatter rewiring in `corpulse/core.py`, plus the dedicated regression suite in `tests/test_report_helpers.py`, using the phase summaries for intent. I did not find a direct behavioral regression or security issue in the implementation itself, and `pytest -q tests/test_report_helpers.py` passes locally. The main gaps are missing public-API regression coverage for `to_dataframe()` and incomplete coverage of the `tabulate`-installed report branch.

## Warnings

### WR-01: No happy-path regression test for public `to_dataframe()`

**File:** `tests/test_report_helpers.py:207-219`
**Issue:** Phase 11 rewired [`corpulse/core.py`](/Users/arkady/src/corpulse/corpulse/core.py#L647) `to_dataframe()` through `_build_dataframe_rows()`, but the test suite only covers the missing-`pandas` error path and the private helper contract. That leaves the public method's DataFrame-specific behavior unpinned: column order, descending sort by `retrievals`, and the final values returned through pandas could drift without a failing test.
**Fix:**
```python
def test_to_dataframe_happy_path():
    corpulse = Corpulse(backend=_report_fixture_backend())

    df = corpulse.to_dataframe(window_days=30)

    assert list(df.columns) == [
        "doc_id", "filename", "retrievals", "engagements", "engagement_rate", "status",
    ]
    assert df.iloc[0]["filename"] == "noisy.md"
    assert list(df["retrievals"].head(4)) == [10, 8, 7, 6]
```

### WR-02: The `tabulate` branch is not regression-tested in an environment where `tabulate` exists

**File:** `tests/test_report_helpers.py:191-241`
**Issue:** [`corpulse/core.py`](/Users/arkady/src/corpulse/corpulse/core.py#L755) still has two output branches in `report()`: `tabulate` and plain-text fallback. The current suite snapshot-tests only the branch exercised by the local environment, then separately forces the fallback branch and checks only a few substrings. Because the phase refactor changed the data fed into `tabulate()` via `table_rows`, a formatting or ordering regression in the optional-dependency branch could ship unnoticed on systems that have `tabulate` installed.
**Fix:**
```python
def test_report_with_tabulate_installed(monkeypatch, capsys):
    corpulse = Corpulse(backend=_report_fixture_backend())

    def _fake_tabulate(rows, headers, tablefmt):
        assert rows[0] == ["noisy.md", 10, "10%", "◌  low eng."]
        assert headers == ["Document", "Retrieved", "Engagement", "Status"]
        assert tablefmt == "rounded_outline"
        return "<tabulated>"

    monkeypatch.setitem(sys.modules, "tabulate", SimpleNamespace(tabulate=_fake_tabulate))
    corpulse.report(window_days=30)

    assert "<tabulated>" in capsys.readouterr().out
```

---

_Reviewed: 2026-04-10T07:45:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
