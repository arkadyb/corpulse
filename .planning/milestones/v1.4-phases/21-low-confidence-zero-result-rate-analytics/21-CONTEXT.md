# Phase 21: Low-Confidence / Zero-Result Rate analytics - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn existing retrieval logs into low-confidence and zero-result analytics without adding schema, changing ingestion APIs, or introducing service-layer behavior. This phase defines the read-only library analytics surface for those signals.

</domain>

<decisions>
## Implementation Decisions

### Analytics surface
- **D-01:** Phase 21 should expose both summary metrics and drill-down detail, not only one or the other.
- **D-02:** The preferred public shape is a paired API: scalar summary methods for quick health checks and `get_*` detail methods for actionable query-level inspection.
- **D-03:** Naming should follow existing analysis conventions in `Corpulse` and `AsyncCorpulse`, where detailed analysis methods use the `get_*` prefix and read-only report surfaces remain separate.

### Metric boundaries
- **D-04:** Zero-result queries must remain a separate signal from low-confidence queries.
- **D-05:** Low-confidence should mean retrievals existed but the best score was weak relative to a configurable threshold.
- **D-06:** Zero-result should mean no usable retrievals were returned for a query in the analysis window, not "low confidence with score zero."

### Data access strategy
- **D-07:** Query-level aggregation belongs in backend methods, not inline inside `Corpulse` or `AsyncCorpulse`.
- **D-08:** SQLite, Postgres, async Postgres, and in-memory backends must expose aligned query-aggregation behavior so sync and async analytics stay symmetric.
- **D-09:** `Corpulse` and `AsyncCorpulse` should remain thin orchestration layers over backend aggregates plus pure result-building helpers, matching the existing architecture.

### the agent's Discretion
- Exact method names, as long as they preserve the summary-plus-detail split and align with the existing public API style.
- The precise typed payloads for detail rows, as long as they remain read-only, minimal, and backward-compatible with the current library style.
- Whether shared helper builders live in `core.py`, `models.py`, or a nearby internal helper layer, as long as sync and async paths reuse the same business logic.

</decisions>

<specifics>
## Specific Ideas

- Recommended API family:
  - `low_confidence_rate(...)`
  - `get_low_confidence_queries(...)`
  - `zero_result_rate(...)`
  - optionally `get_zero_result_queries(...)` if the planner finds the detail surface worth shipping in the same phase
- The intended user experience is: quick metric first, actionable query list second.
- This phase should not overload existing document-level report concepts like ghosts, stale embeddings, or suspects; it is query-centric analytics over existing retrieval data.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase definition
- `.planning/ROADMAP.md` — Phase 21 goal, dependency, and milestone placement
- `.planning/PROJECT.md` — v1.4 milestone framing and the explicit "no new schema / no new ingestion API" constraint
- `.planning/STATE.md` — current milestone context and accumulated rationale for v1.4

### Existing analytics API
- `corpulse/core.py` — sync analysis method shape (`get_ghosts`, `get_duplicates`, `get_obsolete`, `get_stale_embeddings`, `get_suspects`) and reporting split
- `corpulse/async_core.py` — async parity surface showing how new read-only analytics should mirror sync behavior
- `corpulse/models.py` — current typed payload conventions for analysis and report outputs

### Backend aggregation pattern
- `corpulse/backends/base.py` — storage contract that new aggregate methods must extend cleanly
- `corpulse/backends/sqlite.py` — existing retrieval aggregation pattern including `avg_rank` and `avg_score`
- `corpulse/backends/postgres.py` — sync Postgres aggregate implementation to keep aligned with SQLite
- `corpulse/backends/postgres_async.py` — async Postgres aggregate implementation to keep aligned with sync behavior
- `corpulse/backends/memory.py` — in-memory aggregate behavior used by tests and examples

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `corpulse/core.py` helper/build pattern: current analytics rely on thin facade methods plus shared pure builders, which Phase 21 should reuse.
- `corpulse/async_core.py` parity pattern: async methods mirror sync analysis names and semantics rather than inventing a separate async-only surface.
- `corpulse/models.py` TypedDict conventions: existing analysis payloads are lightweight typed dictionaries, not rich model objects.

### Established Patterns
- Analysis methods are read-only and named `get_*` when returning actionable records.
- Summary/report behavior is separated from analysis methods rather than mixed into one return shape.
- Backend classes own SQL and aggregation details; facade classes assemble domain-specific results from backend aggregates.

### Integration Points
- New backend aggregate methods will extend the `StorageBackend` contract and each concrete backend implementation.
- New sync analytics methods will live beside the existing `get_*` family in `corpulse/core.py`.
- New async analytics methods will mirror the sync surface in `corpulse/async_core.py`.
- If typed result rows are added, they should be introduced in `corpulse/models.py` alongside the current analysis payload types.

</code_context>

<deferred>
## Deferred Ideas

- MRR and acceptance-rate analytics are part of milestone v1.4 but not Phase 21.
- Any change to printed `report()` / `cleanup_report()` output that surfaces these new query metrics should be treated as follow-on work unless planning shows it cleanly belongs here.
- Generation-layer metrics such as faithfulness or context precision remain out of scope.

</deferred>

---

*Phase: 21-low-confidence-zero-result-rate-analytics*
*Context gathered: 2026-04-19*
