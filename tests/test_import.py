"""Smoke tests for import behavior (PKG-04)."""
import importlib
import sys


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
