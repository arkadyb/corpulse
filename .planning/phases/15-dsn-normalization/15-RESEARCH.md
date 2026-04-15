# Phase 15: DSN Normalization - Research

**Researched:** 2026-04-15
**Domain:** Postgres DSN handling for sync (`psycopg` / `psycopg_pool`) and async (`asyncpg`) backends
**Confidence:** HIGH

## Summary

This phase adds a small, internal DSN normalization helper that lets both `PostgresBackend` (sync, built on `psycopg_pool.ConnectionPool`) and `AsyncPostgresBackend` (async, built on `asyncpg.create_pool`) accept SQLAlchemy-style DSNs such as `postgresql+psycopg://...` or `postgresql+asyncpg://...`. Neither underlying driver understands the `+driver` qualifier — `psycopg` and `asyncpg` both parse libpq-style URIs (`postgresql://` / `postgres://`) only. The normalization must strip the `+driver` segment and hand the cleaned DSN down to the driver, with plain DSNs passing through unchanged byte-for-byte. [VERIFIED: codebase grep — `postgres.py:64`, `postgres_async.py:43`]

No new dependencies are needed. The helper is trivially implementable with the standard library (`urllib.parse.urlsplit` / `urlunsplit` or, even simpler, a targeted string replacement on the scheme prefix). The primary risk is over-engineering: the helper must leave userinfo (URL-encoded credentials), query parameters, IPv6 host brackets, and non-URL formats (key=value libpq conninfo strings) untouched. The second risk is asymmetry — both backends must share the same helper so sync/async behavior matches per DSN-03.

**Primary recommendation:** Add a single pure function `_normalize_postgres_dsn(dsn: str) -> str` in a shared location (`corpulse/backends/_dsn.py`), call it from `PostgresBackend.__init__` and `AsyncPostgresBackend.create` immediately before passing the DSN to the driver, and cover both backends with parametrized unit tests that assert identical normalization and passthrough behavior.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| DSN normalization | Backend (shared helper module) | — | Pure string transform; lives alongside backends so both sync/async import it |
| DSN consumption (pool creation) | Backend (per-driver) | — | Each backend still owns its own driver-specific pool construction; the normalizer is a thin pre-step |

## Standard Stack

### Core (already in use — unchanged)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `psycopg` + `psycopg_pool` | already declared in `corpulse[postgres]` extra | Sync pool + driver | Current sync backend uses these directly [VERIFIED: `postgres.py:46-57`] |
| `asyncpg` | already declared in `corpulse[postgres-async]` extra | Async pool + driver | Current async backend uses `asyncpg.create_pool` [VERIFIED: `postgres_async.py:17-43`] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `urllib.parse` | stdlib | Parse/reassemble URI scheme | If we choose URL-aware normalization over prefix replacement |

**No new installs.** [VERIFIED: this is an internal normalization, not a parser or new integration.]

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled prefix strip | `sqlalchemy.engine.url.make_url` | Drags in a heavy runtime dep for a one-line transform; rejected |
| Two separate helpers (one per backend) | One shared helper | Shared helper is required by DSN-03 (identical behavior); rejected duplication |

## Architecture Patterns

### System Architecture Diagram

```
caller supplies DSN
       │
       ▼
 PostgresBackend.__init__        AsyncPostgresBackend.create
       │                                  │
       ▼                                  ▼
 _normalize_postgres_dsn(dsn) ◀── shared ──▶ _normalize_postgres_dsn(dsn)
       │                                  │
       ▼                                  ▼
 psycopg_pool.ConnectionPool(      asyncpg.create_pool(
   conninfo=normalized, …)           normalized, …)
       │                                  │
       ▼                                  ▼
     pool ready                        pool ready
```

The normalizer is a pure function between the caller boundary and the driver boundary. It never opens connections, never imports drivers, and produces identical output for identical input across both backends.

### Recommended Project Structure
```
corpulse/backends/
├── _dsn.py          # NEW: _normalize_postgres_dsn + constants
├── postgres.py      # calls _normalize_postgres_dsn before ConnectionPool(...)
├── postgres_async.py # calls _normalize_postgres_dsn before asyncpg.create_pool(...)
└── ...
```

Filename is leading-underscore to signal "internal, not part of the public backends surface." Both postgres modules already co-locate; adding a sibling keeps the import graph flat and avoids leaking into `corpulse.backends.__init__` re-exports.

### Pattern 1: Driver-Qualifier Strip
**What:** Detect `postgresql+<driver>://` or `postgres+<driver>://` at the start of a DSN and replace the scheme with the bare `postgresql://` (or `postgres://`). Leave everything after the `://` byte-for-byte identical.
**When to use:** On every DSN passed into either backend, before the driver sees it.
**Example:**
```python
# corpulse/backends/_dsn.py
_SCHEME_PREFIXES = ("postgresql+", "postgres+")

def _normalize_postgres_dsn(dsn: str) -> str:
    """Strip SQLAlchemy-style '+driver' qualifier from Postgres URIs.

    Plain DSNs (including libpq key=value conninfo strings) pass through
    unchanged. Only the scheme segment is touched; userinfo, host, path,
    and query are preserved byte-for-byte.
    """
    for prefix in _SCHEME_PREFIXES:
        if dsn.startswith(prefix):
            base = prefix[:-1]  # drop the trailing '+'
            rest = dsn[len(prefix):]
            # rest starts with '<driver>://...' — skip driver name up to '://'
            sep = rest.find("://")
            if sep == -1:
                return dsn  # malformed; leave alone
            return f"{base}://{rest[sep + 3:]}"
    return dsn
```

### Anti-Patterns to Avoid
- **Parsing with `urllib.parse.urlsplit` then rebuilding:** Round-tripping through `urlsplit`/`urlunsplit` can re-encode userinfo or drop empty components, breaking byte-for-byte passthrough. Prefer targeted prefix surgery.
- **Regex with `re.sub` on the whole string:** Easy to accidentally match `+asyncpg` inside a password or query value. Anchor to the start only, or do prefix checks as above.
- **Calling the normalizer inside the driver error path or retry loop:** It must run exactly once, at construction time.
- **Exposing it as public API:** Keep it underscore-prefixed; the contract is "DSN in, DSN out," not a stable surface.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Full URI parsing/rewriting | Custom URI parser | `urllib.parse` (stdlib) if needed | But for this phase, prefix strip is enough — full parsing is overkill |
| SQLAlchemy DSN compatibility layer | Our own DSN dialect registry | Just strip the qualifier | We only need the `+driver` suffix stripped; we don't need dialect awareness |

**Key insight:** The goal is maximal conservatism. Any DSN the driver already accepts must reach the driver unchanged. Only the narrow `scheme+driver://` case needs rewriting.

## Runtime State Inventory

This is a greenfield helper addition. No rename, no migration, no stored state touches.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no schema or data changes | None |
| Live service config | None — no external services | None |
| OS-registered state | None | None |
| Secrets/env vars | `CORPULSE_POSTGRES_TEST_CONNINFO` already used in live tests [VERIFIED: `conftest.py:24`, `test_postgres_backend.py:268`] — key name unchanged; value format unchanged | None (optional: document that users may now set a `postgresql+psycopg://...` value) |
| Build artifacts | None | None |

## Common Pitfalls

### Pitfall 1: URL-Encoded Credentials Get Mangled
**What goes wrong:** A password like `p@ss%3Aword` (percent-encoded `:`) gets re-encoded or decoded if you round-trip through `urlsplit`/`urlunsplit`.
**Why it happens:** `urllib.parse` normalizes some components.
**How to avoid:** Use direct string slicing at the `://` boundary instead of full URL parsing. Add a test with percent-encoded userinfo.
**Warning signs:** Tests fail with "password authentication failed" when DSN contained `%` or `@` inside the password.

### Pitfall 2: IPv6 Host Brackets
**What goes wrong:** `postgresql+asyncpg://user:pw@[::1]:5432/db` — careless regex can strip the brackets.
**Why it happens:** `[` and `]` are URI-reserved but commonly look like character classes.
**How to avoid:** Do not regex-walk the host. The prefix-strip approach only touches bytes before `://`, so IPv6 is safe by construction. Add a test to prove it.
**Warning signs:** Connection refused to IPv6 host after normalization.

### Pitfall 3: Query Parameters with `+driver`-Looking Substrings
**What goes wrong:** A DSN with `?options=postgresql+something` in the query gets over-matched by a naive `replace`.
**How to avoid:** Anchor the match to `startswith(...)` at the scheme position only. Never use `str.replace` on the full DSN.
**Warning signs:** Query param values mutate unexpectedly.

### Pitfall 4: libpq key=value Conninfo Strings
**What goes wrong:** `psycopg` accepts not just URIs but also `host=localhost port=5432 dbname=foo user=bar`. A naive normalizer that assumes URI shape will either crash or corrupt these.
**Why it happens:** The sync backend's `conninfo` parameter supports both forms [CITED: psycopg docs — conninfo accepts URI or keyword form].
**How to avoid:** The prefix check (`startswith("postgresql+")` / `startswith("postgres+")`) falls through to "return unchanged" for anything that doesn't match, including key=value conninfo. Add a test proving passthrough.
**Warning signs:** Sync backend starts failing for consumers that were using key=value conninfo.

### Pitfall 5: Scheme Case Sensitivity
**What goes wrong:** `POSTGRESQL+ASYNCPG://` — libpq/asyncpg URIs are technically case-insensitive in scheme per RFC 3986.
**How to avoid:** Decide: either normalize case-sensitively only (document the contract: "lowercase `postgresql+` or `postgres+` required") or lowercase-compare the prefix. Recommendation: match only lowercase prefixes; SQLAlchemy itself produces lowercase. This is consistent with least-surprise — if the driver didn't accept an uppercase scheme before, we shouldn't either.
**Warning signs:** Mixed-case SQLAlchemy-style DSNs silently pass through un-normalized and then fail at the driver.

### Pitfall 6: Asymmetry Between Backends
**What goes wrong:** Sync and async normalize differently, so the same DSN behaves differently depending on which backend consumes it. This directly violates DSN-03.
**How to avoid:** Single shared helper. Parametrize a test that runs identical inputs through both call sites and asserts the DSN handed to the (mocked) pool constructor is identical.
**Warning signs:** A DSN works against `AsyncPostgresBackend` but not `PostgresBackend` (or vice versa).

## Code Examples

### Applying the normalizer in `PostgresBackend.__init__`
```python
# corpulse/backends/postgres.py
from ._dsn import _normalize_postgres_dsn

class PostgresBackend(StorageBackend):
    def __init__(self, conninfo: str, *, min_size: int = 1, max_size: int = 10):
        connection_pool, dict_row, error_cls = _load_psycopg_pool()
        self._error_cls = error_cls
        self._pool = connection_pool(
            conninfo=_normalize_postgres_dsn(conninfo),
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        ...
```

### Applying the normalizer in `AsyncPostgresBackend.create`
```python
# corpulse/backends/postgres_async.py
from ._dsn import _normalize_postgres_dsn

@classmethod
async def create(cls, dsn: str, *, min_size: int = 2, max_size: int = 10):
    asyncpg, error_cls = _load_asyncpg()
    pool = await asyncpg.create_pool(
        _normalize_postgres_dsn(dsn),
        min_size=min_size,
        max_size=max_size,
    )
    ...
```

### Test pattern (mirrors existing style)
The existing tests mock `_load_psycopg_pool` / `_load_asyncpg` and capture the `conninfo` / `dsn` the fake pool receives [VERIFIED: `test_postgres_backend.py:97-105`, `test_async_postgres_backend.py:106-117`]. New DSN tests slot directly into this pattern:

```python
@pytest.mark.parametrize("input_dsn,expected", [
    ("postgresql://u:p@h/db",                "postgresql://u:p@h/db"),           # passthrough
    ("postgres://u:p@h/db",                  "postgres://u:p@h/db"),             # passthrough short form
    ("postgresql+psycopg://u:p@h/db",        "postgresql://u:p@h/db"),           # DSN-02 sync qualifier
    ("postgresql+psycopg2://u:p@h/db",       "postgresql://u:p@h/db"),           # DSN-02 legacy qualifier
    ("postgresql+asyncpg://u:p@h/db",        "postgresql://u:p@h/db"),           # DSN-01
    ("postgres+asyncpg://u:p@h/db",          "postgres://u:p@h/db"),             # short scheme + qualifier
    ("postgresql+asyncpg://u:p%40x@h/db?sslmode=require",
                                             "postgresql://u:p%40x@h/db?sslmode=require"),  # preserve userinfo/query
    ("postgresql+asyncpg://u@[::1]:5432/db", "postgresql://u@[::1]:5432/db"),    # IPv6
    ("host=localhost port=5432 dbname=foo",  "host=localhost port=5432 dbname=foo"),  # libpq key=value passthrough
])
def test_normalize_postgres_dsn(input_dsn, expected):
    assert _normalize_postgres_dsn(input_dsn) == expected
```

Plus integration-level assertions at both backends that prove the normalized string is what actually reaches the pool factory (DSN-03 symmetry).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Reject `+driver` DSNs (current behavior — drivers error) | Strip `+driver`, pass rest through | This phase | Users can paste SQLAlchemy DSNs directly |

**Not deprecating anything.** Plain DSNs (`postgresql://...`, `postgres://...`, libpq key=value) remain first-class and unchanged.

## Driver Qualifiers In Scope

| Qualifier | Target Backend | Notes |
|-----------|----------------|-------|
| `postgresql+psycopg://` | Sync (`PostgresBackend`) | Modern psycopg 3 dialect name [CITED: SQLAlchemy docs — dialect/driver table] |
| `postgresql+psycopg2://` | Sync (`PostgresBackend`) | Legacy but still common; users may paste it |
| `postgresql+asyncpg://` | Async (`AsyncPostgresBackend`) | Primary target of DSN-01 |
| `postgresql+pg8000://` | Either (rare) | Strip and pass through for consistency — neither backend uses pg8000, but the normalizer should not special-case drivers; users will see a connection error if they point a non-matching driver DSN at a backend, which is the expected behavior |
| `postgres+*://` (short form) | Either | Same treatment — short scheme is also accepted by libpq |

**Recommended contract:** The normalizer does NOT validate that the qualifier matches the backend. It blindly strips any `+<driver>` segment. If a user aims `postgresql+psycopg://` at `AsyncPostgresBackend`, normalization succeeds and the connection attempt proceeds against asyncpg — which is identical to what would happen with a plain `postgresql://` DSN. This keeps the helper dumb and predictable. [ASSUMED — see Assumptions Log A1]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Normalizer should not reject mismatched driver/backend combos (e.g., `+psycopg` aimed at async backend) | Driver Qualifiers In Scope | Low. If stakeholders want strict validation, add a backend-specific allowlist check that raises `ValueError` on mismatch. Easy to add later; harder to remove once users depend on lenient behavior. Worth confirming in discuss phase. |
| A2 | Case-sensitive prefix match is preferred (only lowercase `postgresql+` / `postgres+`) | Pitfall 5 | Low. Uppercase SQLAlchemy DSNs are virtually nonexistent in practice, but could surprise a user. Could add case-insensitive match with minimal cost. |
| A3 | Helper lives at `corpulse/backends/_dsn.py` (underscore-private, not re-exported) | Recommended Project Structure | None functionally; purely an organization choice. |

## Open Questions

1. **Should the normalizer log when it rewrites a DSN?**
   - What we know: Current backends do no logging at construction.
   - What's unclear: Whether a debug-level log ("normalized SQLAlchemy-style DSN") adds value.
   - Recommendation: Skip logging in this phase. Keep the helper pure. Revisit only if debugging requires it.

2. **Should we strip qualifiers inside a broader URI parsing step (e.g., for future DSN-aware features like tenant extraction)?**
   - What we know: Phase 16 adds `schema` and `table_prefix` as explicit kwargs, not DSN-embedded [VERIFIED: REQUIREMENTS.md PGMT-01/02].
   - What's unclear: Whether future phases will want to read DSN query params.
   - Recommendation: YAGNI. Implement the minimal strip now. If future phases need parsed DSN components, add a `_parse_postgres_dsn` sibling then.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured; async via pytest-asyncio auto-mode based on existing async tests) |
| Config file | `pyproject.toml` (standard) |
| Quick run command | `pytest tests/test_postgres_backend.py tests/test_async_postgres_backend.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| DSN-01 | `AsyncPostgresBackend.create()` normalizes `postgresql+asyncpg://...` before `asyncpg.create_pool` | unit (fake pool captures DSN) | `pytest tests/test_async_postgres_backend.py -k dsn_normalization -x` | ✅ existing test file; add new tests |
| DSN-02 | `PostgresBackend.__init__` normalizes `postgresql+psycopg://...` and `+psycopg2` before `ConnectionPool` | unit (fake pool captures conninfo) | `pytest tests/test_postgres_backend.py -k dsn_normalization -x` | ✅ existing test file; add new tests |
| DSN-03 | Passthrough + normalized DSNs produce identical behavior across sync and async | unit (parametrized table of inputs, asserted against both call sites' captured DSN) | `pytest tests/test_dsn_normalization.py -x` (new file) OR parametrize in both existing files | ❌ Wave 0: new test file or additions |

### Sampling Rate
- **Per task commit:** `pytest tests/test_postgres_backend.py tests/test_async_postgres_backend.py tests/test_dsn_normalization.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_dsn_normalization.py` — pure unit tests of `_normalize_postgres_dsn` with the parametrized table above (covers DSN-03 directly and supports DSN-01/02)
- [ ] New test cases in `tests/test_postgres_backend.py` — assert that when constructed with `postgresql+psycopg://example`, the fake pool factory receives `postgresql://example` (covers DSN-02 end-to-end through the backend)
- [ ] New test cases in `tests/test_async_postgres_backend.py` — assert that when `AsyncPostgresBackend.create("postgresql+asyncpg://test")` runs, `fake_module.create_pool_calls[0]["dsn"] == "postgresql://test"` (covers DSN-01 end-to-end)
- [ ] No framework install needed — pytest and pytest-asyncio already in use

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DSN-01 | `AsyncPostgresBackend.create()` accepts SQLAlchemy-style DSNs such as `postgresql+asyncpg://...` by normalizing them before pool creation. | Covered by shared `_normalize_postgres_dsn` applied at `postgres_async.py:43` before `asyncpg.create_pool`. Existing fake-pool test harness captures the DSN argument [VERIFIED: `test_async_postgres_backend.py:94-103`], so adding a normalization assertion is a 1-line extension. |
| DSN-02 | `PostgresBackend` accepts equivalent normalized DSN variants for symmetry with the async backend. | Same helper applied at `postgres.py:64` before `ConnectionPool(...)`. Existing fake pool factory captures `conninfo` as first positional arg [VERIFIED: `test_postgres_backend.py:90-94`]. |
| DSN-03 | Tests prove passthrough and normalized DSN forms behave identically. | Parametrized table of inputs/expected outputs in a new `tests/test_dsn_normalization.py`, plus paired assertions in each backend test file that the value captured by the fake pool equals the expected normalized form. The single shared helper guarantees identical logic; the paired assertions guarantee no one accidentally forgets to call it. |

## Sources

### Primary (HIGH confidence)
- Codebase: `corpulse/backends/postgres.py` — sync backend structure, `ConnectionPool(conninfo=...)` call site
- Codebase: `corpulse/backends/postgres_async.py` — async backend structure, `asyncpg.create_pool(dsn, ...)` call site
- Codebase: `tests/test_postgres_backend.py` — fake pool factory pattern that captures `conninfo`
- Codebase: `tests/test_async_postgres_backend.py` — fake asyncpg module pattern that captures `dsn`
- Codebase: `tests/conftest.py` — live-Postgres opt-in via `CORPULSE_POSTGRES_TEST_CONNINFO`
- `.planning/REQUIREMENTS.md` — DSN-01/02/03 acceptance criteria
- `.planning/STATE.md` — Phase 14 decisions (AsyncCorpulse as structured-return API; no conflicting choices for Phase 15)

### Secondary (MEDIUM confidence)
- SQLAlchemy dialect/driver naming convention (`postgresql+psycopg`, `postgresql+asyncpg`, `postgresql+psycopg2`, `postgresql+pg8000`) [CITED: SQLAlchemy PostgreSQL dialect documentation]
- psycopg `conninfo` accepts both URI and key=value forms [CITED: psycopg 3 documentation]

### Tertiary (LOW confidence)
- None. This phase is fully grounded in the codebase and stdlib.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; both existing backends inspected end-to-end.
- Architecture: HIGH — shared-helper pattern is the only sensible shape given DSN-03.
- Pitfalls: HIGH — the five enumerated pitfalls are concrete failure modes provable with unit tests.
- Test strategy: HIGH — existing fake-pool harnesses already capture the exact value we need to assert on.

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable; only at risk if asyncpg or psycopg change their URI parsing, which is rare)
