from __future__ import annotations

_SCHEME_PREFIXES = ("postgresql+", "postgres+")


def _normalize_postgres_dsn(dsn: str) -> str:
    """Strip SQLAlchemy-style '+driver' qualifiers from Postgres URIs."""
    for prefix in _SCHEME_PREFIXES:
        if dsn.startswith(prefix):
            base = prefix[:-1]
            rest = dsn[len(prefix):]
            separator = rest.find("://")
            if separator == -1:
                return dsn
            return f"{base}://{rest[separator + 3:]}"
    return dsn
