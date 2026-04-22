from __future__ import annotations

from dataclasses import dataclass

from corpulse.integrations.wrapper import AsyncWrappedClient, WrapMethod, WrappedClient, wrap


@dataclass
class _SyncResult:
    hits: list[dict]


class _SyncClient:
    def __init__(self):
        self.other_value = "ok"

    def search(self, collection_name, *, limit=5):
        return _SyncResult(
            hits=[
                {
                    "id": "doc-1",
                    "name": "guide.md",
                    "score": 0.91,
                }
            ]
        )


class _AsyncClient:
    async def search(self, collection_name, *, limit=5):
        return _SyncResult(
            hits=[
                {
                    "id": "doc-2",
                    "name": "faq.md",
                    "score": 0.83,
                }
            ]
        )


class _LoggingCorpulse:
    def __init__(self):
        self.calls = []

    def log_retrieval(self, records, query=""):
        self.calls.append((records, query))


class _AsyncLoggingCorpulse:
    def __init__(self):
        self.calls = []

    async def log_retrieval(self, records, query=""):
        self.calls.append((records, query))


def _normalize_hits(result, args, kwargs):
    return [
        {
            "doc_id": item["id"],
            "filename": item["name"],
            "score": item["score"],
            "embedding": None,
        }
        for item in result.hits
    ]


def test_wrap_builds_sync_proxy_and_intercepts_configured_method():
    corpulse = _LoggingCorpulse()
    client = _SyncClient()

    wrapped = wrap(
        client,
        corpulse,
        methods={"search": WrapMethod(normalize=_normalize_hits)},
    )

    assert isinstance(wrapped, WrappedClient)
    result = wrapped.search("docs", query_text="install corpulse", limit=1)

    assert result.hits[0]["id"] == "doc-1"
    assert corpulse.calls == [
        (
            [
                {
                    "doc_id": "doc-1",
                    "filename": "guide.md",
                    "score": 0.91,
                    "embedding": None,
                }
            ],
            "install corpulse",
        )
    ]
    assert wrapped.other_value == "ok"


async def test_wrap_builds_async_proxy_and_supports_async_corpulse():
    corpulse = _AsyncLoggingCorpulse()
    client = _AsyncClient()

    wrapped = wrap(
        client,
        corpulse,
        methods={"search": WrapMethod(normalize=_normalize_hits)},
    )

    assert isinstance(wrapped, AsyncWrappedClient)
    result = await wrapped.search("docs", query_text="faq", limit=1)

    assert result.hits[0]["id"] == "doc-2"
    assert corpulse.calls == [
        (
            [
                {
                    "doc_id": "doc-2",
                    "filename": "faq.md",
                    "score": 0.83,
                    "embedding": None,
                }
            ],
            "faq",
        )
    ]
