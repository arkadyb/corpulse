---
phase: 05-address-review-findings-in-corpus-health-and-qdrant-wrapper
plan: 02
subsystem: api
tags: [python, sqlite, analytics, corpus-health]
requires:
  - phase: 05-01
    provides: corpus_health regression coverage for empty-schema and overlap handling
provides:
  - stable corpus_health response keys for empty and populated corpora
  - unique noisy-document noise_estimate based on doc-id set unions
affects: [corpulse, analytics, review-followups]
tech-stack:
  added: []
  patterns: [stable analytics response contracts, unique noisy-doc set accounting]
key-files:
  created: [.planning/phases/05-address-review-findings-in-corpus-health-and-qdrant-wrapper/05-02-SUMMARY.md]
  modified: [corpulse/memento.py, tests/test_analytics.py]
key-decisions:
  - "Keep corpus_health() return type and public name unchanged while normalizing the empty-corpus shape to the populated schema."
  - "Compute noise_estimate from the union of noisy doc IDs so overlapping categories count once without reintroducing duplicate get_duplicates() calls."
patterns-established:
  - "Analytics summary methods should return one stable key contract regardless of empty/non-empty data state."
  - "Derived corpus ratios should be computed from explicit doc-id sets when categories can overlap."
requirements-completed: [RVW-CH-01, RVW-CH-02]
duration: 4min
completed: 2026-04-07
---

# Phase 05 Plan 02: Corpus Health Corrections Summary

**Stable corpus_health response keys and unique noisy-document accounting in the analytics API**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-07T08:06:00Z
- **Completed:** 2026-04-07T08:09:41Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `corpus_health()` now returns the full public schema even when the corpus is empty.
- `noise_estimate` now counts unique noisy documents once by unioning ghost, obsolete, stale, and duplicate doc IDs.
- The existing FIX-01 regression still passes, so `get_duplicates()` remains a single call per report.

## Task Commits

Each task was committed atomically:

1. **Task 1: Return a single stable corpus_health schema for empty and populated corpora** - `01e4940` (fix)
2. **Task 2: Compute noise_estimate from the union of noisy document IDs** - `b984aa6` (fix)

## Files Created/Modified
- `corpulse/memento.py` - Normalized the empty-corpus return contract and replaced overlapping count sums with explicit noisy doc-id set unions.
- `tests/test_analytics.py` - Renamed the empty-schema regression test so the plan's targeted verification selector matches an actual test.
- `.planning/phases/05-address-review-findings-in-corpus-health-and-qdrant-wrapper/05-02-SUMMARY.md` - Captures execution results, deviations, and verification.

## Decisions Made
- Kept the existing `corpus_health()` API surface unchanged and fixed behavior inside the method only.
- Used per-category doc-id sets plus `noisy_ids` union instead of summed counts because categories overlap by design.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Aligned the structure regression test with the planned verification selector**
- **Found during:** Task 1 (Return a single stable corpus_health schema for empty and populated corpora)
- **Issue:** `python3 -m pytest -q tests/test_analytics.py -k "corpus_health and structure"` collected zero tests because no corpus-health regression included `structure` in its name.
- **Fix:** Renamed the empty-schema regression test to include `structure` so the exact plan command verifies the intended contract.
- **Files modified:** `tests/test_analytics.py`
- **Verification:** `python3 -m pytest -q tests/test_analytics.py -k "corpus_health and structure"`
- **Committed in:** `01e4940`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The deviation was necessary to make the planned verification command meaningful. No product-scope change.

## Issues Encountered
- The task-level verification command for Task 1 selected zero tests until the regression name was aligned with the `-k "corpus_health and structure"` filter.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 5 plan 03 can build on a stable analytics contract while focusing on Qdrant wrapper behavior only.
- No blockers remain for the next plan.

## Self-Check: PASSED

Confirmed:
- Summary file exists at `.planning/phases/05-address-review-findings-in-corpus-health-and-qdrant-wrapper/05-02-SUMMARY.md`
- Task commits `01e4940` and `b984aa6` exist in git history

---
*Phase: 05-address-review-findings-in-corpus-health-and-qdrant-wrapper*
*Completed: 2026-04-07*
