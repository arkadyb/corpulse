# Phase 23: User Acceptance Rate analytics - Research

<user_constraints>
## User Constraints

- Phase scope is narrow: define `acceptance_rate()` for the existing engagement table only, with no new schema and no new ingestion API surface. [VERIFIED: provided phase context; .planning/REQUIREMENTS.md; .planning/PROJECT.md]
- Keep the solution low-change and aligned with existing analytics conventions in `corpulse/core.py` and `corpulse/async_core.py`. [VERIFIED: provided phase context; corpulse/core.py; corpulse/async_core.py]
- Preserve sync/async parity across SQLite, sync Postgres, async Postgres, and in-memory backends. [VERIFIED: provided phase context; corpulse/backends/base.py; corpulse/backends/sqlite.py; corpulse/backends/postgres.py; corpulse/backends/postgres_async.py; corpulse/backends/memory.py]
- The current data model stores generic engagement events as `doc_id`, `event_type`, and `engaged_at`, but the only public aggregate today is `engagement_counts(since)`, which groups by `doc_id` only. [VERIFIED: corpulse/backends/sqlite.py; corpulse/backends/postgres.py; corpulse/backends/postgres_async.py; corpulse/backends/memory.py; corpulse/backends/base.py]
- The repo already frames Phase 23 as a documented accepted-event convention over the existing engagement table. [VERIFIED: .planning/PROJECT.md; .planning/ROADMAP.md; .planning/REQUIREMENTS.md; .planning/STATE.md]
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| v1.5-02 | `Corpulse` and `AsyncCorpulse` expose `acceptance_rate()` over the existing engagement table using a documented accepted-event convention, with no new ingestion APIs. | Define the metric as an engagement-table ratio driven by one shared accepted-event convention and a scalar-only facade method. [VERIFIED: .planning/REQUIREMENTS.md; .planning/ROADMAP.md; corpulse/core.py; corpulse/async_core.py] |
| v1.5-03 | Shared aggregation helpers and backend query contracts support SQLite, Postgres, async Postgres, and in-memory backends with deterministic ordering and parity tests. | Add one backend aggregate for engagement event-type counts, keep ordering deterministic, and reuse one pure helper across sync/async facades. [VERIFIED: .planning/REQUIREMENTS.md; corpulse/backends/base.py; corpulse/backends/sqlite.py; corpulse/backends/postgres.py; corpulse/backends/postgres_async.py; corpulse/backends/memory.py] |
</phase_requirements>

## Summary

User Acceptance Rate should be implemented as a scalar rate over the existing `engagements` table, not as a new schema or ingestion feature. The lowest-change shape is: add one backend aggregate that counts engagement rows by `event_type`, define one shared accepted-event convention in code/docs, and compute `accepted_count / total_count` in a pure helper reused by `Corpulse` and `AsyncCorpulse`. That matches the repository’s established pattern from Phase 21 and Phase 22: backend-owned aggregation plus a thin pure metric helper in the facade layer. [VERIFIED: corpulse/core.py; corpulse/async_core.py; .planning/phases/22-mean-reciprocal-rank-analytics/22-01-SUMMARY.md]

The unresolved part is the accepted-event allowlist. The repo does not currently define a canonical list beyond free-form examples like `"opened"`, `"copied"`, and `"thumbs_up"` in the `log_engagement()` docs/comments, so Phase 23 must lock that convention before implementation. The safest blast-radius-minimizing choice is a fixed, documented allowlist in one shared helper, exact-match or consistently normalized in one place, with everything else counted as non-accepted. [VERIFIED: corpulse/core.py; corpulse/async_core.py; corpulse/backends/sqlite.py] [ASSUMED: the allowlist should be fixed in code/docs rather than user-configurable for v1.5]

**Primary recommendation:** add `acceptance_rate(window_days=None)` as a scalar facade method backed by a new `engagement_event_counts(since)`-style aggregate, and define acceptance as the share of engagement rows whose `event_type` matches the shared accepted-event convention. [VERIFIED: corpulse/core.py; corpulse/async_core.py; corpulse/backends/base.py] [ASSUMED: the backend contract name should be additive rather than changing `engagement_counts()`]

## Standard Stack

### Core
| Library / Component | Version | Purpose | Why Standard |
|---|---:|---|---|
| `corpulse` | `0.1.0` | Existing analytics library and facade layer | Already owns the sync/async analysis pattern and the backend abstraction this phase must extend. [VERIFIED: pyproject.toml; corpulse/core.py; corpulse/async_core.py] |
| `StorageBackend` + concrete backends | repo state | Persistence contract and aggregate query layer | The current backends already implement the read/write surfaces that Phase 23 should extend with one additive aggregate. [VERIFIED: corpulse/backends/base.py; corpulse/backends/sqlite.py; corpulse/backends/postgres.py; corpulse/backends/postgres_async.py; corpulse/backends/memory.py] |
| `pytest` | `9.0.2` installed, `>=8.0` declared | Regression and parity tests | The repo already uses pytest for contract, analytics, and async integration coverage. [VERIFIED: pyproject.toml; pytest --version; tests/test_analytics.py; tests/test_async_core_integration.py; tests/test_backend_contract.py] |

### Supporting
| Library / Component | Version | Purpose | When to Use |
|---|---:|---|---|
| `psycopg[pool]` | `>=3.2` declared, installed | Sync Postgres backend parity | Needed only for the Postgres backend contract and any live Postgres verification. [VERIFIED: pyproject.toml; python import check] |
| `asyncpg` | `>=0.29` declared, installed | Async Postgres backend parity | Needed only for the async Postgres backend contract and any live async verification. [VERIFIED: pyproject.toml; python import check] |
| `scikit-learn` | `>=1.3` declared, installed | Existing duplicate-detection path | Not needed for acceptance rate itself, but part of the current runtime and test environment. [VERIFIED: pyproject.toml; python import check] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|---|---|---|
| New event-type aggregate | Count accepted events by scanning raw engagement rows in the facade | Larger Python-side work, repeated filtering logic, and weaker backend parity. [VERIFIED: repo architecture pattern from Phase 21/22] |
| Fixed allowlist | Add `accepted_events=` as a public parameter | More flexible, but bigger API surface and more test permutations for a metric that should stay stable in v1.5. [ASSUMED] |
| Scalar-only method | Add a detail drill-down API in the same phase | Not required by the current requirement and would expand scope beyond the minimal metric. [VERIFIED: .planning/REQUIREMENTS.md; .planning/ROADMAP.md] |

**Installation:** No new runtime dependency is required for the metric itself. The phase should reuse the existing package set and only add code/tests. [VERIFIED: pyproject.toml; corpulse/backends/*]

## Architecture Patterns

### Recommended Project Structure
```text
corpulse/
├── core.py              # sync facade; shared pure acceptance helper
├── async_core.py        # async facade; reuses the same pure helper
├── models.py            # add a TypedDict for event-type engagement aggregates if needed
└── backends/
    ├── base.py          # additive aggregate contract
    ├── sqlite.py        # SQLite GROUP BY event_type
    ├── postgres.py      # sync Postgres GROUP BY event_type
    ├── postgres_async.py# async Postgres GROUP BY event_type
    └── memory.py        # deterministic in-memory aggregation
```

### Pattern 1: Backend aggregate first, pure helper second
**What:** Add a backend method that returns engagement counts grouped by `event_type`, then pass those rows into one pure helper that computes accepted rows divided by total rows. [ASSUMED]
**When to use:** When a metric depends on stored row classes that the current backend contract does not yet expose. [VERIFIED: corpulse/backends/base.py]
**Example:**
```python
# corpulse/backends/sqlite.py [VERIFIED: repo inspection]
SELECT event_type, COUNT(*) AS cnt
FROM engagements
WHERE engaged_at >= ?
GROUP BY event_type
ORDER BY event_type
```
```python
# corpulse/core.py [ASSUMED]
def _build_acceptance_rate(event_rows, accepted_event_types):
    total = sum(int(row["cnt"]) for row in event_rows)
    if total == 0:
        return 0.0
    accepted = sum(
        int(row["cnt"])
        for row in event_rows
        if row["event_type"] in accepted_event_types
    )
    return round(accepted / total, 2)
```

### Pattern 2: Keep the facade scalar-only
**What:** `acceptance_rate()` should return one float, not a report payload or a mixed summary/detail structure. [ASSUMED]
**When to use:** When the requirement only asks for a metric and the library already has a separate analysis/report split. [VERIFIED: corpulse/core.py; corpulse/async_core.py]
**Why:** This matches `low_confidence_rate()`, `zero_result_rate()`, and the Phase 22 scalar MRR method. [VERIFIED: corpulse/core.py; corpulse/async_core.py; .planning/phases/22-mean-reciprocal-rank-analytics/22-01-SUMMARY.md]

### Anti-Patterns to Avoid
- **Changing `engagement_counts()` to include `event_type`:** that would break existing suspect/report consumers that expect per-document counts. [VERIFIED: tests/test_backend_contract.py; corpulse/core.py; corpulse/async_core.py]
- **Counting accepted events in Python from raw rows:** that duplicates filtering logic across facades and backends. [ASSUMED]
- **Making acceptance depend on retrieval rows:** the current engagement table has no query linkage, so that would create a hidden semantic gap. [VERIFIED: corpulse/backends/base.py; corpulse/backends/sqlite.py]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Accepted-event breakdown | Per-facade row scanning or ad hoc SQL strings | One backend aggregate method returning `event_type` counts | Keeps SQLite/Postgres/async Postgres/memory aligned and testable. [VERIFIED: corpulse/backends/base.py; corpulse/backends/sqlite.py; corpulse/backends/postgres.py; corpulse/backends/postgres_async.py; corpulse/backends/memory.py] |
| Event normalization | Multiple ad hoc `lower()` / `strip()` checks in different callers | One shared helper or constant for accepted-event matching | Avoids convention drift and keeps the metric definition auditable. [ASSUMED] |
| Unique-user acceptance | Treat `doc_id` as a user identifier | Do not infer unique-user semantics from this schema | The engagement table has no `user_id` or session column, so unique-user acceptance is not available from current data. [VERIFIED: corpulse/backends/sqlite.py; corpulse/backends/postgres.py] |

**Key insight:** the table already has enough information for an event-share metric, but not enough information for a true unique-user metric. Keep the scope on row-level acceptance share so the phase stays low-change. [VERIFIED: corpulse/backends/sqlite.py; corpulse/backends/postgres.py; corpulse/backends/postgres_async.py; corpulse/backends/memory.py]

## Common Pitfalls

### Pitfall 1: Ambiguous accepted-event semantics
**What goes wrong:** Different callers treat different `event_type` strings as acceptance, so the metric becomes unstable across environments. [ASSUMED]
**Why it happens:** `log_engagement()` is currently free-form and the repo does not define a canonical accepted-event allowlist. [VERIFIED: corpulse/core.py; corpulse/async_core.py]
**How to avoid:** Freeze the allowlist in one helper and document it in code/tests; do not scatter string checks across facades. [ASSUMED]
**Warning signs:** test fixtures start using mixed event labels and the scalar rate changes without an explicit spec change. [ASSUMED]

### Pitfall 2: Breakage from overloading existing aggregates
**What goes wrong:** Adding `event_type` to `engagement_counts()` breaks suspect/report consumers and contract tests. [VERIFIED: tests/test_backend_contract.py; corpulse/core.py]
**Why it happens:** The current public aggregate is doc-level and is already used by `get_suspects()`, `report()`, and `to_dataframe()`. [VERIFIED: corpulse/core.py; corpulse/async_core.py]
**How to avoid:** Add a new additive aggregate method and leave `engagement_counts()` untouched. [ASSUMED]
**Warning signs:** existing doc-level analytics need to re-map their inputs or their test expectations change. [VERIFIED: tests/test_analytics.py; tests/test_async_core_integration.py]

### Pitfall 3: Window mismatch
**What goes wrong:** numerator and denominator are computed from different time windows, producing a misleading rate. [ASSUMED]
**Why it happens:** the facade methods already use `window_days` / `_days_ago(...)`, so a new helper could accidentally drift if it uses raw timestamps in one place and a pre-filtered list in another. [VERIFIED: corpulse/core.py; corpulse/async_core.py]
**How to avoid:** pass one `since` cutoff through every backend aggregate and compute the ratio from the same filtered rows. [ASSUMED]
**Warning signs:** live and fixture tests disagree only on old data boundaries. [ASSUMED]

### Pitfall 4: Non-deterministic backend parity
**What goes wrong:** event-type rows come back in different orders or with different casing normalization across backends. [ASSUMED]
**Why it happens:** SQL backends need explicit `ORDER BY`, while the in-memory backend must sort manually. [VERIFIED: corpulse/backends/sqlite.py; corpulse/backends/postgres.py; corpulse/backends/postgres_async.py; corpulse/backends/memory.py]
**How to avoid:** sort by `event_type` everywhere and keep the helper order-insensitive. [ASSUMED]
**Warning signs:** backend contract tests start failing only on list equality, not on numeric result. [ASSUMED]

## Code Examples

Verified patterns from the current repo:

### Existing scalar metric shape
```python
# Source: [corpulse/core.py](/Users/arkady/src/corpulse/corpulse/core.py) [VERIFIED: repo inspection]
def low_confidence_rate(self, window_days: int | None = None, threshold: float | None = None) -> float:
    query_rows = self._query_rows(window_days)
    confidence_threshold = threshold if threshold is not None else self.low_confidence_threshold
    low_confidence_rows = _build_low_confidence_queries(query_rows, confidence_threshold)
    return _build_query_rate([row for row in query_rows if int(row["cnt"]) > 0], low_confidence_rows)
```

### Same helper reused by sync and async facades
```python
# Source: [corpulse/async_core.py](/Users/arkady/src/corpulse/corpulse/async_core.py) [VERIFIED: repo inspection]
async def zero_result_rate(self, window_days: int | None = None) -> float:
    query_rows = await self._query_attempt_rows(window_days)
    zero_result_rows = _build_zero_result_queries(query_rows)
    return _build_query_rate(query_rows, zero_result_rows)
```

### Acceptance-rate shape to mirror
```python
# Source: [corpulse/backends/sqlite.py](/Users/arkady/src/corpulse/corpulse/backends/sqlite.py) [VERIFIED: repo inspection]
SELECT event_type, COUNT(*) AS cnt
FROM engagements
WHERE engaged_at >= ?
GROUP BY event_type
ORDER BY event_type
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Inline Python counting in each facade | Backend-owned aggregate + shared pure helper | Phase 21 and Phase 22 established this pattern [VERIFIED: .planning/phases/22-mean-reciprocal-rank-analytics/22-01-SUMMARY.md; corpulse/core.py; corpulse/async_core.py] | Keeps sync/async semantics aligned and pushes filtering into the storage layer. |
| Mixed summary/detail return shapes | Scalar metric methods for rates, separate detail methods when needed | Phase 21 and Phase 22 [VERIFIED: corpulse/core.py; corpulse/async_core.py; .planning/phases/22-mean-reciprocal-rank-analytics/22-01-SUMMARY.md] | Acceptance rate should stay scalar-only unless a future phase explicitly asks for drill-down rows. |

**Deprecated/outdated:** `engagement_counts(since)` alone is not enough to compute acceptance rate because it loses the `event_type` dimension. [VERIFIED: corpulse/backends/base.py; corpulse/backends/sqlite.py; corpulse/backends/postgres.py; corpulse/backends/postgres_async.py; corpulse/backends/memory.py]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | Phase 23 should use one fixed accepted-event allowlist in shared code/docs rather than an `accepted_events=` public parameter. | Summary / Architecture Patterns | Public API and tests would need to expand, increasing blast radius. [ASSUMED] |
| A2 | The backend should expose a new additive event-type aggregate instead of changing `engagement_counts()`. | Architecture Patterns / Don't Hand-Roll | Existing document-level analytics would break if the contract is repurposed. [ASSUMED] |
| A3 | The public scalar result should follow the existing rate helpers and round to 2 decimals. | Summary / Code Examples | If the team wants higher precision, the tests will need a deliberate precision decision. [ASSUMED] |

## Open Questions

1. **Which `event_type` values count as accepted?**
   - What we know: the current API is free-form, and the repo only shows examples like `"opened"`, `"copied"`, and `"thumbs_up"`. [VERIFIED: corpulse/core.py; corpulse/async_core.py; corpulse/backends/sqlite.py]
   - What is unclear: whether the canonical allowlist is just `"opened"`, a small positive-action set, or a broader normalization rule. [ASSUMED]
   - Recommendation: lock the allowlist in one shared helper and write tests against those exact labels before implementation. [ASSUMED]

2. **Should the metric be exact-match or normalized?**
   - What we know: engagement labels are free-form strings, and the current schema does not constrain case or punctuation. [VERIFIED: corpulse/backends/sqlite.py; corpulse/backends/postgres.py]
   - What is unclear: whether `"Opened"` should count the same as `"opened"`. [ASSUMED]
   - Recommendation: choose one normalization rule now and apply it in one place only. [ASSUMED]

3. **Should acceptance be row-level or document-level?**
   - What we know: the schema stores engagement rows but not user IDs or sessions. [VERIFIED: corpulse/backends/sqlite.py; corpulse/backends/postgres.py]
   - What is unclear: whether the phrase "User Acceptance Rate" was intended to mean unique users rather than event rows. [ASSUMED]
   - Recommendation: treat it as an engagement-row rate for v1.5; unique-user acceptance is not derivable from the current model without extra identity data. [VERIFIED: corpulse/backends/sqlite.py; corpulse/backends/postgres.py] [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python | Running the library and tests | ✓ | 3.14.3 | — [VERIFIED: `python3 --version`] |
| pytest | Test execution | ✓ | 9.0.2 | — [VERIFIED: `pytest --version`] |
| `psycopg` / `psycopg_pool` | Sync Postgres backend tests | ✓ | installed | Use SQLite/in-memory contract tests if live Postgres is unavailable. [VERIFIED: python import check] |
| `asyncpg` | Async Postgres backend tests | ✓ | installed | Use mocked async backend parity tests if live Postgres is unavailable. [VERIFIED: python import check] |
| `scikit-learn` | Existing duplicate-detection runtime | ✓ | installed | Not needed for acceptance rate. [VERIFIED: python import check] |
| `pandas` | DataFrame/report path | ✗ | — | Not required for Phase 23. [VERIFIED: python import check] |
| `tabulate` | Pretty report printing | ✗ | — | Not required for Phase 23. [VERIFIED: python import check] |
| `CORPULSE_POSTGRES_TEST_CONNINFO` | Live Postgres verification | ✗ | unset | Rely on contract tests and mocked parity unless the env var is provided. [VERIFIED: `printenv CORPULSE_POSTGRES_TEST_CONNINFO`; python env check] |

**Missing dependencies with no fallback:**
- None for the acceptance-rate implementation itself. [VERIFIED: repo inspection; environment checks]

**Missing dependencies with fallback:**
- Live Postgres DSN is unset, but backend-contract and mocked parity tests can still cover the phase. [VERIFIED: environment check; tests/test_postgres_backend.py; tests/test_async_postgres_backend.py]

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Framework | `pytest 9.0.2` with `asyncio_mode = "auto"` [VERIFIED: pyproject.toml; pytest --version] |
| Config file | `pyproject.toml` [VERIFIED: pyproject.toml] |
| Quick run command | `pytest tests/test_analytics.py tests/test_async_core_integration.py tests/test_backend_contract.py -x` [VERIFIED: repo test layout; existing Phase 22 pattern] |
| Full suite command | `pytest` [VERIFIED: pyproject.toml] |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| v1.5-02 | `acceptance_rate()` returns a scalar rate from the accepted-event convention and preserves sync/async parity. | unit + integration | `pytest tests/test_analytics.py tests/test_async_core_integration.py -x` | ✅ existing files, new assertions needed [VERIFIED: repo inspection] |
| v1.5-03 | All backends expose the same additive aggregate contract with deterministic ordering. | contract | `pytest tests/test_backend_contract.py tests/test_postgres_backend.py tests/test_async_postgres_backend.py -x` | ✅ existing files, new assertions needed [VERIFIED: repo inspection] |

### Sampling Rate
- **Per task commit:** `pytest tests/test_analytics.py tests/test_backend_contract.py -x` [VERIFIED: existing suite layout]
- **Per wave merge:** `pytest tests/test_analytics.py tests/test_async_core_integration.py tests/test_backend_contract.py` [VERIFIED: existing suite layout]
- **Phase gate:** full suite green before verification [VERIFIED: repo workflow pattern]

### Wave 0 Gaps
- `tests/test_analytics.py` needs acceptance-rate semantics and empty/no-match coverage. [VERIFIED: repo inspection]
- `tests/test_async_core_integration.py` needs async parity assertions for the new scalar metric. [VERIFIED: repo inspection]
- `tests/test_backend_contract.py` needs a new backend aggregate contract assertion for event-type counts. [VERIFIED: repo inspection]
- `corpulse/models.py` may need a new `TypedDict` for the additive event-type aggregate row if the planner chooses to type it explicitly. [ASSUMED]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | Not part of a library-only read/aggregate metric. [VERIFIED: repo scope] |
| V3 Session Management | no | No session state exists in the current data model. [VERIFIED: corpulse/backends/sqlite.py; corpulse/backends/postgres.py] |
| V4 Access Control | no | No authorization logic is in scope for the analytics library. [VERIFIED: repo scope] |
| V5 Input Validation | yes | Validate or normalize accepted-event labels in one helper; use parameterized SQL in backends. [VERIFIED: corpulse/backends/sqlite.py; corpulse/backends/postgres.py; corpulse/backends/postgres_async.py] |
| V6 Cryptography | no | No new crypto is required. [VERIFIED: repo scope] |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Free-form event labels causing semantic drift | Tampering | One canonical allowlist / normalization helper; tests lock exact labels. [ASSUMED] |
| SQL injection | Tampering | Parameterized SQL only; no string interpolation of user values. [VERIFIED: corpulse/backends/sqlite.py; corpulse/backends/postgres.py; corpulse/backends/postgres_async.py] |
| Metric misreporting from inconsistent windows | Tampering / Repudiation | Use one `since` cutoff and one shared helper for all backends. [ASSUMED] |

## Sources

### Primary (HIGH confidence)
- [corpulse/core.py](/Users/arkady/src/corpulse/corpulse/core.py) - existing scalar metric shape, helper reuse pattern, and free-form engagement docs. [VERIFIED: repo inspection]
- [corpulse/async_core.py](/Users/arkady/src/corpulse/corpulse/async_core.py) - async parity surface and identical metric shape. [VERIFIED: repo inspection]
- [corpulse/backends/base.py](/Users/arkady/src/corpulse/corpulse/backends/base.py) - current storage contract. [VERIFIED: repo inspection]
- [corpulse/backends/sqlite.py](/Users/arkady/src/corpulse/corpulse/backends/sqlite.py) - current engagement schema and doc-level aggregate. [VERIFIED: repo inspection]
- [corpulse/backends/postgres.py](/Users/arkady/src/corpulse/corpulse/backends/postgres.py) - sync Postgres aggregate contract. [VERIFIED: repo inspection]
- [corpulse/backends/postgres_async.py](/Users/arkady/src/corpulse/corpulse/backends/postgres_async.py) - async Postgres aggregate contract. [VERIFIED: repo inspection]
- [corpulse/backends/memory.py](/Users/arkady/src/corpulse/corpulse/backends/memory.py) - deterministic in-memory aggregate behavior. [VERIFIED: repo inspection]
- [.planning/PROJECT.md](/Users/arkady/src/corpulse/.planning/PROJECT.md) - milestone framing and acceptance-rate requirement. [VERIFIED: repo inspection]
- [.planning/REQUIREMENTS.md](/Users/arkady/src/corpulse/.planning/REQUIREMENTS.md) - v1.5-02 and v1.5-03 requirement text. [VERIFIED: repo inspection]
- [.planning/ROADMAP.md](/Users/arkady/src/corpulse/.planning/ROADMAP.md) - phase 23 goal and dependency. [VERIFIED: repo inspection]
- [.planning/STATE.md](/Users/arkady/src/corpulse/.planning/STATE.md) - current milestone context and Phase 23 scope. [VERIFIED: repo inspection]
- [.planning/phases/22-mean-reciprocal-rank-analytics/22-01-SUMMARY.md](/Users/arkady/src/corpulse/.planning/phases/22-mean-reciprocal-rank-analytics/22-01-SUMMARY.md) - established backend-aggregate + pure-helper pattern. [VERIFIED: repo inspection]

### Secondary (MEDIUM confidence)
- None. [VERIFIED: repo inspection]

### Tertiary (LOW confidence)
- The exact accepted-event allowlist for Phase 23 is not defined in the repo yet and must be locked by the planner/user. [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - current package/runtime and existing backend contract are directly verified. [VERIFIED: repo inspection; environment checks]
- Architecture: MEDIUM - the backend-aggregate shape is clear, but the accepted-event convention is unresolved. [VERIFIED: repo inspection; ASSUMED]
- Pitfalls: MEDIUM - main risks are inferred from the current schema and the Phase 21/22 implementation pattern. [VERIFIED: repo inspection; .planning/phases/22-mean-reciprocal-rank-analytics/22-01-SUMMARY.md]

**Research date:** 2026-04-20
**Valid until:** 2026-05-20
