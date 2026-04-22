"""Generic client wrappers that auto-log retrievals to Corpulse."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Mapping


RecordNormalizer = Callable[[Any, tuple[Any, ...], dict[str, Any]], list[dict[str, Any]]]


@dataclass(frozen=True)
class WrapMethod:
    """Describe how to intercept one client method."""

    normalize: RecordNormalizer
    query_kwarg: str = "query_text"


class _BaseWrappedClient:
    def __init__(
        self,
        client: Any,
        corpulse: Any,
        methods: Mapping[str, WrapMethod],
    ) -> None:
        self._client = client
        self._corpulse = corpulse
        self._methods = dict(methods)

    def _wrapped_attr(self, name: str):
        attr = getattr(self._client, name)
        method = self._methods.get(name)
        if method is None or not callable(attr):
            return attr
        return self._wrap_call(attr, method)

    def __getattr__(self, name: str):
        return self._wrapped_attr(name)

    def _split_query_text(
        self,
        method: WrapMethod,
        kwargs: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        call_kwargs = dict(kwargs)
        query_text = ""
        if method.query_kwarg:
            query_text = str(call_kwargs.pop(method.query_kwarg, "") or "")
        return query_text, call_kwargs

    def _wrap_call(self, attr: Callable[..., Any], method: WrapMethod):
        raise NotImplementedError


class WrappedClient(_BaseWrappedClient):
    """Sync proxy that intercepts configured methods and logs retrievals."""

    def _wrap_call(self, attr: Callable[..., Any], method: WrapMethod):
        def wrapped(*args, **kwargs):
            query_text, call_kwargs = self._split_query_text(method, kwargs)
            result = attr(*args, **call_kwargs)
            maybe = self._corpulse.log_retrieval(
                method.normalize(result, args, call_kwargs),
                query=query_text,
            )
            if inspect.isawaitable(maybe):
                raise TypeError(
                    "wrap() produced a sync wrapper, but corpulse.log_retrieval() "
                    "returned an awaitable. Use an async client or async wrapper."
                )
            return result

        return wrapped


class AsyncWrappedClient(_BaseWrappedClient):
    """Async proxy that intercepts configured methods and logs retrievals."""

    def _wrap_call(self, attr: Callable[..., Any], method: WrapMethod):
        async def wrapped(*args, **kwargs):
            query_text, call_kwargs = self._split_query_text(method, kwargs)
            result = await attr(*args, **call_kwargs)
            await self._log_retrieval(
                method.normalize(result, args, call_kwargs),
                query_text,
            )
            return result

        return wrapped

    async def _log_retrieval(self, records: list[dict[str, Any]], query_text: str) -> None:
        log_retrieval = self._corpulse.log_retrieval
        if inspect.iscoroutinefunction(log_retrieval):
            await log_retrieval(records, query=query_text)
            return
        await asyncio.to_thread(log_retrieval, records, query=query_text)


def wrap(
    client: Any,
    corpulse: Any,
    *,
    methods: Mapping[str, WrapMethod],
    async_mode: bool | None = None,
):
    """Wrap a client with Corpulse logging interceptors.

    The wrapper only intercepts configured methods. All other attributes
    delegate transparently to the underlying client.
    """

    if async_mode is None:
        async_mode = any(
            inspect.iscoroutinefunction(getattr(client, name, None))
            for name in methods
        )

    wrapper_cls = AsyncWrappedClient if async_mode else WrappedClient
    return wrapper_cls(client, corpulse, methods)
