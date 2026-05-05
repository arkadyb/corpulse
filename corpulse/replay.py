from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Iterable
from copy import deepcopy
from typing import Any

from .models import (
    RagRequestTraceRow,
    ReplayReportPayload,
    ReplayRequest,
    ReplayResult,
)

ReplayHandler = Callable[[ReplayRequest], Any]
AsyncReplayHandler = Callable[[ReplayRequest], Awaitable[Any]]


def _ordered_replay_traces(
    traces: Iterable[RagRequestTraceRow],
) -> list[RagRequestTraceRow]:
    return sorted(
        list(traces),
        key=lambda trace: (float(trace["captured_at"]), int(trace["trace_id"])),
    )


def _scaled_delay(
    previous: RagRequestTraceRow | None,
    current: RagRequestTraceRow,
    *,
    time_scale: float | None,
    max_delay_seconds: float | None,
) -> float:
    if time_scale is None:
        return 0.0
    if time_scale <= 0:
        raise ValueError("time_scale must be greater than 0")
    if max_delay_seconds is not None and max_delay_seconds < 0:
        raise ValueError("max_delay_seconds must be greater than or equal to 0")

    if previous is None:
        delay = 0.0
    else:
        captured_delta = max(
            float(current["captured_at"]) - float(previous["captured_at"]),
            0.0,
        )
        delay = captured_delta / float(time_scale)

    if max_delay_seconds is not None:
        delay = min(delay, float(max_delay_seconds))
    return delay


def _build_replay_request(
    trace: RagRequestTraceRow,
    *,
    sequence_index: int,
    scheduled_delay_seconds: float,
) -> ReplayRequest:
    return {
        "sequence_index": sequence_index,
        "trace_id": trace["trace_id"],
        "request_id": trace["request_id"],
        "session_id": trace["session_id"],
        "query_text": trace["query_text"],
        "query_hash": trace["query_hash"],
        "input_token_count": trace["input_token_count"],
        "output_token_count": trace["output_token_count"],
        "components": deepcopy(trace["components"]),
        "timings": deepcopy(trace["timings"]),
        "timeout": trace["timeout"],
        "error": trace["error"],
        "captured_at": trace["captured_at"],
        "scheduled_delay_seconds": scheduled_delay_seconds,
    }


def _build_replay_result(
    request: ReplayRequest,
    *,
    ok: bool,
    error: str | None,
    started_at: float,
    completed_at: float,
) -> ReplayResult:
    return {
        "sequence_index": request["sequence_index"],
        "trace_id": request["trace_id"],
        "request_id": request["request_id"],
        "session_id": request["session_id"],
        "ok": ok,
        "error": error,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": max(completed_at - started_at, 0.0),
        "scheduled_delay_seconds": request["scheduled_delay_seconds"],
    }


def _build_report(
    *,
    trace_count: int,
    results: list[ReplayResult],
    total_runtime_seconds: float,
) -> ReplayReportPayload:
    succeeded_count = sum(1 for result in results if result["ok"])
    failed_count = sum(1 for result in results if not result["ok"])
    replayed_count = len(results)
    return {
        "summary": {
            "trace_count": trace_count,
            "replayed_count": replayed_count,
            "succeeded_count": succeeded_count,
            "failed_count": failed_count,
            "skipped_count": trace_count - replayed_count,
            "total_scheduled_delay_seconds": sum(
                result["scheduled_delay_seconds"] for result in results
            ),
            "total_runtime_seconds": total_runtime_seconds,
        },
        "results": results,
    }


def replay_rag_request_traces(
    traces: Iterable[RagRequestTraceRow],
    handler: ReplayHandler,
    *,
    time_scale: float | None = None,
    max_delay_seconds: float | None = None,
    stop_on_error: bool = False,
    sleep: Callable[[float], Any] | None = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> ReplayReportPayload:
    ordered_traces = _ordered_replay_traces(traces)
    results: list[ReplayResult] = []
    replay_started_at = float(clock())
    previous_trace: RagRequestTraceRow | None = None

    for sequence_index, trace in enumerate(ordered_traces):
        delay = _scaled_delay(
            previous_trace,
            trace,
            time_scale=time_scale,
            max_delay_seconds=max_delay_seconds,
        )
        if delay > 0 and sleep is not None:
            sleep(delay)

        request = _build_replay_request(
            trace,
            sequence_index=sequence_index,
            scheduled_delay_seconds=delay,
        )
        started_at = float(clock())
        ok = True
        error = None
        try:
            handler(request)
        except Exception as exc:  # pragma: no cover - exercised via public behavior
            ok = False
            error = str(exc)
        completed_at = float(clock())
        results.append(
            _build_replay_result(
                request,
                ok=ok,
                error=error,
                started_at=started_at,
                completed_at=completed_at,
            )
        )

        previous_trace = trace
        if not ok and stop_on_error:
            break

    replay_completed_at = float(clock())
    return _build_report(
        trace_count=len(ordered_traces),
        results=results,
        total_runtime_seconds=max(replay_completed_at - replay_started_at, 0.0),
    )


async def async_replay_rag_request_traces(
    traces: Iterable[RagRequestTraceRow],
    handler: AsyncReplayHandler,
    *,
    time_scale: float | None = None,
    max_delay_seconds: float | None = None,
    stop_on_error: bool = False,
    sleep: Callable[[float], Awaitable[Any]] | None = asyncio.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> ReplayReportPayload:
    ordered_traces = _ordered_replay_traces(traces)
    results: list[ReplayResult] = []
    replay_started_at = float(clock())
    previous_trace: RagRequestTraceRow | None = None

    for sequence_index, trace in enumerate(ordered_traces):
        delay = _scaled_delay(
            previous_trace,
            trace,
            time_scale=time_scale,
            max_delay_seconds=max_delay_seconds,
        )
        if delay > 0 and sleep is not None:
            await sleep(delay)

        request = _build_replay_request(
            trace,
            sequence_index=sequence_index,
            scheduled_delay_seconds=delay,
        )
        started_at = float(clock())
        ok = True
        error = None
        try:
            await handler(request)
        except Exception as exc:  # pragma: no cover - exercised via public behavior
            ok = False
            error = str(exc)
        completed_at = float(clock())
        results.append(
            _build_replay_result(
                request,
                ok=ok,
                error=error,
                started_at=started_at,
                completed_at=completed_at,
            )
        )

        previous_trace = trace
        if not ok and stop_on_error:
            break

    replay_completed_at = float(clock())
    return _build_report(
        trace_count=len(ordered_traces),
        results=results,
        total_runtime_seconds=max(replay_completed_at - replay_started_at, 0.0),
    )
