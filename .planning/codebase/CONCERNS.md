# Codebase Concerns

**Analysis Date:** 2026-03-24

## Tech Debt

**Inefficient duplicate detection logic:**
- Issue: `corpus_health()` calls `get_duplicates()` twice (lines 330-334 in `memento.py`) to extract both `doc_id_a` and `doc_id_b`. The second call re-runs the full similarity matrix computation instead of reusing results.
- Files: `memento.py` (lines 329-334)
- Impact: Performance degradation on corpora with many documents. Full O(n²) cosine similarity computation runs twice unnecessarily.
- Fix approach: Cache duplicate pairs after first calculation, or refactor `corpus_health()` to compute duplicates once and extract both sets.

**Nested list comprehensions and lookups in reporting:**
- Issue: `to_dataframe()` and `report()` methods iterate through all documents and perform repeated dictionary lookups for retrieval/engagement maps (lines 364-375, 475-490). For each document, nested lookups like `r_map[did]` occur even when doc has no retrievals.
- Files: `memento.py` (lines 356-392, lines 449-515)
- Impact: O(n) operations scale poorly with corpus size. Multiple passes over `all_documents()` without batch queries.
- Fix approach: Consolidate into single query loops; use `.get()` with defaults instead of exceptions; consider lazy evaluation for report generation.

**Arbitrary magic numbers without configuration:**
- Issue: Hard-coded thresholds in `get_suspects()` (line 298: `< 5` retrieval minimum, line 301: `< 0.15` engagement rate) have no corresponding Memento configuration parameters.
- Files: `memento.py` (lines 298, 301)
- Impact: Cannot tune suspect detection without modifying source code. Different use cases may need different thresholds.
- Fix approach: Add `min_retrieval_threshold` and `min_engagement_threshold` parameters to `__init__()`.

**Naive query hashing:**
- Issue: `_hash_query()` truncates SHA256 to 16 characters (line 34). While unlikely to cause collision issues in practice, this design choice is undocumented and not parameterized.
- Files: `memento.py` (line 34)
- Impact: If two different queries hash to the same 16-char prefix, engagement/retrieval tracking becomes conflated.
- Fix approach: Either document the collision-safety assumptions or make hash length configurable.

## Known Bugs

**Noise estimate double-counting:**
- Symptoms: `corpus_health()` returns `noise_estimate` that sums `ghosts + obsolete + stale + dupes` and then divides by total (line 337). A document can be counted in multiple categories (e.g., a doc can be both ghost AND stale), inflating the noise ratio.
- Files: `memento.py` (lines 336-338)
- Trigger: Create a corpus with documents that are both ghost (never retrieved) AND have stale embeddings. `noise_ratio` will exceed 1.0 in some edge cases (clamped to 1.0 on line 338, but the underlying math is incorrect).
- Workaround: Use the individual counts (`ghosts`, `obsolete`, `stale`, `duplicates`) directly rather than relying on `noise_estimate`.

**Potential missing query hash in engagement:**
- Symptoms: Engagement events are not tied to specific queries; only document + timestamp recorded. High engagement on one query may mask low engagement on another.
- Files: `memento.py` (line 136), `db.py` (lines 80-85)
- Trigger: Log high engagement for a frequently-retrieved document, followed by many retrievals with low engagement. Per-document engagement rate obscures query-level issues.
- Workaround: None built-in. Analyze raw retrieval + engagement tables directly.

**Status assignment conflicts in reporting:**
- Symptoms: A document matching multiple status conditions (e.g., ghost AND obsolete) gets assigned only the first matching status (lines 377-381, 483-488). Reporting shows incomplete picture.
- Files: `memento.py` (lines 377-381, 483-488)
- Trigger: Create versioned documents where v1 is never retrieved. v1 is both ghost AND obsolete, but only shows as "ghost".
- Workaround: Check raw analysis methods separately (`get_ghosts()`, `get_obsolete()`, etc.) to get full picture.

## Security Considerations

**Direct SQL parameter binding (secure, but no validation):**
- Risk: While prepared statements are used correctly (SQLite `?` placeholders), doc_id and filename are passed through without length limits or validation. Malicious inputs won't cause injection, but could exceed SQLite's field limits.
- Files: `db.py` (all write methods lines 59-91)
- Current mitigation: SQLite's built-in prepared statement safety. No explicit validation layer.
- Recommendations: Add length validation on doc_id, filename (e.g., max 1024 chars) before insertion. Consider adding a validation layer in Memento class.

**No authentication on SQLite database:**
- Risk: Default `./memento.db` file has no encryption or access controls. Sensitive corpus metadata is readable by any user with filesystem access.
- Files: `db.py` (line 39), `memento.py` (line 74)
- Current mitigation: Users can place DB file in protected directory. Documentation suggests no security for sensitive data.
- Recommendations: Document that this is local-only analytics. For sensitive deployments, recommend storing DB path in secure location or using encrypted filesystem. Consider optional encryption parameter.

**Demo hardcodes sensitive patterns:**
- Risk: `demo.py` contains example query strings and document contents that might reveal internal system structure if committed to public repos.
- Files: `demo.py` (lines 89-96)
- Current mitigation: Demo file is example-only.
- Recommendations: None if this is intentional demo file. If repo is public, consider moving sensitive examples to private documentation.

## Performance Bottlenecks

**All-documents materializes entire corpus into Python memory:**
- Problem: `all_documents()` calls `fetchall()` (line 97 in `db.py`) without pagination. Large corpora (>100K documents) will cause memory spikes.
- Files: `db.py` (line 97), used by `memento.py` lines 176, 231, 269, 319, 371, 458, 475
- Cause: Single query fetches all rows; no streaming or cursor-based iteration.
- Improvement path: Implement generator methods or pagination (e.g., `all_documents_paginated(batch_size=1000)`). Most analysis methods only need to process documents once; lazy evaluation would help.

**Duplicate detection recomputes similarity matrix on every call:**
- Problem: `get_duplicates()` loads all embeddings and recomputes full cosine similarity matrix (lines 204-208). No caching.
- Files: `memento.py` (lines 183-221)
- Cause: Called repeatedly by `corpus_health()`, `cleanup_report()`, `report()`, each causing O(n²) work.
- Improvement path: Cache the similarity matrix with a validity timestamp. Invalidate only when new embeddings are added. Alternatively, compute similarity lazily during analysis initialization.

**Regex compilation in loop:**
- Problem: `get_obsolete()` compiles `obsolete_pattern` regex for every call, then calls `pattern.search()` and `pattern.sub()` on every document (lines 232, 237, 247).
- Files: `memento.py` (lines 232, 237, 247-248)
- Cause: Pattern recompiled even though it's initialized once in `__init__()`.
- Improvement path: Pre-compile and cache pattern in `__init__()` (minor improvement but good practice).

**Report generation is O(n × m) where m is analysis methods:**
- Problem: `report()` calls `get_ghosts()`, `get_obsolete()`, `get_stale_embeddings()` separately (lines 462-464), each scanning all documents independently.
- Files: `memento.py` (lines 449-515)
- Cause: No batching or unified analysis pass.
- Improvement path: Refactor to single-pass analysis that computes all statuses simultaneously. Cache results for reuse.

## Fragile Areas

**Engagement rate calculation assumes retrieval exists:**
- Files: `memento.py` (lines 300, 375, 481, 486)
- Why fragile: Division by zero is handled (`if ret > 0`), but engagement tracking is completely separate from retrieval tracking. A document with engagement events but no retrieval records will have engagement_rate calculated as 0. Edge case: what if engagement is logged before any retrieval?
- Safe modification: Add explicit validation that enforces retrieval-before-engagement constraint in `log_engagement()`.
- Test coverage: No tests visible. Demo doesn't cover engagement-only scenarios.

**Embedding vector serialization/deserialization is lossy:**
- Files: `memento.py` (lines 47-52)
- Why fragile: Vectors are converted to `float32` numpy arrays (line 48). Rounding errors accumulate, and similarity scores computed after round-trip won't exactly match original. If duplicate detection threshold is very close (e.g., 0.920 vs 0.921), inconsistency is possible.
- Safe modification: Document precision assumptions. Add test vectors that should/shouldn't trigger duplication at threshold.
- Test coverage: No visible tests for embedding round-trip accuracy.

**Filename parsing for obsolete detection relies on regex extraction:**
- Files: `memento.py` (lines 232-260)
- Why fragile: If `obsolete_pattern` doesn't match expected version strings, files won't group correctly. Default pattern `r"v\d+"` won't catch "v1.2.3", "version1", "1.0", etc.
- Safe modification: Add warnings when version extraction fails. Document pattern expectations clearly.
- Test coverage: Demo includes "v1"/"v2" files. No tests for edge cases like non-standard versioning.

## Scaling Limits

**SQLite single-writer limitation:**
- Current capacity: Works fine for single-threaded RAG pipelines; scales to ~1M retrieval events.
- Limit: If multiple processes/threads call `log_retrieval()` concurrently, SQLite write-ahead logging (WAL) mode may experience contention. Beyond ~1B events, query performance degrades.
- Scaling path: For large-scale deployments, migrate DB layer to PostgreSQL or similar. Implement a `DBBackend` interface allowing swappable implementations.

**All embeddings loaded into memory for duplicate detection:**
- Current capacity: Works for ~10K documents with 512-dim embeddings (64MB per copy).
- Limit: 100K+ documents exceeds typical memory budgets. Similarity matrix would be 100K² = 10B floats = 40GB.
- Scaling path: Implement approximate nearest neighbor search (e.g., FAISS, LSH). Batch similarity computation. Move to vector database native duplicate detection.

**Report generation tables are un-paginated:**
- Current capacity: `top_k_report` parameter limits to 20 rows by default. Works for single-shot analysis.
- Limit: If user wants full corpus health report on 100K+ documents, memory and runtime are prohibitive.
- Scaling path: Stream reports to file. Implement pagination UI. Aggregate statistics without enumerating all documents.

## Dependencies at Risk

**numpy dependency implicit through scikit-learn:**
- Risk: `numpy` is listed as direct import (line 14, `memento.py`) but no separate requirement enforced. If scikit-learn requirement is dropped, numpy might not be installed.
- Impact: `_vec_to_bytes()` and `_bytes_to_vec()` would fail at runtime. `demo.py` imports `numpy` directly (line 11).
- Migration plan: Add numpy to explicit requirements. Alternatively, remove numpy dependency by using struct/array modules for serialization (lower precision but no external deps).

**scikit-learn is optional but fragile:**
- Risk: Duplicate detection feature silently disabled if scikit-learn not installed (lines 19-22). No warning unless `get_duplicates()` called directly. User may assume duplicates are being tracked when they're not.
- Impact: `corpus_health()` silently doesn't count duplicates (line 329). Noise estimate misleadingly low.
- Migration plan: Either make it required, or add verbose logging on feature degradation. Consider alternatives like scipy or pure-Python cosine similarity.

**pandas is optional but encouraged:**
- Risk: `to_dataframe()` raises at call time if pandas not installed (line 361). User has no way to know beforehand.
- Impact: Integration guides may not be followed if user doesn't pre-install pandas.
- Migration plan: Add `[viz]` extras group to setup. Warn in docs that full reporting requires pandas + tabulate.

**tabulate is soft-required for pretty printing:**
- Risk: `report()` falls back to plain-text if tabulate not installed (lines 454-455). Behavior change without warning.
- Impact: Output formatting unexpectedly changes between environments.
- Migration plan: Add to required deps if pretty tables are core feature, or clarify that it's optional and graceful degradation applies.

## Missing Critical Features

**No garbage collection / data retention policy:**
- Problem: `log_retrieval()` and `log_engagement()` append infinitely. Database grows unbounded.
- Blocks: Long-running RAG systems will accumulate multi-GB databases with stale historical data.
- Recommendation: Add `cleanup(days=90)` method that prunes events older than N days. Optionally aggregate before deletion (e.g., store daily summaries, delete individual events).

**No concurrent write safety:**
- Problem: Multiple processes calling `log_retrieval()` simultaneously may corrupt SQLite WAL.
- Blocks: Deployment in multi-worker environments (e.g., FastAPI with 4 workers) without external locking.
- Recommendation: Add optional `Lock`-based serialization or migrate to concurrent-safe backend.

**Engagement events not linked to retrieval context:**
- Problem: When user engages with a document, which query was it from? Currently unknown.
- Blocks: Diagnosis of query-specific quality issues (e.g., "users ignore results for queries about X").
- Recommendation: Extend `log_engagement()` to accept optional `query_hash` or `context` parameter for query-aware engagement tracking.

**No A/B testing framework:**
- Problem: No way to track how metrics change when chunking or retrieval strategy changes.
- Blocks: Measuring impact of corpus improvements.
- Recommendation: Add experiment/variant tracking (e.g., `memento.set_variant("chunking_v2")` tags all subsequent events).

**No export to external monitoring systems:**
- Problem: Reports are printed to stdout. No webhook, no metrics export.
- Blocks: Integration with observability platforms (Datadog, Prometheus, etc.).
- Recommendation: Add `export_metrics(handler)` allowing pluggable exporters.

## Test Coverage Gaps

**No unit tests for core analysis methods:**
- What's not tested: `get_duplicates()`, `get_obsolete()`, `get_suspects()` logic. Demo file is integration-only.
- Files: `memento.py` (lines 169-313)
- Risk: Regression in similarity thresholds, version parsing, or engagement rate calculations would go unnoticed.
- Priority: High

**No edge case testing:**
- What's not tested: Empty corpus, single document, all documents identical, zero engagement, missing embeddings.
- Files: `memento.py` (all analysis methods)
- Risk: Crashes on empty datasets or division-by-zero scenarios.
- Priority: High

**No embedding round-trip accuracy tests:**
- What's not tested: Precision loss in `_vec_to_bytes()` / `_bytes_to_vec()` round-trip. Similarity scores before/after serialization.
- Files: `memento.py` (lines 47-52)
- Risk: Duplicate detection threshold behavior changes if vectors are serialized/deserialized in certain ways.
- Priority: Medium

**No concurrency/threading tests:**
- What's not tested: Simultaneous `log_retrieval()` calls from multiple threads. SQLite WAL safety.
- Files: `db.py` (context manager)
- Risk: Data corruption in multi-threaded deployments.
- Priority: High

**No database migration/schema versioning tests:**
- What's not tested: Behavior on upgrade (e.g., new columns added). Schema backwards compatibility.
- Files: `db.py` (lines 6-34, 43-45)
- Risk: If schema changes in future versions, old databases will silently fail.
- Priority: Medium

---

*Concerns audit: 2026-03-24*
