from corpulse.backends._dsn import _normalize_postgres_dsn

import pytest


@pytest.mark.parametrize(
    ("input_dsn", "expected"),
    [
        ("postgresql://u:p@h/db", "postgresql://u:p@h/db"),
        ("postgres://u:p@h/db", "postgres://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql://u:p@h/db"),
        ("postgresql+psycopg2://u:p@h/db", "postgresql://u:p@h/db"),
        ("postgresql+asyncpg://u:p@h/db", "postgresql://u:p@h/db"),
        ("postgres+asyncpg://u:p@h/db", "postgres://u:p@h/db"),
        (
            "postgresql+asyncpg://u:p%40x@h/db?sslmode=require",
            "postgresql://u:p%40x@h/db?sslmode=require",
        ),
        (
            "postgresql+asyncpg://u@[::1]:5432/db",
            "postgresql://u@[::1]:5432/db",
        ),
        (
            "host=localhost port=5432 dbname=foo",
            "host=localhost port=5432 dbname=foo",
        ),
        ("POSTGRESQL+ASYNCPG://u:p@h/db", "POSTGRESQL+ASYNCPG://u:p@h/db"),
        ("postgresql+psycopg", "postgresql+psycopg"),
    ],
)
def test_normalize_postgres_dsn(input_dsn, expected):
    assert _normalize_postgres_dsn(input_dsn) == expected
