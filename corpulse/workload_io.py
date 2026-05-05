from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import (
    RagRequestComponent,
    RagRequestTimings,
    RagRequestTraceImportResult,
    RagRequestTraceRow,
)

RAG_REQUEST_TRACE_JSONL_SCHEMA = "corpulse.rag_request_trace.v1"


def _component_for_export(
    component: RagRequestComponent,
    *,
    include_component_metadata: bool,
) -> dict[str, Any]:
    exported: dict[str, Any] = {
        "type": component["type"],
        "token_count": component["token_count"],
        "refs": component["refs"],
        "content_hash": component["content_hash"],
    }
    if include_component_metadata:
        exported["metadata"] = component["metadata"]
    else:
        exported["metadata"] = None
    return exported


def _component_for_fingerprint(component: RagRequestComponent) -> dict[str, Any]:
    return {
        "type": component["type"],
        "token_count": component["token_count"],
        "refs": component["refs"],
        "content_hash": component["content_hash"],
    }


def serialize_rag_request_trace_jsonl(
    trace: RagRequestTraceRow,
    *,
    include_raw_text: bool = False,
    include_component_metadata: bool = False,
) -> str:
    record: dict[str, Any] = {
        "schema_version": RAG_REQUEST_TRACE_JSONL_SCHEMA,
        "trace_id": trace["trace_id"],
        "request_id": trace["request_id"],
        "session_id": trace["session_id"],
        "query_hash": trace["query_hash"],
        "input_token_count": trace["input_token_count"],
        "output_token_count": trace["output_token_count"],
        "components": [
            _component_for_export(component, include_component_metadata=include_component_metadata)
            for component in trace["components"]
        ],
        "timings": dict(trace["timings"]),
        "timeout": trace["timeout"],
        "error": trace["error"],
        "captured_at": trace["captured_at"],
    }
    if include_raw_text:
        record["query_text"] = trace["query_text"]
    else:
        record["query_text"] = None
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def _coerce_component(raw: Any, *, strict: bool, line_number: int) -> RagRequestComponent:
    if not isinstance(raw, dict):
        raise ValueError(f"Line {line_number}: component entries must be objects")
    if "type" not in raw:
        raise ValueError(f"Line {line_number}: component missing required field 'type'")
    component: RagRequestComponent = {
        "type": str(raw["type"]),
        "token_count": raw.get("token_count"),
        "refs": raw.get("refs"),
        "content_hash": raw.get("content_hash"),
        "metadata": raw.get("metadata"),
    }
    if component["refs"] is not None and not isinstance(component["refs"], list):
        raise ValueError(f"Line {line_number}: component refs must be a list or null")
    if component["metadata"] is not None and not isinstance(component["metadata"], dict):
        raise ValueError(f"Line {line_number}: component metadata must be an object or null")
    if component["token_count"] is not None and not isinstance(component["token_count"], int):
        raise ValueError(f"Line {line_number}: component token_count must be an int or null")
    if component["content_hash"] is not None and not isinstance(component["content_hash"], str):
        raise ValueError(f"Line {line_number}: component content_hash must be a string or null")
    return component


def _coerce_timings(raw: Any, *, line_number: int) -> RagRequestTimings:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"Line {line_number}: timings must be an object or null")
    timings: RagRequestTimings = {}
    for key, value in raw.items():
        if value is None:
            continue
        if not isinstance(value, (int, float)):
            raise ValueError(f"Line {line_number}: timing '{key}' must be numeric or null")
        timings[str(key)] = float(value)
    return timings


def parse_rag_request_trace_jsonl_line(
    line: str,
    *,
    line_number: int,
    strict: bool = True,
) -> RagRequestTraceRow:
    stripped = line.strip()
    if not stripped:
        raise ValueError(f"Line {line_number}: blank JSONL line")
    try:
        raw = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Line {line_number}: invalid JSON") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"Line {line_number}: JSONL record must be an object")
    schema_version = raw.get("schema_version")
    if schema_version != RAG_REQUEST_TRACE_JSONL_SCHEMA:
        raise ValueError(
            f"Line {line_number}: unsupported schema_version {schema_version!r}"
        )
    if "components" not in raw:
        if strict:
            raise ValueError(f"Line {line_number}: missing required field 'components'")
        components: list[RagRequestComponent] = []
    else:
        components_raw = raw.get("components")
        if components_raw is None:
            if strict:
                raise ValueError(f"Line {line_number}: components must be a list")
            components = []
        elif not isinstance(components_raw, list):
            raise ValueError(f"Line {line_number}: components must be a list")
        else:
            components = [
                _coerce_component(component, strict=strict, line_number=line_number)
                for component in components_raw
            ]
    timings = _coerce_timings(raw.get("timings"), line_number=line_number)
    if strict and "timings" not in raw:
        raise ValueError(f"Line {line_number}: missing required field 'timings'")
    timeout = raw.get("timeout")
    if strict and "timeout" not in raw:
        raise ValueError(f"Line {line_number}: missing required field 'timeout'")
    if not isinstance(timeout, bool):
        raise ValueError(f"Line {line_number}: timeout must be a boolean")
    if "captured_at" not in raw:
        raise ValueError(f"Line {line_number}: missing required field 'captured_at'")
    captured_at = raw["captured_at"]
    if not isinstance(captured_at, (int, float)):
        raise ValueError(f"Line {line_number}: captured_at must be numeric")
    query_text = raw.get("query_text")
    if query_text is not None and not isinstance(query_text, str):
        raise ValueError(f"Line {line_number}: query_text must be a string or null")
    query_hash = raw.get("query_hash")
    if query_hash is not None and not isinstance(query_hash, str):
        raise ValueError(f"Line {line_number}: query_hash must be a string or null")
    request_id = raw.get("request_id")
    if request_id is not None and not isinstance(request_id, str):
        raise ValueError(f"Line {line_number}: request_id must be a string or null")
    session_id = raw.get("session_id")
    if session_id is not None and not isinstance(session_id, str):
        raise ValueError(f"Line {line_number}: session_id must be a string or null")
    input_token_count = raw.get("input_token_count")
    if input_token_count is not None and not isinstance(input_token_count, int):
        raise ValueError(f"Line {line_number}: input_token_count must be an int or null")
    output_token_count = raw.get("output_token_count")
    if output_token_count is not None and not isinstance(output_token_count, int):
        raise ValueError(f"Line {line_number}: output_token_count must be an int or null")
    error = raw.get("error")
    if error is not None and not isinstance(error, str):
        raise ValueError(f"Line {line_number}: error must be a string or null")

    return {
        "trace_id": int(raw.get("trace_id", 0)),
        "request_id": request_id,
        "session_id": session_id,
        "query_text": query_text,
        "query_hash": query_hash,
        "input_token_count": input_token_count,
        "output_token_count": output_token_count,
        "components": components,
        "timings": timings,
        "timeout": timeout,
        "error": error,
        "captured_at": float(captured_at),
    }


def rag_request_trace_fingerprint(trace: RagRequestTraceRow) -> str:
    payload = {
        "request_id": trace["request_id"],
        "session_id": trace["session_id"],
        "query_hash": trace["query_hash"],
        "input_token_count": trace["input_token_count"],
        "output_token_count": trace["output_token_count"],
        "components": [_component_for_fingerprint(component) for component in trace["components"]],
        "timings": dict(trace["timings"]),
        "timeout": trace["timeout"],
        "error": trace["error"],
        "captured_at": trace["captured_at"],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def existing_rag_request_trace_fingerprints(traces: list[RagRequestTraceRow]) -> set[str]:
    return {rag_request_trace_fingerprint(trace) for trace in traces}
