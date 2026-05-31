from .core import Corpulse

__all__ = [
    "Corpulse",
    "AsyncCorpulse",
    "WrapMethod",
    "wrap",
    "QdrantCorpulseClient",
    "AsyncQdrantCorpulseClient",
]
__version__ = "1.9.2"


def __getattr__(name):
    if name == "AsyncCorpulse":
        from .async_core import AsyncCorpulse

        globals()["AsyncCorpulse"] = AsyncCorpulse
        return AsyncCorpulse
    if name in ("WrapMethod", "wrap"):
        from .integrations.wrapper import WrapMethod, wrap

        globals()["WrapMethod"] = WrapMethod
        globals()["wrap"] = wrap
        return globals()[name]
    if name in ("QdrantCorpulseClient", "AsyncQdrantCorpulseClient"):
        from .integrations.qdrant import QdrantCorpulseClient, AsyncQdrantCorpulseClient
        globals()["QdrantCorpulseClient"] = QdrantCorpulseClient
        globals()["AsyncQdrantCorpulseClient"] = AsyncQdrantCorpulseClient
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
