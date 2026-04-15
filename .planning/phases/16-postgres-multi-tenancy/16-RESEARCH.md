# Phase 16: Postgres Multi-Tenancy - Research

**Researched:** 2026-04-15
**Domain:** Tenant-scoped Postgres storage for sync (`psycopg_pool`) and async (`asyncpg`) corpulse backends
**Confidence:** HIGH

## Summary

Phase 16 is a Postgres-only refactor that removes hardcoded table names from both storage backends and replaces them with validated schema-aware and prefix-aware naming. Today `PostgresBackend` owns a static `SCHEMA` string and every DML query targets bare `documents`, `retrievals`, and `engagements`; `AsyncPostgresBackend` imports that same static schema and mirrors the hardcoded names. This blocks multi-tenant use on a shared database because callers cannot isolate tenants by schema or table namespace. [VERIFIED: `corpulse/backends/postgres.py`, `corpulse/backends/postgres_async.py`]

The correct fix is to keep tenancy concerns local to the Postgres implementations rather than push them into the generic `StorageBackend` contract. Both backends should accept optional constructor parameters `schema: str | None = None` and `table_prefix: str = ""`, validate both against a strict Postgres identifier regex, and resolve all table/index references through a shared helper layer. DDL should be generated from a public `build_schema_sql(schema=None, prefix="")` helper so consumers can pre-provision tenant schemas out-of-band, and the async backend should import that helper rather than split a static constant.

**Primary recommendation:** build the tenancy naming primitives in `corpulse/backends/postgres.py` and reuse them from the async backend. Split execution into three waves: shared identifier/DDL generation, sync+async query rewiring, then coverage for invalid identifiers and isolation semantics.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Identifier validation | Postgres backend helpers | — | Validation is Postgres-specific and should not leak into non-SQL backends |
| DDL generation | Shared Postgres helper | Async backend consumer | One source of truth keeps sync and async schema creation identical |
| Qualified table resolution | Per-backend instance helper | Shared name builder | Each backend needs `self._t(...)` for query assembly |
| Tenant isolation tests | Backend test suites | Live Postgres env if available | Existing tests already own fake/live backend behavior |

## Current Constraints

### Existing sync backend shape

- `PostgresBackend.__init__(conninfo, *, min_size=1, max_size=10)` has no tenancy knobs.
- `_init()` executes a module-level `SCHEMA` string once.
- Every query hardcodes bare table names.

### Existing async backend shape

- `AsyncPostgresBackend.create(dsn, *, min_size=2, max_size=10)` has no tenancy knobs.
- `_initialize()` imports `SCHEMA` from the sync module and splits it into statements.
- Every query hardcodes bare table names.

### Consequence

Adding only constructor params is not enough. The refactor must cover:
- DDL table names
- index names
- every DML/SELECT/DELETE statement
- schema bootstrap ordering
- validation before SQL execution

## Recommended Design

### Pattern 1: Shared identifier validation

Use a strict regex for both `schema` and `table_prefix`:

```python
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
```

Rules:
- `schema=None` is allowed and means use the default schema
- `table_prefix=""` is allowed and means no prefix
- non-empty `schema` and `table_prefix` must match the regex exactly
- invalid values raise `ValueError` before any driver SQL executes

Rationale:
- table and schema names are interpolated into SQL identifiers, so parameter binding cannot protect them
- the strict regex gives a safe interpolation surface without quoting complexity

### Pattern 2: Shared qualified-name builder

Keep a helper that resolves tenant-safe table names from logical names:

```python
def _table_name(name: str, *, prefix: str = "") -> str:
    return f"{prefix}{name}"


def _qualified_name(name: str, *, schema: str | None = None, prefix: str = "") -> str:
    table = _table_name(name, prefix=prefix)
    return f"{schema}.{table}" if schema else table
```

Each backend instance should expose:

```python
def _t(self, name: str) -> str:
    return _qualified_name(name, schema=self._schema, prefix=self._table_prefix)
```

This keeps query rewrites mechanical and auditable.

### Pattern 3: Public DDL builder

Expose:

```python
def build_schema_sql(schema: str | None = None, prefix: str = "") -> str:
    ...
```

Behavior:
- validates `schema` and `prefix`
- emits `CREATE SCHEMA IF NOT EXISTS <schema>;` first when schema is set
- emits table and index DDL using qualified table names and prefixed index names
- remains backward-compatible when called with defaults

Important implementation note:
- prefixed index names must also change, otherwise prefix-only mode collides in one schema
- async initialization should consume this helper directly rather than import a stale constant

## API Boundary Decision

Do **not** add `schema` or `table_prefix` to `StorageBackend` in `corpulse/backends/base.py`.

Why:
- tenancy configuration is constructor-time backend wiring, not a storage operation contract
- the base interface currently describes CRUD/query behavior, not backend provisioning knobs
- pushing Postgres-specific construction concerns into every backend would add fake complexity with no benefit

The phase can still touch `base.py` only if a small docstring note is helpful, but no interface expansion is needed.

## Test Strategy

### Must-cover unit/integration cases

1. Invalid identifier rejection
- `schema="bad-name"`
- `schema="tenant.one"`
- `table_prefix="tenant-"`
- `table_prefix="1tenant_"`
- all must raise `ValueError` before pool initialization or SQL execution

2. Prefix-only mode
- `table_prefix="tenant_abc_"`
- generated DDL and query strings target `tenant_abc_documents`, `tenant_abc_retrievals`, `tenant_abc_engagements`

3. Schema-qualified mode
- `schema="tenant_alpha"`
- generated DDL and query strings target `tenant_alpha.documents`, etc.
- initialization emits `CREATE SCHEMA IF NOT EXISTS tenant_alpha`

4. Per-schema isolation
- two backend instances on one DB with different schemas must not see each other's rows
- if live Postgres test infrastructure is available, use it for the strongest proof
- otherwise capture the exact SQL names used in fake connection assertions and keep the live case behind the existing env gate

### Test placement

- DDL generation and invalid identifier tests can live near sync backend tests because the public helper will likely live in `postgres.py`
- async tests should prove the async backend passes the same schema/prefix names into queries and initialization

## Execution Risks

### Risk 1: Static async schema import drifts from sync logic

If the async backend keeps consuming a copied `SCHEMA` constant, sync and async tenancy behavior will diverge. The fix is to delete the static dependency and call the shared builder directly.

### Risk 2: Index name collisions in prefix-only mode

Table prefixing without index prefixing still collides inside one schema. Index names need the same namespace treatment.

### Risk 3: Over-expanding the base contract

Adding tenancy knobs to `StorageBackend` would create fake API churn for in-memory/SQLite backends that do not need them. Keep the change local to Postgres backend constructors.

### Risk 4: SQL injection through identifiers

Identifiers cannot be parameterized in these drivers. Validation must happen before string interpolation and before schema DDL runs.

## Recommended Project Structure

```
corpulse/backends/
├── postgres.py
│   ├── build_schema_sql(schema=None, prefix="")
│   ├── _validate_identifier(...)
│   ├── _qualified_name(...)
│   └── PostgresBackend(..., schema=None, table_prefix="")
├── postgres_async.py
│   └── AsyncPostgresBackend.create(..., schema=None, table_prefix="")
└── base.py  # unchanged interface surface
```

## Recommended Execution Order

1. Add shared validation + public DDL builder and lock it down with direct tests.
2. Rewire sync and async backends to store validated tenancy config and replace hardcoded table names with `self._t(...)`.
3. Add invalid-identifier, prefix-only, and per-schema isolation coverage in both backend test suites.

## Decision

Proceed with a three-plan phase:
- `16-01`: shared identifier validation and DDL builder
- `16-02`: sync and async backend refactor to qualified table helpers
- `16-03`: isolation and regression coverage
