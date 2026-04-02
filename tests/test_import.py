"""Smoke tests for import behavior (PKG-04)."""
import importlib
import sys


def test_import_rag_memento():
    """PKG-04: import rag_memento succeeds."""
    import rag_memento
    assert hasattr(rag_memento, "Memento"), "Memento class not exported"
    assert hasattr(rag_memento, "__version__"), "__version__ not exposed"


def test_version_is_string():
    """Version is a valid string."""
    import rag_memento
    assert isinstance(rag_memento.__version__, str)
    assert rag_memento.__version__ == "0.1.0"


def test_import_without_qdrant(monkeypatch):
    """PKG-04: import rag_memento must succeed without qdrant-client installed."""
    # Poison qdrant_client in sys.modules to simulate it being absent
    monkeypatch.setitem(sys.modules, "qdrant_client", None)
    # Reload to verify no top-level qdrant import
    import rag_memento
    importlib.reload(rag_memento)
    assert hasattr(rag_memento, "Memento")


def test_memento_class_importable():
    """Memento class can be instantiated from the package."""
    from rag_memento import Memento
    # Just verify the class is accessible; don't instantiate (needs filesystem)
    assert callable(Memento)
