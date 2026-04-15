# Phase 11: Shared Report Helpers — Research

**Researched:** 2026-04-10
**Domain:** Python internal refactor — extract structured-payload builders from `Corpulse.report()` / `cleanup_report()` / `to_dataframe()` and rewire sync methods through a thin formatter
**Confidence:** HIGH (all findings derived from direct codebase inspection)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REPORT-HELPERS-01 | Structured-payload builder helpers for `to_dataframe` rows and cleanup-report sections factored into `corpulse/core.py` so sync and async paths compute the same output from the same code path. | Helpers `_build_report_rows`, `_build_report_summary`, `_build_cleanup_payload`, `_build_dataframe_rows` designed below; they accept pre-fetched data rows and return pure dicts/lists with no I/O. |
| REPORT-HELPERS-02 | Sync `Corpulse.report()` and `Corpulse.cleanup_report()` refactored to consume the shared structured payloads via a thin stdout formatter; printed output and public signatures remain unchanged. | Split between data-assembly helpers (to move) and stdout formatter (to stay in method) is fully mapped in "Sync Refactor Strategy" section. |
</phase_requirements>

---

## Phase Understanding

Phase 11 is a pure internal refactor of `corpulse/core.py`. No new user-facing behaviour is added. The sync public API (`Corpulse.report()`, `Corpulse.cleanup_report()`, `Corpulse.to_dataframe()`) keeps the same signatures and the same printed/returned output. The only observable change from outside the class is that new private module-level helper functions appear — which Phase 12 will import and call from `AsyncCorpulse`.

The design constraint is tight: "byte-for-byte identical stdout" means every print statement, space, Unicode character, and `%`-format must survive the split. This drives the split point: all formatting logic stays inside the sync methods; all data-assembly logic moves into helpers.

The pattern was already proven by quick task `260410-mf8`, which extracted `_build_ghosts`, `_build_duplicate_pairs`, `_build_obsolete_documents`, `_build_stale_embeddings`, `_build_suspects`, and `_build_corpus_health` from `Corpulse` analysis methods. Phase 11 applies the same technique to the reporting surface.

---

## Existing Code Map

### `Corpulse.to_dataframe()` (lines 510-559) [VERIFIED: codebase]

**What it currently does:**

1. Imports `pandas` or raises `RuntimeError("pip install pandas to use to_dataframe()")`.
2. Computes `since` from `window_days or self.ghost_threshold_days`.
3. Fetches: `db.retrieval_counts(since)`, `db.engagement_counts(since)`, `get_ghosts()`, `get_obsolete()`, `get_stale_embeddings()`, `db.all_documents()`.
4. Iterates `all_documents()` — for each doc: computes `ret`, `eng`, `rate`, and classifies `status` via if/elif chain.
5. Appends dict with keys: `doc_id`, `filename`, `retrievals`, `engagements`, `engagement_rate`, `status`.
6. Returns `pd.DataFrame(rows).sort_values("retrievals", ascending=False)`.

**Status classification logic:**
```python
if did in ghosts:   status = "ghost"
elif did in obs:    status = "obsolete"
elif did in stale:  status = "stale"
elif ret > 0 and rate < 0.15: status = "low_engagement"
else:               status = "healthy"
```
Note: `rate` here is `round(eng / ret, 2)` — computed **before** the classification check. This `rate < 0.15` uses the rounded value.

### `Corpulse.report()` (lines 624-702) [VERIFIED: codebase]

**What it currently does:**

1. Tries `from tabulate import tabulate`; sets `_tabulate = True/False`.
2. Computes `since`; fetches `all_documents()`, `retrieval_counts()`, `engagement_counts()`, `get_ghosts()`, `get_obsolete()`, `get_stale_embeddings()`.
3. Defines `STATUS_ICON` dict (maps status key to display string with emoji).
4. Iterates `all_docs` sorted by `retrieval_count desc`, trimmed to `top_k_report`:
   - Computes `ret`, `eng`, `rate` (formatted as `"{eng/ret*100:.0f}%"` or `"—"` — a string, NOT a float).
   - Classifies status using same if/elif chain.
   - Appends list `[doc["filename"], ret, rate, STATUS_ICON[status]]` — note `rate` is already the **formatted string**.
5. Calls `corpus_health()`.
6. Builds `header` string; adds bloat warning if `health["bloat_warning"]`.
7. Prints: header, table (tabulate or fallback loop), footer with counts.

**Critical distinction from `to_dataframe`:** In `report()`, the `rate` value is a display string (`"42%"` or `"—"`) placed into the row list. In `to_dataframe()`, it is a float. The helpers must keep these separate.

**Status classification in `report()` — subtle difference:**
```python
elif ret > 0 and (e_map.get(did, 0) / ret) < 0.15:
    status = "low_engagement"
```
This recalculates `e_map.get(did, 0) / ret` — it does NOT use the rounded `rate` variable. This is an unrounded check. The `to_dataframe()` path uses `rate < 0.15` where `rate = round(eng/ret, 2)`. These can disagree at boundary values (e.g. `eng/ret = 0.149...` rounds to `0.15`, fails `< 0.15` in dataframe but passes in report). **This is a pre-existing behavioural inconsistency in the current code.** Phase 11 must preserve it exactly — do not fix it silently.

### `Corpulse.cleanup_report()` (lines 561-622) [VERIFIED: codebase]

**What it currently does:**

1. Calls `corpus_health()`, `get_ghosts()`, `get_obsolete()`, `get_stale_embeddings()`, `get_suspects()`.
2. Prints header block (60-char rule, title, total docs, noise estimate, optional bloat warning).
3. If `ghosts`: prints count with `ghost_threshold_days`, top-5 filenames, "… and N more" if truncated.
4. If `obsolete`: prints count, top-5 with `→  superseded by` text, overflow line.
5. If `stale`: prints count, top-5 with `days_behind`, `source_updated`, `last_embedded`, overflow line.
6. If `suspects`: prints count with explanation, top-5 with `retrievals` / `engagement_rate * 100`, overflow line.
7. Prints trailing rule.

**Print format details that must be preserved exactly:**

```
\n + "─" * 60
  corpulse — Cleanup Report
─ * 60
  Total documents : {health['total_docs']}
  Noise estimate  : {health['noise_estimate']*100:.0f}%
  ⚠  {health['recommendation']}    ← only if bloat_warning
(blank line)
  👻  GHOSTS  ({len(ghosts)} docs — never retrieved in {self.ghost_threshold_days}d)
      · {filename}
      … and {N-5} more   ← only if > 5
(blank line)
  💀  OBSOLETE  ({len(obsolete)} docs)
      · {filename}  →  superseded by {superseded_by}
(blank line)
  🕓  STALE EMBEDDINGS  ({len(stale)} docs)
      · {filename}  ({days_behind}d behind — source {source_updated}, embedded {last_embedded})
(blank line)
  🔁  RE-CHUNK CANDIDATES  ({len(suspects)} docs — high retrieval, low engagement)
      · {filename}  ({retrievals} retrievals, {engagement_rate*100:.0f}% engagement)
(blank line)
─ * 60 + \n
```

**Conditional sections:** Each section only prints if the list is non-empty. This must be preserved in the structured payload (empty list = section absent from output, but still present in the payload as an empty list).

---

## Helper Design

Four new private module-level functions in `corpulse/core.py`.

### `_build_dataframe_rows`

```python
def _build_dataframe_rows(
    all_docs: list[dict[str, Any]],
    r_map: dict[str, dict[str, Any]],       # {doc_id: retrieval_row}  (row has "cnt")
    e_map: dict[str, int],                   # {doc_id: engagement_count}
    ghost_ids: set[str],
    obsolete_ids: set[str],
    stale_ids: set[str],
) -> list[dict[str, Any]]:
    ...
```

**Returns:** Unsorted list of row dicts (sort happens at the DataFrame call site, preserving current behavior). Each dict:

```python
{
    "doc_id":          str,
    "filename":        str,
    "retrievals":      int,
    "engagements":     int,
    "engagement_rate": float,   # round(eng / ret, 2) if ret > 0 else 0.0
    "status":          str,     # "ghost"|"obsolete"|"stale"|"low_engagement"|"healthy"
}
```

**Status logic:** Uses the rounded `rate < 0.15` form from the current `to_dataframe()` — do NOT unify with `report()` form. See "Pitfalls" section.

**Why no sorting here:** Current `to_dataframe()` does `.sort_values("retrievals", ascending=False)` at the pandas call site. The helper returns unsorted so the async path (Phase 12) can also do the sort there.

---

### `_build_report_rows`

```python
def _build_report_rows(
    all_docs: list[dict[str, Any]],
    r_map: dict[str, dict[str, Any]],       # {doc_id: retrieval_row}
    e_map: dict[str, int],                   # {doc_id: engagement_count}
    ghost_ids: set[str],
    obsolete_ids: set[str],
    stale_ids: set[str],
    top_k: int,
) -> list[dict[str, Any]]:
    ...
```

**Returns:** List of row dicts, already sorted by retrievals descending, already trimmed to `top_k`. Each dict:

```python
{
    "filename":        str,
    "retrievals":      int,
    "engagement_rate": str,       # formatted display string: "42%" or "—"
    "status":          str,       # "ghost"|"obsolete"|"stale"|"low_engagement"|"healthy"
    "status_display":  str,       # STATUS_ICON lookup, e.g. "👻 ghost"
}
```

**Why include `status` AND `status_display`:** `status` is the machine-readable key (useful for Phase 12 structured payload). `status_display` is what `report()` currently formats via `STATUS_ICON`. Keeping both avoids the formatter re-doing the lookup.

**STATUS_ICON must live in the helper:** To ensure sync and async produce identical display strings without duplicating the dict, define `STATUS_ICON` at module level (private constant) in `core.py`, referenced by the helper.

**Status logic:** Uses the unrounded `(e_map.get(did, 0) / ret) < 0.15` form from the current `report()`. See "Pitfalls".

---

### `_build_report_summary`

```python
def _build_report_summary(
    all_docs: list[dict[str, Any]],
    window_days: int,
    health: dict[str, Any],
) -> dict[str, Any]:
    ...
```

**Returns:**

```python
{
    "total_docs":       int,
    "window_days":      int,
    "bloat_warning":    bool,
    "noise_pct":        float,        # health["noise_estimate"] * 100
    "ghosts":           int,
    "obsolete":         int,
    "duplicates":       int,
    "stale":            int,
    "recommendation":   str,
}
```

**Purpose:** Bundles the header and footer metadata for `report()`. The sync formatter pulls from this dict to produce the header string and the footer counts line. Phase 12's `AsyncCorpulse.report()` returns this dict as part of its payload.

---

### `_build_cleanup_payload`

```python
def _build_cleanup_payload(
    health: dict[str, Any],
    ghosts: list[dict[str, Any]],
    obsolete: list[dict[str, Any]],
    stale: list[dict[str, Any]],
    suspects: list[dict[str, Any]],
    ghost_threshold_days: int,
) -> dict[str, Any]:
    ...
```

**Returns:**

```python
{
    "total_docs":           int,
    "noise_pct":            float,    # health["noise_estimate"] * 100 — pre-computed for formatter
    "bloat_warning":        bool,
    "recommendation":       str,
    "ghost_threshold_days": int,      # needed by formatter for label text
    "ghosts": {
        "count": int,
        "top5":  list[dict],          # [{doc_id, filename}, ...] — first 5 items
        "overflow": int,              # max(0, len(ghosts) - 5)
    },
    "obsolete": {
        "count": int,
        "top5":  list[dict],          # [{doc_id, filename, superseded_by}, ...]
        "overflow": int,
    },
    "stale": {
        "count": int,
        "top5":  list[dict],          # [{doc_id, filename, source_updated, last_embedded, days_behind}, ...]
        "overflow": int,
    },
    "suspects": {
        "count": int,
        "top5":  list[dict],          # [{doc_id, filename, retrievals, engagement_rate}, ...]
        "overflow": int,
    },
}
```

**Why pre-compute `top5` and `overflow`:** The sync formatter currently does `ghosts[:5]` and `len(ghosts)-5` inline. By placing this in the helper, the async path in Phase 12 gets the same truncated view for its structured payload without re-slicing. The full lists remain accessible via the analysis methods if needed.

**Why include section dicts even when empty:** The formatter checks `if payload["ghosts"]["count"] > 0`. An empty section has `count=0`, `top5=[]`, `overflow=0`. This preserves the current `if ghosts:` guard faithfully.

---

## Structured Payload Schemas

Full literal examples for the planner and Phase 12 implementer.

### Dataframe row (from `_build_dataframe_rows`)

```python
{
    "doc_id":          "abc123",
    "filename":        "guide-v2.md",
    "retrievals":      14,
    "engagements":     2,
    "engagement_rate": 0.14,
    "status":          "low_engagement",
}
```

### Report row (from `_build_report_rows`)

```python
{
    "filename":        "guide-v2.md",
    "retrievals":      14,
    "engagement_rate": "14%",         # display string
    "status":          "low_engagement",
    "status_display":  "◌  low eng.",
}
```

### Report summary (from `_build_report_summary`)

```python
{
    "total_docs":     42,
    "window_days":    30,
    "bloat_warning":  True,
    "noise_pct":      23.0,
    "ghosts":         5,
    "obsolete":       2,
    "duplicates":     4,
    "stale":          3,
    "recommendation": "Consider pruning ~9 low-signal documents.",
}
```

### Cleanup payload (from `_build_cleanup_payload`)

```python
{
    "total_docs":           42,
    "noise_pct":            23.0,
    "bloat_warning":        True,
    "recommendation":       "Consider pruning ~9 low-signal documents.",
    "ghost_threshold_days": 30,
    "ghosts": {
        "count": 5,
        "top5":  [{"doc_id": "g1", "filename": "old.md"}, ...],
        "overflow": 0,
    },
    "obsolete": {
        "count": 2,
        "top5":  [{"doc_id": "o1", "filename": "api-v1.md", "superseded_by": "api-v2.md"}, ...],
        "overflow": 0,
    },
    "stale": {
        "count": 3,
        "top5":  [{"doc_id": "s1", "filename": "stale.md", "source_updated": "2026-01-10",
                   "last_embedded": "2025-12-25", "days_behind": 16}, ...],
        "overflow": 0,
    },
    "suspects": {
        "count": 1,
        "top5":  [{"doc_id": "r1", "filename": "noisy.md", "retrievals": 9, "engagement_rate": 0.0}],
        "overflow": 0,
    },
}
```

---

## Sync Refactor Strategy

### `Corpulse.to_dataframe()` refactor

**Stays in method:**
- `import pandas` guard and `RuntimeError` raise
- `since` computation
- Backend reads: `retrieval_counts`, `engagement_counts`, calls to `get_ghosts()`, `get_obsolete()`, `get_stale_embeddings()`, `all_documents()`
- Conversion of result lists to `r_map`, `e_map`, `ghost_ids`, `obs`, `stale` sets
- Final `pd.DataFrame(rows).sort_values(...)` call

**Moves to `_build_dataframe_rows`:**
- The `for doc in all_documents()` loop
- `ret`, `eng`, `rate` computation
- Status classification
- Row dict assembly

**New body sketch:**

```python
def to_dataframe(self, window_days=None):
    try:
        import pandas as pd
    except ImportError:
        raise RuntimeError("pip install pandas to use to_dataframe()")

    since = _days_ago(window_days or self.ghost_threshold_days)
    r_map = {r["doc_id"]: r for r in self.db.retrieval_counts(since=since)}
    e_map = {e["doc_id"]: e["cnt"] for e in self.db.engagement_counts(since=since)}
    ghost_ids = {d["doc_id"] for d in self.get_ghosts()}
    obs       = {d["doc_id"] for d in self.get_obsolete()}
    stale_ids = {d["doc_id"] for d in self.get_stale_embeddings()}

    rows = _build_dataframe_rows(
        self.db.all_documents(), r_map, e_map, ghost_ids, obs, stale_ids
    )
    return pd.DataFrame(rows).sort_values("retrievals", ascending=False)
```

---

### `Corpulse.report()` refactor

**Stays in method:**
- `tabulate` import guard and `_tabulate` flag
- `since` computation
- Backend reads (same as current)
- `r_map`, `e_map`, `ghost_ids`, `obs`, `stale_ids` set construction
- Call to `corpus_health()`
- `header` string construction (uses `summary` dict)
- `print(header)`
- `if _tabulate:` branch — `tabulate(...)` call with column headers and `tablefmt`
- `else:` fallback loop printing plain-text rows
- Footer `print()` with ghost/obsolete/duplicate/stale counts

**Moves to `_build_report_rows`:**
- `sorted(all_docs, key=...)[: self.top_k_report]` iteration
- `ret`, `eng`, `rate` (as formatted string) computation
- Status classification (unrounded form)
- `STATUS_ICON` lookup
- Row list/dict assembly

**Moves to `_build_report_summary`:**
- `total`, `window_days or self.ghost_threshold_days` packaging
- Health dict field extraction into summary dict

**Formatter note:** Sync `report()` passes `rows` to `tabulate()` as a list-of-lists (`[filename, ret, rate_str, status_display]`). After refactor, each row is a dict. The formatter extracts the four columns from the dict before passing to tabulate:

```python
table_rows = [[r["filename"], r["retrievals"], r["engagement_rate"], r["status_display"]]
              for r in rows]
print(tabulate(table_rows, headers=["Document", "Retrieved", "Engagement", "Status"],
               tablefmt="rounded_outline"))
```

This produces byte-identical output because the data is the same. The formatter just unpacks from dict rather than building the list directly.

---

### `Corpulse.cleanup_report()` refactor

**Stays in method:**
- All `print()` calls — every line, every emoji, every spacing
- Conditional `if health["bloat_warning"]:` print
- `if ghosts:` / `if obsolete:` / `if stale:` / `if suspects:` guards (now `if payload["ghosts"]["count"] > 0:`)
- `for g in ghosts[:5]:` loops (now `for g in payload["ghosts"]["top5"]:`)
- `if len(ghosts) > 5:` overflow prints (now `if payload["ghosts"]["overflow"] > 0:`)

**Moves to `_build_cleanup_payload`:**
- All list-slicing (`[:5]`, `len(x) - 5`)
- Pre-computing `noise_pct`, `ghost_threshold_days` bundling
- Section dict assembly

**New body sketch:**

```python
def cleanup_report(self):
    health   = self.corpus_health()
    ghosts   = self.get_ghosts()
    obsolete = self.get_obsolete()
    stale    = self.get_stale_embeddings()
    suspects = self.get_suspects()

    payload = _build_cleanup_payload(
        health, ghosts, obsolete, stale, suspects, self.ghost_threshold_days
    )

    print("\n" + "─" * 60)
    print("  corpulse — Cleanup Report")
    print("─" * 60)
    print(f"  Total documents : {payload['total_docs']}")
    print(f"  Noise estimate  : {payload['noise_pct']:.0f}%")
    if payload["bloat_warning"]:
        print(f"  ⚠  {payload['recommendation']}")
    print()

    g = payload["ghosts"]
    if g["count"] > 0:
        print(f"  👻  GHOSTS  ({g['count']} docs — never retrieved in {payload['ghost_threshold_days']}d)")
        for item in g["top5"]:
            print(f"      · {item['filename']}")
        if g["overflow"] > 0:
            print(f"      … and {g['overflow']} more")
        print()

    # ... same pattern for obsolete, stale, suspects ...

    print("─" * 60 + "\n")
```

This is byte-identical to current output because `payload['total_docs']` is `health['total_docs']`, `payload['noise_pct']` is `health['noise_estimate'] * 100`, etc. — the formatter just reads from the payload dict instead of the raw result lists.

---

## Validation Architecture

`nyquist_validation: true` in `.planning/config.json` — this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (detected — `tests/conftest.py` exists, `pyproject.toml` has pytest config) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run | `pytest tests/test_async_core_integration.py tests/test_core_backend_integration.py -q` |
| Full suite | `pytest tests/ -q` |
| Async support | `pytest-anyio` (already used in `test_async_core_integration.py`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| REPORT-HELPERS-01 | `_build_dataframe_rows` returns correct rows for known fixture | unit | `pytest tests/test_report_helpers.py::test_build_dataframe_rows -x` | ❌ Wave 0 |
| REPORT-HELPERS-01 | `_build_report_rows` returns correct rows, sorted, trimmed | unit | `pytest tests/test_report_helpers.py::test_build_report_rows -x` | ❌ Wave 0 |
| REPORT-HELPERS-01 | `_build_report_summary` returns correct summary dict | unit | `pytest tests/test_report_helpers.py::test_build_report_summary -x` | ❌ Wave 0 |
| REPORT-HELPERS-01 | `_build_cleanup_payload` returns correct section dicts with top5/overflow | unit | `pytest tests/test_report_helpers.py::test_build_cleanup_payload -x` | ❌ Wave 0 |
| REPORT-HELPERS-02 | Sync `report()` stdout unchanged pre/post refactor | stdout snapshot | `pytest tests/test_report_helpers.py::test_report_stdout_unchanged -x` | ❌ Wave 0 |
| REPORT-HELPERS-02 | Sync `cleanup_report()` stdout unchanged pre/post refactor | stdout snapshot | `pytest tests/test_report_helpers.py::test_cleanup_report_stdout_unchanged -x` | ❌ Wave 0 |
| REPORT-HELPERS-02 | `to_dataframe()` raises RuntimeError when pandas missing | unit | `pytest tests/test_report_helpers.py::test_to_dataframe_raises_without_pandas -x` | ❌ Wave 0 |
| REPORT-HELPERS-02 | `report()` fallback plain-text path works when tabulate missing | unit | `pytest tests/test_report_helpers.py::test_report_fallback_without_tabulate -x` | ❌ Wave 0 |

### Backwards-Compat Verification Strategy

The recommended approach is **stdout capture via `capsys`** — not golden files.

Rationale:
- Golden files require an external fixture file that can drift from the code
- `capsys` captures are inline, always current, and fail loudly if output changes
- The test can be structured as: run `report()` against a deterministic `InMemoryBackend` fixture, capture stdout, assert it matches an expected multiline string literal
- The expected string is constructed from the known format — this makes the test self-documenting and the assertion exact

Implementation pattern:

```python
def test_report_stdout_unchanged(capsys):
    corp = Corpulse(backend=_report_fixture_backend())
    corp.report(window_days=30)
    captured = capsys.readouterr().out
    assert captured == EXPECTED_REPORT_OUTPUT  # multiline string constant in test file
```

The `EXPECTED_REPORT_OUTPUT` string is derived from current code behaviour by running the test once before the refactor to capture the baseline. This is an important Wave 0 step: **generate the expected strings before touching the implementation**.

For `to_dataframe()`: assert DataFrame column names, row count, dtypes, `retrievals` sort order, and specific cell values against the same fixture. No stdout involved.

### Sampling Rate

- Per-task: `pytest tests/test_report_helpers.py -q`
- Per-wave: `pytest tests/ -q`
- Phase gate: full suite green + 0 regressions in `test_async_core_integration.py`

### Wave 0 Gaps

- [ ] `tests/test_report_helpers.py` — new file covering all four helpers and both backwards-compat stdout assertions
- [ ] `EXPECTED_REPORT_OUTPUT` constant — captured from pre-refactor run
- [ ] `EXPECTED_CLEANUP_OUTPUT` constant — captured from pre-refactor run
- [ ] `_report_fixture_backend()` helper — deterministic `InMemoryBackend` with known docs, retrievals, engagements

---

## Pitfalls and Gotchas

### 1. The `rate < 0.15` vs `(eng / ret) < 0.15` divergence

**What:** `to_dataframe()` classifies `low_engagement` using `rate = round(eng / ret, 2)` and then checks `rate < 0.15`. `report()` uses raw `(e_map.get(did, 0) / ret) < 0.15`.

**When it matters:** A document with `eng=1, ret=7` has `eng/ret = 0.1428...`, which rounds to `0.14 < 0.15` → `low_engagement` in both paths. But with `eng=1, ret=7` giving exactly `0.14285...` → rounds to `0.14`; these happen to agree. The divergence would occur at values like `eng=3, ret=20` → `0.15` exactly → rounds to `0.15`, NOT `< 0.15` in dataframe, but `0.15 < 0.15` is False in both. Edge case requires careful thought: `eng=2, ret=14` → `0.142857` → rounds to `0.14` → `0.14 < 0.15` is True in dataframe; raw is also `< 0.15`.

**Action:** Do NOT unify. `_build_dataframe_rows` uses the rounded form; `_build_report_rows` uses the raw form. Document with a comment in each helper.

### 2. `STATUS_ICON` scope

**What:** Currently defined inside `report()`. The dict is used only for the formatted display string.

**Action:** Extract to a module-level private constant `_STATUS_ICON` in `core.py`. Referenced by `_build_report_rows`. Not imported by `async_core.py` (async path returns `status` key; Phase 12 either uses `_STATUS_ICON` or omits display strings from its structured payload — that is a Phase 12 decision, not Phase 11).

### 3. Sorting stability in `_build_report_rows`

**What:** Current `report()` sorts by `r_map.get(d["doc_id"], {"cnt": 0})["cnt"]` descending then slices `[: self.top_k_report]`. If two documents have the same retrieval count, insertion order of `all_documents()` determines the tie-break.

**Action:** `_build_report_rows` must use the identical sort key. Do NOT switch to `sorted(..., key=..., reverse=True)` with a different secondary key. The sort is stable in Python, so tie-breaking follows the order of `all_documents()` — which is fine as long as the helper takes the same `all_docs` list.

### 4. `top_k` applied before building rows

**What:** The current code sorts ALL docs then slices to `top_k_report` before constructing the `rows` list. This means documents outside the top-K are never classified or included in the row list.

**Action:** `_build_report_rows` takes `top_k: int` and applies the trim before returning. This matches current behaviour. The dataframe helper does NOT trim — `to_dataframe()` shows all documents.

### 5. `engagement_rate` string format in `report()` rows

**What:** Current code builds `rate = f"{eng/ret*100:.0f}%"` if `ret > 0` else `"—"`. This is a display string put directly into the tabulate row. It must remain a string in `_build_report_rows` output — not a float.

**Action:** The `engagement_rate` key in report rows is a `str`. The `engagement_rate` key in dataframe rows is a `float`. These are different fields with the same name but different types — this is intentional and matches current behaviour.

### 6. `_SKLEARN` guard in `corpus_health()`

**What:** `corpus_health()` only calls `get_duplicates()` when `_SKLEARN` is True. The `_build_corpus_health` helper (from mf8) always receives a `duplicate_pairs` list — if `_SKLEARN` is False, that list is `[]`, so `duplicates=0` in the health result.

**Action:** No change needed for Phase 11 helpers. The `_build_report_summary` and `_build_cleanup_payload` consume the already-computed `health` dict, which already handles the sklearn guard. The helpers do not re-check `_SKLEARN`.

### 7. `get_ghosts()` is not pure — it calls the backend

**What:** The current `report()` and `to_dataframe()` call `self.get_ghosts()`, `self.get_obsolete()`, `self.get_stale_embeddings()` — which each call `self.db.*` internally. The helpers receive the results of those calls as sets, not the calls themselves.

**Action:** The new helpers receive `ghost_ids: set[str]`, `obsolete_ids: set[str]`, `stale_ids: set[str]` — the caller (sync method or async method) does the backend fetches first. This is the same pattern mf8 used (pass rows in, not backend reference).

### 8. `cleanup_report()` calls `corpus_health()` which re-fetches everything

**What:** Current `cleanup_report()` calls `corpus_health()`, which internally calls `get_ghosts()`, `get_obsolete()`, `get_stale_embeddings()`, `get_duplicates()` — all of which call the backend. Then `cleanup_report()` also separately calls `get_ghosts()`, `get_obsolete()`, `get_stale_embeddings()`, `get_suspects()`. This means some analysis is computed twice.

**Action:** Phase 11 does NOT fix this double-fetch. It preserves existing call structure inside the sync methods (to guarantee identical output), just moves the data-shaping into helpers. The double-fetch is a pre-existing performance characteristic — fixing it would be a separate optimisation beyond Phase 11 scope.

### 9. Unicode emoji width in tabulate output

**What:** `STATUS_ICON` values contain Unicode emoji (`👻`, `⚠`, `🕓`, `◌`, `✓`). These emoji have variable terminal display width. Tabulate's `rounded_outline` format aligns columns based on character count, not display width. This is current behaviour and not changed.

**Action:** No change. The helper returns the same emoji strings. Tabulate is called identically.

### 10. Wave 0 ordering — capture golden strings BEFORE refactoring

**What:** The stdout snapshot test requires `EXPECTED_REPORT_OUTPUT` to match post-refactor output. The only reliable way to derive this constant is to run the current code against the fixture and capture its output.

**Action:** Wave 0 of the plan must: (1) create test fixture, (2) write a temporary script or test to capture current output, (3) embed the captured string as the test constant, (4) THEN implement the refactor. Running the fixture against the new code should produce the same string.

---

## Open Questions (RESOLVED)

1. **Should `_build_report_rows` include the raw `status` key alongside `status_display`?**
   - RESOLVED: YES. Phase 11 keeps both `status` and `status_display` in the helper output so Phase 12 can consume the machine-readable status key without changing the helper contract later.

2. **Should `_build_cleanup_payload` include the full lists (not just top5) as separate keys?**
   - RESOLVED: NO. Phase 11 limits the payload to `count`, `top5`, and `overflow` per section because that matches current cleanup-report semantics; callers needing full lists continue using `get_ghosts()`, `get_obsolete()`, `get_stale_embeddings()`, and `get_suspects()` directly.

3. **Should `to_dataframe()`'s reset_index be included?**
   - RESOLVED: NO. Phase 11 preserves the current `pd.DataFrame(rows).sort_values("retrievals", ascending=False)` behavior without `reset_index()`, so downstream work must not assume a reindexed DataFrame.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 11 is a pure Python in-process refactor with no external tool dependencies beyond what is already verified installed (pytest, numpy, scikit-learn). No new external services, CLIs, or runtimes are introduced.

---

## Sources

All findings are [VERIFIED: codebase] — derived from direct Read tool inspection of the files listed in `<files_to_read>`.

- `corpulse/core.py` — full file read, lines 1-703
- `corpulse/async_core.py` — full file read
- `tests/test_async_core_integration.py` — full file read
- `tests/test_core_backend_integration.py` — full file read
- `.planning/REQUIREMENTS.md` — REPORT-HELPERS-01 and REPORT-HELPERS-02
- `.planning/ROADMAP.md` — Phase 11 success criteria
- `.planning/PROJECT.md` — key decisions and constraints
- `.planning/config.json` — `nyquist_validation: true` confirmed
- `pytest tests/ -q` — baseline test run: all non-Postgres tests pass, 4 skipped

---

## RESEARCH COMPLETE

**Phase:** 11 — Shared Report Helpers
**Confidence:** HIGH — all claims derived from direct codebase inspection; no external tool lookup required; all code paths traced manually.

### Key Findings

1. Four helpers needed: `_build_dataframe_rows`, `_build_report_rows`, `_build_report_summary`, `_build_cleanup_payload`. All follow the mf8 pattern (pure functions, pre-fetched rows as inputs, structured dicts/lists as outputs).

2. **Critical pre-existing inconsistency:** `to_dataframe()` uses rounded `rate < 0.15` for low-engagement classification; `report()` uses raw `(eng/ret) < 0.15`. Both must be preserved as-is — do NOT unify.

3. **`STATUS_ICON` must move to module level** as a private constant (`_STATUS_ICON`) so `_build_report_rows` can reference it without redefining it inside a method.

4. **Wave 0 must capture golden stdout strings BEFORE implementing the refactor.** The backwards-compat test depends on an expected-output constant derived from current code behaviour.

5. **`cleanup_report()` double-fetch is pre-existing and must not be "fixed" in this phase.** Preserving it ensures identical output and avoids scope creep.

6. The sync methods remain structurally unchanged at the backend-call level — they still call `get_ghosts()`, `get_obsolete()`, etc. The only change is that the inner loop / data-shaping moves to the helper, and the method calls the helper then formats the result.

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Helper signatures | HIGH | Derived from line-by-line code trace |
| Payload schemas | HIGH | Directly reverse-engineered from current print/return logic |
| Backwards-compat strategy | HIGH | `capsys` is the standard pytest approach; no golden files needed |
| Pitfalls | HIGH | Found by static trace; rate divergence confirmed by reading both code paths |

### Ready for Planning

Research complete. Planner can now create PLAN.md.
