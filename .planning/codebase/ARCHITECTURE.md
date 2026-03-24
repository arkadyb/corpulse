# Architecture

**Analysis Date:** 2026-03-24

## Pattern Overview

**Overall:** Layered analytics wrapper with persistence layer

**Key Characteristics:**
- Single-responsibility core: `Memento` orchestrates ingestion and analysis
- Thin persistence abstraction: `DB` class isolates SQLite interactions
- No external dependencies for core functionality (optional: numpy, scikit-learn, pandas, tabulate)
- Event-driven data collection (retrieval events + engagement events)
- Time-windowed analysis (queries use configurable day thresholds)

## Layers

**API Layer (Public Interface):**
- Purpose: Expose analytics methods and ingestion hooks to RAG pipelines
- Location: `memento.py` (class `Memento`)
- Contains: Public methods for logging (retrieval, engagement, source updates), analysis queries, reporting
- Depends on: `DB` layer, numpy, optional sklearn/pandas/tabulate
- Used by: External RAG applications, demo scripts

**Analysis Layer:**
- Purpose: Implement corpus health detection and anomaly finding algorithms
- Location: `memento.py` (methods: `get_ghosts()`, `get_duplicates()`, `get_obsolete()`, `get_stale_embeddings()`, `get_suspects()`, `corpus_health()`)
- Contains: Statistical analysis, similarity computations, pattern matching
- Depends on: `DB` layer (read-only), numpy for vector operations
- Used by: Reporting layer and public API

**Persistence Layer:**
- Purpose: SQLite schema management and query execution
- Location: `db.py` (class `DB`)
- Contains: Schema definition, read/write methods, connection management
- Depends on: sqlite3 standard library
- Used by: API layer, analysis layer

**Ingestion Layer:**
- Purpose: Normalize incoming data from vector DB searches and user actions
- Location: `memento.py` (methods: `log_retrieval()`, `log_engagement()`, `log_source_update()`, `register_document()`)
- Contains: Data normalization, hashing (query hashing), vector serialization
- Depends on: `DB` layer
- Used by: External systems

**Reporting Layer:**
- Purpose: Format analysis results for human consumption
- Location: `memento.py` (methods: `report()`, `cleanup_report()`, `to_dataframe()`)
- Contains: Text formatting, table generation, prioritization logic
- Depends on: Analysis layer, optional tabulate/pandas
- Used by: End users, CLI output

## Data Flow

**Ingestion Flow:**

1. External RAG system calls `memento.log_retrieval(results, query)` with search results
2. `Memento` hashes query, normalizes each result item
3. For each result: `DB.upsert_document()` updates documents table, `DB.insert_retrieval()` records the search event
4. Optional: embeddings are converted from list/ndarray → numpy float32 bytes via `_vec_to_bytes()`
5. Data persisted atomically via `DB._conn()` context manager

**Engagement Flow:**

1. External system calls `memento.log_engagement(doc_id, event)`
2. `Memento` calls `DB.insert_engagement()` with current timestamp
3. Event type is free-form (e.g., "opened", "thumbs_up")

**Source Update Flow:**

1. External system notifies `memento.log_source_update(doc_id, updated_at)`
2. `Memento` calls `DB.update_source_timestamp()` to mark when source file changed
3. Used for detecting stale embeddings (embedding timestamp vs. source update timestamp)

**Analysis Flow:**

1. User calls `memento.get_ghosts()` (or other analysis method)
2. Query is filtered by time window: `_days_ago(threshold) = now - threshold * 86400`
3. Relevant rows fetched from DB via aggregation queries (e.g., `retrieval_counts(since=cutoff)`)
4. Python-side processing applies business logic (filtering, ranking, similarity checks)
5. Results returned as list[dict]

**State Management:**
- No in-memory state beyond initialization parameters (thresholds, patterns)
- All corpus state lives in SQLite: documents, retrievals, engagements
- Query-time aggregation (no materialized views or caching)
- Timestamps are unix seconds (float) throughout

## Key Abstractions

**Memento (Main Facade):**
- Purpose: Single entry point for RAG operators; combines ingestion, analysis, reporting
- Examples: `memento.py` class `Memento` (lines 59-516)
- Pattern: Facade pattern; initializes `DB` at construction; delegates to analysis methods

**DB (Persistence Abstraction):**
- Purpose: Hide SQLite details; provide schema versioning; manage connections safely
- Examples: `db.py` class `DB` (lines 37-126)
- Pattern: Repository pattern; contextmanager for connection lifecycle; schema in constants

**Query Hash:**
- Purpose: Anonymize and deduplicate user queries
- Examples: `_hash_query()` in `memento.py` (line 33)
- Pattern: Deterministic hashing; stores first 16 chars of SHA256; query deduplication happens at DB level

**Vector Serialization:**
- Purpose: Store embeddings as binary blobs without external storage
- Examples: `_vec_to_bytes()` and `_bytes_to_vec()` in `memento.py` (lines 47-52)
- Pattern: numpy float32 ↔ bytes conversion; enables duplicate detection without re-embedding

**Time Windows:**
- Purpose: Allow flexible time-based filtering (ghost detection, stale embeddings, etc.)
- Examples: `_days_ago()`, `_ts_to_date()` in `memento.py` (lines 37-44)
- Pattern: Epoch time (float seconds); relative calculations relative to `_now()`; configurable thresholds

## Entry Points

**Memento Constructor:**
- Location: `memento.py` lines 72-86
- Triggers: Called once per application to initialize analytics
- Responsibilities: Accept configuration (thresholds, patterns), initialize `DB`, store parameters

**log_retrieval():**
- Location: `memento.py` lines 90-124
- Triggers: Called immediately after vector DB search completes
- Responsibilities: Parse results list, upsert documents, insert retrieval events, optionally store embeddings

**log_engagement():**
- Location: `memento.py` lines 126-136
- Triggers: Called when user acts on a retrieved document
- Responsibilities: Insert engagement event with user-defined event type

**Analysis Methods (get_ghosts, get_duplicates, etc.):**
- Location: `memento.py` lines 169-313
- Triggers: Called ad-hoc or periodically for reporting
- Responsibilities: Query DB, apply filtering logic, return anomalies

**report() / cleanup_report():**
- Location: `memento.py` lines 394-515
- Triggers: Called to display results to user
- Responsibilities: Format analysis results as human-readable text/tables

## Error Handling

**Strategy:** Graceful degradation; optional dependencies handled via try/except

**Patterns:**
- sklearn unavailable: `get_duplicates()` raises RuntimeError with installation hint (lines 193-197)
- pandas unavailable: `to_dataframe()` raises RuntimeError with installation hint (lines 358-361)
- tabulate unavailable: `report()` falls back to simple text formatting (lines 501-509)
- Missing embedding data: Filtered out during analysis (lines 200-202, 272-273)
- Empty results: Return empty list; no exceptions
- Database I/O: Contextmanager ensures connections closed; sqlite3 exceptions propagate

## Cross-Cutting Concerns

**Logging:** No structured logging; demo.py uses print() for stdout feedback; production usage silent by default

**Validation:** Minimal input validation; trusts caller:
- `doc_id` assumed unique per document
- Embeddings assumed normalized (not checked)
- Query strings not validated; hashed as-is
- Timestamps assumed unix epoch; no conversion logic

**Authentication:** Not applicable; SQLite local file, no credentials

**Timestamps:** Consistent use of float seconds since epoch (`time.time()`):
- Retrieval logged with rank and cosine similarity score
- Engagement logged with event type
- Source updates logged to separate timestamp
- Analysis filters by absolute time (since=cutoff, where cutoff is float timestamp)

---

*Architecture analysis: 2026-03-24*
