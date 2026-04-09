from .core import Corpulse

__all__ = [
    "Corpulse",
    "AsyncCorpulse",
    "QdrantCorpulseClient",
    "AsyncQdrantCorpulseClient",
]
__version__ = "0.1.0"


def __getattr__(name):
    if name == "AsyncCorpulse":
        from .async_core import AsyncCorpulse

        globals()["AsyncCorpulse"] = AsyncCorpulse
        return AsyncCorpulse
    if name in ("QdrantCorpulseClient", "AsyncQdrantCorpulseClient"):
        from .integrations.qdrant import QdrantCorpulseClient, AsyncQdrantCorpulseClient
        globals()["QdrantCorpulseClient"] = QdrantCorpulseClient
        globals()["AsyncQdrantCorpulseClient"] = AsyncQdrantCorpulseClient
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
