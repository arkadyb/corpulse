# Technology Stack

**Analysis Date:** 2026-03-24

## Languages

**Primary:**
- Python 3.7+ - Core library and analysis framework
- SQL - SQLite database schema and queries

## Runtime

**Environment:**
- Python 3.7 or higher (based on modern type hints in code)

**Package Manager:**
- pip - Standard Python package manager
- Lockfile: Not detected (no requirements.txt, setup.py, pyproject.toml, or poetry.lock found)

## Frameworks

**Core:**
- NumPy 1.x - Numeric computations, vector operations for embedding similarity
- SQLite 3 - Embedded database for tracking retrievals and engagements

**Optional/Conditional:**
- scikit-learn - Optional dependency for cosine similarity calculations in duplicate detection
- pandas - Optional dependency for DataFrame export in reporting
- tabulate - Optional dependency for formatted table output in reports

**Testing:**
- Not detected

**Build/Dev:**
- Not detected

## Key Dependencies

**Critical:**
- numpy - Required for vector operations, embedding storage/conversion between bytes and arrays
  - Used in `memento.py`: embedding serialization, cosine similarity computation
  - Used in `demo.py`: vector generation and normalization

**Infrastructure:**
- sqlite3 - Built-in Python module, no external dependency required
  - Used in `db.py`: entire database layer, connection management, schema execution
  - Implements connection pooling via context managers

**Optional but Strongly Recommended:**
- scikit-learn - Enables duplicate detection via cosine_similarity
  - Only imported and used when `get_duplicates()` is called
  - Raises clear error if missing: "scikit-learn is required for duplicate detection"
- pandas - Enables DataFrame export capability
  - Only imported when `to_dataframe()` is called
  - Raises clear error if missing: "pip install pandas to use to_dataframe()"
- tabulate - Enables formatted table output in corpus health reports
  - Gracefully falls back to plain text formatting if missing

## Configuration

**Environment:**
- No environment variables required
- All configuration via constructor parameters to `Memento()` class
- Database path configurable via `db_path` parameter (defaults to `./memento.db`)

**Build:**
- No build configuration files detected
- Pure Python, no compilation or build step required

**Key Configuration Parameters:**
- `db_path` - SQLite database file location (default: `"./memento.db"`)
- `ghost_threshold_days` - Days of inactivity before doc flagged as ghost (default: 30)
- `duplicate_threshold` - Cosine similarity threshold for duplicate detection (default: 0.92)
- `stale_threshold_days` - Days between source update and embedding before flagged stale (default: 14)
- `obsolete_pattern` - Regex pattern for version detection (default: `r"v\d+"`)
- `top_k_report` - Number of top documents shown in report (default: 20)

## Platform Requirements

**Development:**
- Python 3.7+
- pip for package management
- Access to filesystem for SQLite database creation
- NumPy for core functionality

**Production:**
- Python 3.7+ runtime
- NumPy installed
- Writable filesystem for SQLite database (`.db` file)
- Optional: scikit-learn, pandas, tabulate for full feature set

**No External Services Required:**
- Zero cloud dependencies
- Entirely self-contained SQLite storage
- All computations local

---

*Stack analysis: 2026-03-24*
