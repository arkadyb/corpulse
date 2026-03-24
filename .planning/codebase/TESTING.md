# Testing Patterns

**Analysis Date:** 2026-03-24

## Test Framework

**Runner:**
- Not currently used — no test framework configured
- No pytest, unittest, or other test runner present

**Assertion Library:**
- Not applicable — no tests exist

**Run Commands:**
- Not established yet

## Test File Organization

**Location:**
- No test directory structure exists
- No `tests/` or `test_*.py` files present
- Recommended location: `tests/` directory at project root (parallel to source files)

**Naming:**
- Not established — no test files to reference

**Structure:**
- Recommended structure would be:
  ```
  tests/
  ├── test_memento.py        # Tests for Memento class
  ├── test_db.py             # Tests for DB class
  ├── fixtures/              # Test data/fixtures
  └── conftest.py            # Shared fixtures and pytest config
  ```

## Test Structure

**Demonstration via demo.py:**
The codebase includes `demo.py` which serves as a realistic integration scenario rather than a test suite. It:
- Creates a corpus with known problem types (ghosts, obsolete, duplicates, stale, low-engagement)
- Simulates retrieval and engagement patterns over 90 days
- Verifies analysis methods produce expected results
- Uses deterministic seeding: `random.seed(42)`, `np.random.seed(42)`

**Test data setup in demo.py:**
```python
DOCS = [
    ("doc_001", "onboarding-guide.md",      "onboarding",  True),
    ("doc_002", "api-reference-v2.md",      "api",         True),
    ("doc_003", "api-reference-v1.md",      "api",         True),   # obsolete
    # ... more docs
]

topic_vecs = {}
for _, _, topic, _ in DOCS:
    if topic not in topic_vecs:
        topic_vecs[topic] = rand_vec()

for doc_id, filename, topic, _ in DOCS:
    vec = near_vec(topic_vecs[topic], noise=0.03)
    memento.register_document(doc_id, filename, embedding=vec)
```

## Mocking

**Framework:**
- Not currently used
- No mock objects or fixtures configured

**Patterns Observed in Code:**
- Demo uses deterministic seeding for reproducible test scenarios
- DB operations wrapped in context manager for clean resource management:
  ```python
  @contextmanager
  def _conn(self):
      conn = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES)
      conn.row_factory = sqlite3.Row
      try:
          yield conn
          conn.commit()
      finally:
          conn.close()
  ```
- Optional dependencies gracefully handled with try/except guards

**Suggested Strategy for Future Tests:**
- Mock sklearn for testing duplicate detection without actual computation
- Mock file system by using in-memory SQLite (`:memory:`)
- Mock numpy arrays when testing vector operations
- Don't mock: core DB operations, list comprehensions, dict operations

**What to Mock:**
- External optional dependencies (sklearn, pandas, tabulate)
- File I/O operations
- Time-based operations (use mock for `time.time()`)

**What NOT to Mock:**
- Core Memento/DB classes (these should be integration tested)
- Data transformation logic
- Analysis algorithms

## Fixtures and Factories

**Test Data Pattern from demo.py:**
```python
def rand_vec(dim=64):
    v = np.random.randn(dim).astype(np.float32)
    return v / np.linalg.norm(v)

def near_vec(base, noise=0.05):
    v = base + np.random.randn(len(base)).astype(np.float32) * noise
    return v / np.linalg.norm(v)

def days_ago(n):
    return time.time() - n * 86_400
```

**Location:**
- Currently in `demo.py` (lines 27-37)
- Suggested location for tests: `tests/fixtures.py` or `tests/conftest.py`

**Recommended Factory Pattern:**
```python
# tests/factories.py
def create_memento(db_path=":memory:"):
    return Memento(
        db_path=db_path,
        ghost_threshold_days=30,
        duplicate_threshold=0.92,
    )

def create_test_documents(n=5, with_embeddings=True):
    docs = []
    for i in range(n):
        doc = {
            "doc_id": f"doc_{i:03d}",
            "filename": f"file_{i}.md",
        }
        if with_embeddings:
            doc["embedding"] = rand_vec(64)
        docs.append(doc)
    return docs
```

## Coverage

**Requirements:** Not enforced

**View Coverage:**
- No coverage configuration present
- Would use pytest-cov: `pytest --cov=rag_memento --cov-report=html`

**Recommended coverage targets:**
- Core Memento methods: >80%
- Analysis methods (get_ghosts, get_duplicates, etc.): >85%
- DB layer: >90%
- Helper functions: >70%

## Test Types

**Unit Tests:**
- Scope: Individual methods of `Memento` and `DB`
- Approach: Isolate one function at a time, use fixtures for test data
- Example test structure:
  ```python
  def test_get_ghosts():
      memento = create_memento()
      memento.register_document("doc_1", "file1.md")
      ghosts = memento.get_ghosts()
      assert len(ghosts) == 1
      assert ghosts[0]["doc_id"] == "doc_1"
  ```

**Integration Tests:**
- Scope: Full retrieval→analysis workflows
- Approach: Use demo.py as reference; create complete scenarios
- Example structure:
  ```python
  def test_obsolete_detection_workflow():
      memento = create_memento()
      # Register versioned docs
      memento.register_document("doc_v1", "api-v1.md")
      memento.register_document("doc_v2", "api-v2.md")
      # Simulate retrievals
      memento.log_retrieval([{"doc_id": "doc_v2", "score": 0.95}])
      obsolete = memento.get_obsolete()
      assert any(d["doc_id"] == "doc_v1" for d in obsolete)
  ```

**E2E Tests:**
- Framework: Not currently used
- Suggested approach: Use demo.py as baseline; could extend to test CLI/output formatting

## Common Patterns

**Test Data Setup:**
- Use deterministic seeding for reproducibility
- Create minimal fixture scenarios (3-5 documents)
- Use meaningful doc_id/filename pairs that reflect what's being tested

**Async Testing:**
- Not applicable — codebase is synchronous

**Error Testing:**
```python
# Pattern for testing error cases
def test_duplicate_detection_requires_sklearn(memento, monkeypatch):
    monkeypatch.setattr("memento._SKLEARN", False)
    with pytest.raises(RuntimeError) as exc_info:
        memento.get_duplicates()
    assert "scikit-learn is required" in str(exc_info.value)
```

**Database Testing:**
```python
# Use in-memory SQLite for fast, isolated tests
def test_db_operations():
    db = DB(":memory:")
    db.upsert_document("doc_1", "file.md")
    docs = db.all_documents()
    assert len(docs) == 1
    assert docs[0]["doc_id"] == "doc_1"
```

**Timestamp Testing:**
```python
# Mock time for reproducible results
def test_ghost_detection_timing(memento, freezegun):
    freezegun.move_to("2026-03-24")
    memento.register_document("doc_1", "file.md")
    freezegun.move_to("2026-04-24")  # Move forward 30 days

    ghosts = memento.get_ghosts(threshold_days=30)
    assert len(ghosts) == 1
```

---

*Testing analysis: 2026-03-24*

## Notes on Test Implementation Gaps

The codebase currently has zero automated tests. The `demo.py` file serves as a manual test/validation script. Key areas needing test coverage:

1. **Duplicate detection algorithm** — complex cosine similarity logic with matrix operations
2. **Obsolete version detection** — regex matching and version number extraction
3. **Stale embedding detection** — timestamp comparisons across different update times
4. **Corpus health scoring** — aggregation of multiple factors with edge cases
5. **DataFrame export** — data transformation and status categorization
6. **Edge cases** — empty corpus, single document, all ghosts, etc.
7. **Optional dependency handling** — graceful degradation when sklearn/pandas missing
