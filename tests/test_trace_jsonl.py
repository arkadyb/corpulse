from __future__ import annotations

import asyncio
import io
import json

import pytest

from corpulse.workload_io import (
    RAG_REQUEST_TRACE_JSONL_SCHEMA,
    existing_rag_request_trace_fingerprints,
    parse_rag_request_trace_jsonl_line,
    rag_request_trace_fingerprint,
    serialize_rag_request_trace_jsonl,
)
from corpulse.backends import InMemoryBackend
from corpulse import Corpulse, AsyncCorpulse
from tests.test_trace_capture import FakeAsyncTraceBackend


def sample_rag_request_trace():
    return {
        "trace_id": 7,
        "request_id": "req-7",
        "session_id": "session-7",
        "query_text": "how do I enroll?",
        "query_hash": "hash-7",
        "input_token_count": 42,
        "output_token_count": 9,
        "components": [
            {
                "type": "system_prompt",
                "token_count": 11,
                "refs": None,
                "content_hash": "sp-7",
                "metadata": {"source": "system"},
            },
            {
                "type": "vector_db",
                "token_count": 21,
                "refs": [{"doc_id": "doc-7"}],
                "content_hash": "vec-7",
                "metadata": {"top_k": 5},
            },
        ],
        "timings": {
            "ttft_ms": 123.0,
            "tpot_ms": 11.0,
            "generation_ms": 321.0,
        },
        "timeout": False,
        "error": None,
        "captured_at": 1710000000.0,
    }


def log_sample_trace(corpulse, *, request_id="req-7", query_text="how do I enroll?"):
    corpulse.log_rag_request(
        session_id="session-7",
        query=query_text,
        request_id=request_id,
        components=[
            {
                "type": "system_prompt",
                "token_count": 11,
                "refs": None,
                "content_hash": "sp-7",
                "metadata": {"source": "system"},
            },
            {
                "type": "vector_db",
                "token_count": 21,
                "refs": [{"doc_id": "doc-7"}],
                "content_hash": "vec-7",
                "metadata": {"top_k": 5},
            },
        ],
        input_token_count=42,
        output_token_count=9,
        timings={
            "ttft_ms": 123.0,
            "tpot_ms": 11.0,
            "generation_ms": 321.0,
        },
        timeout=False,
        error=None,
    )


def test_rag_request_trace_jsonl_serializes_line_only_schema_version():
    trace = sample_rag_request_trace()

    line = serialize_rag_request_trace_jsonl(trace)

    assert line.endswith("\n") is False
    record = json.loads(line)
    assert record["schema_version"] == RAG_REQUEST_TRACE_JSONL_SCHEMA
    assert record["trace_id"] == 7
    assert record["query_text"] is None
    assert record["components"][0]["metadata"] is None


def test_rag_request_trace_jsonl_privacy_default_omits_query_text_and_metadata():
    trace = sample_rag_request_trace()

    record = json.loads(serialize_rag_request_trace_jsonl(trace))

    assert record["query_text"] is None
    assert record["components"][0]["metadata"] is None
    assert record["components"][1]["metadata"] is None
    assert record["query_hash"] == "hash-7"
    assert record["timings"]["ttft_ms"] == 123.0
    assert record["captured_at"] == 1710000000.0


def test_rag_request_trace_jsonl_raw_opt_in_preserves_query_text_and_metadata():
    trace = sample_rag_request_trace()

    record = json.loads(
        serialize_rag_request_trace_jsonl(
            trace,
            include_raw_text=True,
            include_component_metadata=True,
        )
    )

    assert record["query_text"] == "how do I enroll?"
    assert record["components"][0]["metadata"] == {"source": "system"}
    assert record["components"][1]["metadata"] == {"top_k": 5}


def test_rag_request_trace_jsonl_strict_parse_rejects_invalid_required_fields():
    with pytest.raises(ValueError, match="invalid JSON"):
        parse_rag_request_trace_jsonl_line("{", line_number=1)

    with pytest.raises(ValueError, match="schema_version"):
        parse_rag_request_trace_jsonl_line(
            json.dumps({"schema_version": "wrong"}),
            line_number=2,
        )

    base = {
        "schema_version": RAG_REQUEST_TRACE_JSONL_SCHEMA,
        "trace_id": 1,
        "request_id": None,
        "session_id": None,
        "query_hash": "q",
        "input_token_count": 1,
        "output_token_count": 1,
        "components": [],
        "timings": {},
        "timeout": False,
        "error": None,
        "captured_at": 1.0,
    }

    for missing_key, match in [
        ("components", "components"),
        ("timings", "timings"),
        ("timeout", "timeout"),
        ("captured_at", "captured_at"),
    ]:
        payload = dict(base)
        payload.pop(missing_key)
        with pytest.raises(ValueError, match=match):
            parse_rag_request_trace_jsonl_line(json.dumps(payload), line_number=3)


def test_rag_request_trace_jsonl_permissive_parse_reports_optional_defaults():
    payload = {
        "schema_version": RAG_REQUEST_TRACE_JSONL_SCHEMA,
        "trace_id": 3,
        "request_id": "req-3",
        "session_id": "session-3",
        "query_hash": "hash-3",
        "timeout": True,
        "captured_at": 1710000000.0,
    }

    trace = parse_rag_request_trace_jsonl_line(
        json.dumps(payload),
        line_number=4,
        strict=False,
    )

    assert trace["components"] == []
    assert trace["timings"] == {}
    assert trace["request_id"] == "req-3"
    assert trace["timeout"] is True
    assert trace["captured_at"] == 1710000000.0


def test_rag_request_trace_jsonl_fingerprint_ignores_trace_id_query_text_and_metadata():
    trace_a = sample_rag_request_trace()
    trace_b = sample_rag_request_trace()
    trace_b["trace_id"] = 99
    trace_b["query_text"] = "a different raw query"
    trace_b["components"] = [
        {
            "type": "system_prompt",
            "token_count": 11,
            "refs": None,
            "content_hash": "sp-7",
            "metadata": {"source": "mutated"},
        },
        {
            "type": "vector_db",
            "token_count": 21,
            "refs": [{"doc_id": "doc-7"}],
            "content_hash": "vec-7",
            "metadata": {"top_k": 99},
        },
    ]

    assert rag_request_trace_fingerprint(trace_a) == rag_request_trace_fingerprint(trace_b)
    assert existing_rag_request_trace_fingerprints([trace_a, trace_b]) == {
        rag_request_trace_fingerprint(trace_a)
    }


def test_sync_export_rag_request_traces_jsonl_writes_privacy_first_lines(tmp_path):
    backend = InMemoryBackend()
    corpulse = Corpulse(backend=backend)
    log_sample_trace(corpulse)

    destination = tmp_path / "traces.jsonl"
    count = corpulse.export_rag_request_traces_jsonl(destination)

    assert count == 1
    lines = destination.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["query_text"] is None
    assert record["components"][0]["metadata"] is None


def test_sync_export_rag_request_traces_jsonl_raw_opt_in_writes_query_text_and_metadata():
    backend = InMemoryBackend()
    corpulse = Corpulse(backend=backend)
    log_sample_trace(corpulse)
    buf = io.StringIO()

    count = corpulse.export_rag_request_traces_jsonl(
        buf,
        include_raw_text=True,
        include_component_metadata=True,
    )

    assert count == 1
    record = json.loads(buf.getvalue().strip())
    assert record["query_text"] == "how do I enroll?"
    assert record["components"][0]["metadata"] == {"source": "system"}


def test_sync_import_rag_request_traces_jsonl_round_trips_privacy_export(tmp_path):
    backend = InMemoryBackend()
    corpulse = Corpulse(backend=backend)
    log_sample_trace(corpulse)
    destination = tmp_path / "traces.jsonl"
    corpulse.export_rag_request_traces_jsonl(destination)

    imported = Corpulse(backend=InMemoryBackend()).import_rag_request_traces_jsonl(destination)

    assert imported == {
        "total": 1,
        "imported": 1,
        "skipped_duplicates": 0,
        "invalid": 0,
        "errors": [],
    }


def test_sync_import_rag_request_traces_jsonl_skips_duplicate_reimport(tmp_path):
    backend = InMemoryBackend()
    corpulse = Corpulse(backend=backend)
    log_sample_trace(corpulse)
    destination = tmp_path / "traces.jsonl"
    corpulse.export_rag_request_traces_jsonl(destination)

    target = Corpulse(backend=InMemoryBackend())
    first = target.import_rag_request_traces_jsonl(destination)
    second = target.import_rag_request_traces_jsonl(destination)

    assert first["imported"] == 1
    assert second == {
        "total": 1,
        "imported": 0,
        "skipped_duplicates": 1,
        "invalid": 0,
        "errors": [],
    }


def test_sync_import_rag_request_traces_jsonl_permissive_mode_reports_invalid_lines():
    backend = InMemoryBackend()
    corpulse = Corpulse(backend=backend)
    log_sample_trace(corpulse)
    buf = io.StringIO()
    corpulse.export_rag_request_traces_jsonl(buf)
    buf.write("\n")
    buf.write('{"schema_version":"corpulse.rag_request_trace.v1","timeout":false}\n')
    buf.seek(0)

    result = Corpulse(backend=InMemoryBackend()).import_rag_request_traces_jsonl(
        buf,
        strict=False,
    )

    assert result["total"] == 2
    assert result["imported"] == 1
    assert result["invalid"] == 1
    assert result["skipped_duplicates"] == 0
    assert result["errors"]


@pytest.mark.asyncio
async def test_async_export_rag_request_traces_jsonl_matches_sync_lines(tmp_path, monkeypatch):
    monkeypatch.setattr("corpulse.core._now", lambda: 1710000000.0)
    monkeypatch.setattr("corpulse.async_core._now", lambda: 1710000000.0)
    monkeypatch.setattr("corpulse.core._days_ago", lambda days: 0.0)
    monkeypatch.setattr("corpulse.async_core._days_ago", lambda days: 0.0)

    sync_backend = InMemoryBackend()
    sync_corpulse = Corpulse(backend=sync_backend)
    log_sample_trace(sync_corpulse)
    sync_file = tmp_path / "sync.jsonl"
    sync_corpulse.export_rag_request_traces_jsonl(sync_file)

    async_backend = FakeAsyncTraceBackend()
    async_corpulse = AsyncCorpulse(backend=async_backend)
    await async_corpulse.alog_rag_request(
        session_id="session-7",
        query="how do I enroll?",
        request_id="req-7",
        components=sample_rag_request_trace()["components"],
        input_token_count=42,
        output_token_count=9,
        timings=sample_rag_request_trace()["timings"],
        timeout=False,
        error=None,
    )
    async_file = tmp_path / "async.jsonl"
    await async_corpulse.aexport_rag_request_traces_jsonl(async_file)

    assert async_file.read_text(encoding="utf-8") == sync_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_async_import_rag_request_traces_jsonl_round_trips_privacy_export(tmp_path):
    async_backend = FakeAsyncTraceBackend()
    async_corpulse = AsyncCorpulse(backend=async_backend)
    await async_corpulse.alog_rag_request(
        session_id="session-7",
        query="how do I enroll?",
        request_id="req-7",
        components=sample_rag_request_trace()["components"],
        input_token_count=42,
        output_token_count=9,
        timings=sample_rag_request_trace()["timings"],
        timeout=False,
        error=None,
    )
    destination = tmp_path / "async.jsonl"
    await async_corpulse.aexport_rag_request_traces_jsonl(destination)

    imported = await AsyncCorpulse(backend=FakeAsyncTraceBackend()).aimport_rag_request_traces_jsonl(destination)

    assert imported == {
        "total": 1,
        "imported": 1,
        "skipped_duplicates": 0,
        "invalid": 0,
        "errors": [],
    }


@pytest.mark.asyncio
async def test_async_import_rag_request_traces_jsonl_skips_duplicate_reimport(tmp_path):
    async_backend = FakeAsyncTraceBackend()
    async_corpulse = AsyncCorpulse(backend=async_backend)
    await async_corpulse.alog_rag_request(
        session_id="session-7",
        query="how do I enroll?",
        request_id="req-7",
        components=sample_rag_request_trace()["components"],
        input_token_count=42,
        output_token_count=9,
        timings=sample_rag_request_trace()["timings"],
        timeout=False,
        error=None,
    )
    destination = tmp_path / "async.jsonl"
    await async_corpulse.aexport_rag_request_traces_jsonl(destination)

    target = AsyncCorpulse(backend=FakeAsyncTraceBackend())
    first = await target.aimport_rag_request_traces_jsonl(destination)
    second = await target.aimport_rag_request_traces_jsonl(destination)

    assert first["imported"] == 1
    assert second == {
        "total": 1,
        "imported": 0,
        "skipped_duplicates": 1,
        "invalid": 0,
        "errors": [],
    }


@pytest.mark.asyncio
async def test_async_import_rag_request_traces_jsonl_permissive_mode_reports_invalid_lines():
    async_backend = FakeAsyncTraceBackend()
    async_corpulse = AsyncCorpulse(backend=async_backend)
    await async_corpulse.alog_rag_request(
        session_id="session-7",
        query="how do I enroll?",
        request_id="req-7",
        components=sample_rag_request_trace()["components"],
        input_token_count=42,
        output_token_count=9,
        timings=sample_rag_request_trace()["timings"],
        timeout=False,
        error=None,
    )
    buf = io.StringIO()
    await async_corpulse.aexport_rag_request_traces_jsonl(buf)
    buf.write("\n")
    buf.write('{"schema_version":"corpulse.rag_request_trace.v1","timeout":false}\n')
    buf.seek(0)

    result = await AsyncCorpulse(backend=FakeAsyncTraceBackend()).aimport_rag_request_traces_jsonl(
        buf,
        strict=False,
    )

    assert result["total"] == 2
    assert result["imported"] == 1
    assert result["invalid"] == 1
    assert result["skipped_duplicates"] == 0
    assert result["errors"]
