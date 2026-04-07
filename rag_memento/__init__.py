from .memento import Memento

__all__ = ["Memento", "QdrantMementoClient", "AsyncQdrantMementoClient"]
__version__ = "0.1.0"


def __getattr__(name):
    if name in ("QdrantMementoClient", "AsyncQdrantMementoClient"):
        from .integrations.qdrant import QdrantMementoClient, AsyncQdrantMementoClient
        globals()["QdrantMementoClient"] = QdrantMementoClient
        globals()["AsyncQdrantMementoClient"] = AsyncQdrantMementoClient
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
