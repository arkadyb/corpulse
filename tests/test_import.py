"""Smoke tests for import behavior (PKG-04)."""
import importlib
import sys

import pytest


def test_import_corpulse():
    """PKG-04: import corpulse succeeds."""
    import corpulse
    assert hasattr(corpulse, "Corpulse"), "Corpulse class not exported"
    assert hasattr(corpulse, "__version__"), "__version__ not exposed"


def test_version_is_string():
    """Version is a valid string."""
    import corpulse
    assert isinstance(corpulse.__version__, str)
    assert corpulse.__version__ == "0.1.0"


def test_version_remains_single_sourced():
    """PKG-01: Runtime version remains available while Hatch reads it dynamically."""
    import corpulse
    assert corpulse.__version__ == "0.1.0"


def test_import_without_qdrant(monkeypatch):
    """PKG-04: import corpulse must succeed without qdrant-client installed."""
    # Poison qdrant_client in sys.modules to simulate it being absent
    monkeypatch.setitem(sys.modules, "qdrant_client", None)
    # Reload to verify no top-level qdrant import
    import corpulse
    importlib.reload(corpulse)
    assert hasattr(corpulse, "Corpulse")


def test_corpulse_class_importable():
    """Corpulse class can be instantiated from the package."""
    from corpulse import Corpulse
    # Just verify the class is accessible; don't instantiate (needs filesystem)
    assert callable(Corpulse)


def test_import_backends_does_not_eagerly_load_psycopg():
    """corpulse.backends import succeeds without importing psycopg."""
    sys.modules.pop("psycopg", None)
    import corpulse.backends as backends

    importlib.reload(backends)

    assert hasattr(backends, "SQLiteBackend")
    assert "psycopg" not in sys.modules


def test_postgres_backend_lazy_export_does_not_import_psycopg():
    """Accessing the lazy export should load the backend module, not the driver."""
    sys.modules.pop("psycopg", None)
    import corpulse.backends as backends

    importlib.reload(backends)

    postgres_backend = backends.PostgresBackend

    assert postgres_backend.__name__ == "PostgresBackend"
    assert "psycopg" not in sys.modules


def test_import_backends_does_not_eagerly_load_asyncpg():
    """corpulse.backends import succeeds without importing asyncpg."""
    sys.modules.pop("asyncpg", None)
    import corpulse.backends as backends

    importlib.reload(backends)

    assert hasattr(backends, "SQLiteBackend")
    assert "asyncpg" not in sys.modules


def test_async_postgres_backend_lazy_export_does_not_import_asyncpg():
    """Accessing the async lazy export should load the backend module, not the driver."""
    sys.modules.pop("asyncpg", None)
    import corpulse.backends as backends

    importlib.reload(backends)

    if not hasattr(backends, "AsyncPostgresBackend"):
        pytest.skip("AsyncPostgresBackend not yet implemented")

    async_pg_backend = backends.AsyncPostgresBackend

    assert async_pg_backend.__name__ == "AsyncPostgresBackend"
    assert "asyncpg" not in sys.modules


def test_package_root_async_corpulse_export_does_not_import_asyncpg():
    """corpulse.AsyncCorpulse should be available without importing asyncpg."""
    sys.modules.pop("asyncpg", None)
    import corpulse

    importlib.reload(corpulse)

    assert hasattr(corpulse, "AsyncCorpulse")
    assert corpulse.AsyncCorpulse.__name__ == "AsyncCorpulse"
    assert "asyncpg" not in sys.modules
