"""Smoke tests for import behavior (PKG-04)."""
import importlib
import sys


def test_import_corpulse():
    """PKG-04: import corpulse succeeds."""
    import corpulse
    assert hasattr(corpulse, "Memento"), "Memento class not exported"
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
    assert hasattr(corpulse, "Memento")


def test_memento_class_importable():
    """Memento class can be instantiated from the package."""
    from corpulse import Memento
    # Just verify the class is accessible; don't instantiate (needs filesystem)
    assert callable(Memento)
