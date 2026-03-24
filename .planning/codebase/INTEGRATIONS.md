# External Integrations

**Analysis Date:** 2026-03-24

## APIs & External Services

**No external APIs required:**
- rag-memento is self-contained with zero external service dependencies
- All features work offline and locally
- Designed as a wrapper around existing RAG pipelines, not dependent on them

**Optional Future Integrations (mentioned in README):**
- Chroma - Vector database integration helper (not implemented yet)
- Qdrant - Vector database integration helper (not implemented yet)
- LlamaIndex - Callback handler integration (not implemented yet)
- LangChain - Retriever wrapper integration (not implemented yet)
- Generic support for any vector store via `log_retrieval()` method

## Data Storage

**Databases:**
- SQLite 3 (local file-based)
  - Connection: File path specified via `db_path` parameter to `Memento()` class
  - Default location: `./memento.db`
  - Schema location: `db.py` lines 6-34
  - Client: Built-in Python `sqlite3` module (no ORM)

**Schema Details:**
- `documents` table - Stores document metadata, embeddings (as BLOB), timestamps
- `retrievals` table - Stores search results, query hashes, ranks, scores, timestamps
- `engagements` table - Stores user interaction events with timestamps
- Indexes on `doc_id` and `retrieved_at` for query optimization

**File Storage:**
- Local filesystem only
- SQLite database file written to disk at configured path
- No cloud storage, no object storage services

**Caching:**
- SQLite in-process caching via connection context managers (`db.py` lines 47-55)
- No external cache services (Redis, Memcached, etc.)
- No application-level caching layer

## Authentication & Identity

**Auth Provider:**
- Not applicable - rag-memento is a library, not a service
- No authentication mechanisms implemented
- No user identity tracking
- Assumes it runs in a trusted environment (same Python process as RAG pipeline)

## Monitoring & Observability

**Error Tracking:**
- None detected
- Errors are Python exceptions raised inline

**Logs:**
- No logging framework configured
- Console output only via `print()` statements in report methods
- No structured logging or log levels

**Observability Patterns:**
- Explicit query/report methods return dictionaries and DataFrames for external logging
- Users responsible for capturing and storing results externally

## CI/CD & Deployment

**Hosting:**
- Not applicable - rag-memento is a library, not a deployed service
- Intended for installation via pip in client applications
- Runs in the same process as the consuming RAG application

**CI Pipeline:**
- Not detected
- No GitHub Actions, GitLab CI, or other pipeline configuration files
- No test automation infrastructure found

## Environment Configuration

**Required env vars:**
- None - All configuration is code-based

**Optional env vars:**
- None - Configuration happens through Memento constructor parameters

**Secrets location:**
- No secrets management
- No API keys or credentials required
- Database file is local (no remote auth)

## Webhooks & Callbacks

**Incoming:**
- None - rag-memento is a library, not a server

**Outgoing:**
- No webhook support
- Integration pattern is imperative (direct method calls) rather than event-driven
- User code directly calls:
  - `memento.log_retrieval()` after vector search
  - `memento.log_engagement()` when user interacts with results
  - `memento.report()` or `memento.get_*()` methods to retrieve analysis

## Data Flow

**Typical Integration Pattern:**

1. Application calls `Memento()` constructor, specifying db_path
2. Application calls `memento.log_retrieval(results, query)` after vector search
3. Application calls `memento.log_engagement(doc_id, event)` on user interaction
4. Optional: Application calls `memento.log_source_update(doc_id)` when corpus changes
5. Application calls `memento.report()` or specific `memento.get_*()` methods for analysis
6. All data persisted to local SQLite database

**No network communication at any step.**

## Vector Store Independence

**How it works:**
- rag-memento accepts search results in a standard format (list of dicts)
- Each result dict must contain at minimum a `doc_id` key
- Optional fields: `filename`, `score`, `embedding` (list or numpy array)
- Embedding vectors stored as binary blobs (NumPy float32 serialization)

**Supported Vector Stores:**
- Any store whose results can be formatted as `{"doc_id": str, ...}` dict
- Chroma, Qdrant, Weaviate, Milvus, Pinecone, etc. via adapter code
- Custom implementations by reformatting search results

---

*Integration audit: 2026-03-24*
