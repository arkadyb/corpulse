"""
corpulse  v1.9.2
Core public API — track, analyse, and report on your RAG corpus health.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from math import ceil
from typing import Any, Iterable, List, Set, Dict

import numpy as np

from .backends import SQLiteBackend, StorageBackend
from .models import (
    ReportRow, ReportSummary, CleanupPayload, GhostItem,
    DuplicatePair, ObsoleteItem, StaleItem, SuspectItem,
    CorpusHealth, DocumentRow, RetrievalRow, EngagementRow, EngagementEventRow, QueryRow,
    QueryAttemptRow,
    GenerationTraceRow,
    RagRequestComponent,
    RagRequestTimings,
    RagRequestTraceImportResult,
    RagRequestTraceRow,
    TokenDistribution,
    WorkloadComponentSummary,
    WorkloadReportPayload,
    WorkloadTokenSummary,
    WorkloadTrafficSummary,
    ContextReuseItem,
    LatencyDistribution,
    ServingReportPayload,
    ServingSlowContributor,
    SessionReportPayload,
    ReplayReportPayload,
    LowConfidenceQueryRow, ZeroResultQueryRow,
    EmbeddingRow
)
from .replay import ReplayHandler, replay_rag_request_traces
from .workload_io import (
    existing_rag_request_trace_fingerprints,
    parse_rag_request_trace_jsonl_line,
    rag_request_trace_fingerprint,
    serialize_rag_request_trace_jsonl,
)

try:
    from sklearn.metrics.pairwise import cosine_similarity
    _SKLEARN = True
except ImportError:
    _SKLEARN = False


# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _hash_query(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()[:16]


def _days_ago(days: int) -> float:
    return _now() - days * 86_400


def _ts_to_date(ts: float | None) -> str:
    if ts is None:
        return "—"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def _vec_to_bytes(vec) -> bytes:
    return np.array(vec, dtype=np.float32).tobytes()


def _bytes_to_vec(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)


_STATUS_ICON = {
    "ghost": "👻 ghost",
    "obsolete": "⚠  obsolete",
    "stale": "🕓 stale emb.",
    "low_engagement": "◌  low eng.",
    "healthy": "✓  healthy",
}

_ACCEPTED_ENGAGEMENT_EVENTS = {"opened", "clicked", "copied", "thumbs_up"}


def _normalize_engagement_event_type(event_type: str) -> str:
    return event_type.strip().lower()


def _build_dataframe_rows(
    all_docs: List[DocumentRow],
    r_map: Dict[str, RetrievalRow],
    e_map: Dict[str, int],
    ghost_ids: Set[str],
    obsolete_ids: Set[str],
    stale_ids: Set[str],
) -> List[Dict[str, Any]]:
    rows = []
    for doc in all_docs:
        doc_id = doc["doc_id"]
        retrievals = r_map[doc_id]["cnt"] if doc_id in r_map else 0
        engagements = e_map.get(doc_id, 0)
        engagement_rate = round(engagements / retrievals, 2) if retrievals > 0 else 0.0

        # Preserve the existing dataframe path's rounded threshold behavior.
        if doc_id in ghost_ids:
            status = "ghost"
        elif doc_id in obsolete_ids:
            status = "obsolete"
        elif doc_id in stale_ids:
            status = "stale"
        elif retrievals > 0 and engagement_rate < 0.15:
            status = "low_engagement"
        else:
            status = "healthy"

        rows.append({
            "doc_id": doc_id,
            "filename": doc["filename"],
            "retrievals": retrievals,
            "engagements": engagements,
            "engagement_rate": engagement_rate,
            "status": status,
        })

    return rows


def _build_report_rows(
    all_docs: List[DocumentRow],
    r_map: Dict[str, RetrievalRow],
    e_map: Dict[str, int],
    ghost_ids: Set[str],
    obsolete_ids: Set[str],
    stale_ids: Set[str],
    top_k: int,
) -> List[ReportRow]:
    rows: List[ReportRow] = []
    for doc in sorted(
        all_docs,
        key=lambda d: r_map.get(d["doc_id"], {"cnt": 0})["cnt"],
        reverse=True,
    )[:top_k]:
        doc_id = doc["doc_id"]
        retrievals = r_map[doc_id]["cnt"] if doc_id in r_map else 0
        engagements = e_map.get(doc_id, 0)
        engagement_rate = f"{engagements / retrievals * 100:.0f}%" if retrievals > 0 else "—"

        # Preserve the existing report path's unrounded threshold behavior.
        if doc_id in ghost_ids:
            status = "ghost"
        elif doc_id in obsolete_ids:
            status = "obsolete"
        elif doc_id in stale_ids:
            status = "stale"
        elif retrievals > 0 and (e_map.get(doc_id, 0) / retrievals) < 0.15:
            status = "low_engagement"
        else:
            status = "healthy"

        rows.append({
            "filename": doc["filename"],
            "retrievals": retrievals,
            "engagement_rate": engagement_rate,
            "status": status,
            "status_display": _STATUS_ICON[status],
        })

    return rows


def _build_report_summary(
    all_docs: List[DocumentRow],
    window_days: int,
    health: CorpusHealth,
) -> ReportSummary:
    return {
        "total_docs": len(all_docs),
        "window_days": window_days,
        "bloat_warning": health["bloat_warning"],
        "noise_pct": health["noise_estimate"] * 100,
        "ghosts": health["ghosts"],
        "obsolete": health["obsolete"],
        "duplicates": health["duplicates"],
        "stale": health["stale"],
        "recommendation": health["recommendation"],
    }


def _build_cleanup_payload(
    health: CorpusHealth,
    ghosts: List[GhostItem],
    obsolete: List[ObsoleteItem],
    stale: List[StaleItem],
    suspects: List[SuspectItem],
    ghost_threshold_days: int,
) -> CleanupPayload:
    def _section(items: List[Any]) -> CleanupSection:
        return {
            "count": len(items),
            "top5": items[:5],
            "overflow": max(0, len(items) - 5),
        }

    return {
        "total_docs": health["total_docs"],
        "noise_pct": health["noise_estimate"] * 100,
        "bloat_warning": health["bloat_warning"],
        "recommendation": health["recommendation"],
        "ghost_threshold_days": ghost_threshold_days,
        "ghosts": _section(ghosts),
        "obsolete": _section(obsolete),
        "stale": _section(stale),
        "suspects": _section(suspects),
    }


def _build_ghosts(
    all_docs: List[DocumentRow],
    retrieval_rows: List[RetrievalRow],
) -> List[GhostItem]:
    recent_ids = {row["doc_id"] for row in retrieval_rows}
    return [
        {"doc_id": doc["doc_id"], "filename": doc["filename"]}
        for doc in all_docs
        if doc["doc_id"] not in recent_ids
    ]


def _build_duplicate_pairs(
    embedding_rows: List[EmbeddingRow],
    threshold: float,
) -> List[DuplicatePair]:
    if not _SKLEARN:
        raise RuntimeError(
            "scikit-learn is required for duplicate detection. "
            "Install it with: pip install scikit-learn"
        )

    if len(embedding_rows) < 2:
        return []

    ids = [row["doc_id"] for row in embedding_rows]
    names = [row["filename"] for row in embedding_rows]
    vecs = np.array([_bytes_to_vec(row["embedding_vec"]) for row in embedding_rows])

    sim_matrix = cosine_similarity(vecs)
    pairs: List[DuplicatePair] = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if sim_matrix[i, j] >= threshold:
                pairs.append({
                    "doc_id_a": ids[i],
                    "filename_a": names[i],
                    "doc_id_b": ids[j],
                    "filename_b": names[j],
                    "similarity": round(float(sim_matrix[i, j]), 4),
                })

    return sorted(pairs, key=lambda x: x["similarity"], reverse=True)


def _build_obsolete_documents(
    all_docs: List[DocumentRow],
    obsolete_pattern: str,
) -> List[ObsoleteItem]:
    pattern = re.compile(obsolete_pattern, re.IGNORECASE)

    groups: Dict[str, List[DocumentRow]] = {}
    for doc in all_docs:
        base = pattern.sub("", doc["filename"]).strip(" -_.")
        groups.setdefault(base, []).append(doc)

    obsolete: List[ObsoleteItem] = []
    for docs in groups.values():
        if len(docs) < 2:
            continue

        def _version(doc: DocumentRow) -> int:
            match = pattern.search(doc["filename"])
            nums = re.findall(r"\d+", match.group()) if match else []
            return int(nums[0]) if nums else 0

        sorted_docs = sorted(docs, key=_version)
        newest = sorted_docs[-1]
        for old in sorted_docs[:-1]:
            obsolete.append({
                "doc_id": old["doc_id"],
                "filename": old["filename"],
                "superseded_by": newest["filename"],
            })

    return obsolete


def _build_stale_embeddings(
    all_docs: List[DocumentRow],
    stale_threshold_days: int,
) -> List[StaleItem]:
    threshold_secs = stale_threshold_days * 86_400
    stale: List[StaleItem] = []
    for doc in all_docs:
        src = doc["source_updated_at"]
        emb = doc["embedded_at"]
        if src is None or emb is None:
            continue
        gap = src - emb
        if gap > threshold_secs:
            stale.append({
                "doc_id": doc["doc_id"],
                "filename": doc["filename"],
                "source_updated": _ts_to_date(src),
                "last_embedded": _ts_to_date(emb),
                "days_behind": int(gap // 86_400),
            })

    return sorted(stale, key=lambda x: x["days_behind"], reverse=True)


def _build_suspects(
    all_docs: List[DocumentRow],
    retrieval_rows: List[RetrievalRow],
    engagement_rows: List[EngagementRow],
) -> List[SuspectItem]:
    doc_map = {doc["doc_id"]: doc for doc in all_docs}
    retrieval_map = {row["doc_id"]: row for row in retrieval_rows}
    engagement_map = {row["doc_id"]: row["cnt"] for row in engagement_rows}

    suspects: List[SuspectItem] = []
    for doc_id, retrieval in retrieval_map.items():
        total_retrievals = retrieval["cnt"]
        if total_retrievals < 5:
            continue

        engagement_rate = engagement_map.get(doc_id, 0) / total_retrievals
        if engagement_rate < 0.15:
            doc = doc_map.get(doc_id)
            suspects.append({
                "doc_id": doc_id,
                "filename": doc["filename"] if doc else doc_id,
                "retrievals": total_retrievals,
                "engagement_rate": round(engagement_rate, 3),
            })

    return sorted(suspects, key=lambda x: x["retrievals"], reverse=True)


def _build_mean_reciprocal_rank(
    retrieval_rows: List[RetrievalRow],
    engagement_rows: List[EngagementRow],
) -> float:
    """Compute the Phase 22 MRR proxy from doc-level retrieval and engagement aggregates."""
    if not retrieval_rows or not engagement_rows:
        return 0.0

    engaged_docs = {
        row["doc_id"]
        for row in engagement_rows
        if int(row["cnt"]) > 0
    }
    reciprocal_ranks: List[float] = []
    for row in retrieval_rows:
        if row["doc_id"] not in engaged_docs:
            continue

        avg_rank = row.get("avg_rank")
        if avg_rank is None:
            continue

        rank_value = float(avg_rank)
        if rank_value <= 0:
            continue

        reciprocal_ranks.append(1.0 / rank_value)

    if not reciprocal_ranks:
        return 0.0

    return round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4)


def _build_acceptance_rate(
    event_rows: List[EngagementEventRow],
) -> float:
    if not event_rows:
        return 0.0

    accepted_count = 0
    total_count = 0
    for row in event_rows:
        cnt = int(row["cnt"])
        total_count += cnt
        if _normalize_engagement_event_type(row["event_type"]) in _ACCEPTED_ENGAGEMENT_EVENTS:
            accepted_count += cnt

    if total_count == 0:
        return 0.0

    return round(accepted_count / total_count, 2)


def _build_low_confidence_queries(
    query_rows: List[QueryRow],
    threshold: float,
) -> List[LowConfidenceQueryRow]:
    low_confidence = [
        row.copy()
        for row in query_rows
        if row["cnt"] > 0
        and row["max_score"] is not None
        and float(row["max_score"]) < threshold
    ]
    return sorted(
        low_confidence,
        key=lambda row: (
            float(row["max_score"]) if row["max_score"] is not None else float("inf"),
            -int(row["cnt"]),
            row["query_hash"],
        ),
    )


def _build_zero_result_queries(
    query_rows: List[QueryAttemptRow],
) -> List[ZeroResultQueryRow]:
    zero_result = [row.copy() for row in query_rows if int(row["result_cnt"]) == 0]
    return sorted(zero_result, key=lambda row: row["query_hash"])


def _build_query_rate(
    query_rows: List[dict[str, Any]],
    filtered_rows: List[dict[str, Any]],
) -> float:
    if not query_rows:
        return 0.0
    return round(len(filtered_rows) / len(query_rows), 2)


def _nearest_rank_percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, ceil((percentile / 100.0) * len(ordered)))
    return float(ordered[rank - 1])


def _build_token_distribution(values: Iterable[int | float]) -> TokenDistribution:
    ordered = [float(value) for value in values if value is not None]
    count = len(ordered)
    if count == 0:
        return {
            "count": 0,
            "total": 0,
            "avg": 0.0,
            "p50": None,
            "p95": None,
            "max": None,
        }

    total = int(sum(ordered))
    return {
        "count": count,
        "total": total,
        "avg": round(total / count, 2),
        "p50": _nearest_rank_percentile(ordered, 50.0),
        "p95": _nearest_rank_percentile(ordered, 95.0),
        "max": float(max(ordered)),
    }


def _build_latency_distribution(values: Iterable[int | float]) -> LatencyDistribution:
    ordered = [float(value) for value in values if value is not None]
    count = len(ordered)
    if count == 0:
        return {
            "count": 0,
            "avg_ms": 0.0,
            "p50_ms": None,
            "p95_ms": None,
            "max_ms": None,
        }

    return {
        "count": count,
        "avg_ms": round(sum(ordered) / count, 2),
        "p50_ms": _nearest_rank_percentile(ordered, 50.0),
        "p95_ms": _nearest_rank_percentile(ordered, 95.0),
        "max_ms": float(max(ordered)),
    }


_CANONICAL_COMPONENT_TYPES = (
    "system_prompt",
    "vector_db",
    "chat_history",
    "web_search",
    "user_input",
    "file_attachment",
    "tool_result",
    "other",
)

_COMPONENT_ALIASES = {
    "vector_db_context": "vector_db",
    "vector-db": "vector_db",
    "vector db": "vector_db",
    "file_attachments": "file_attachment",
    "tool_results": "tool_result",
    "system": "system_prompt",
}

_SERVING_STAGE_FIELDS = (
    "retrieval_ms",
    "rerank_ms",
    "generation_ms",
    "queue_ms",
)

_SESSION_REUSE_COMPONENT_TYPES = {
    "vector_db",
    "web_search",
    "file_attachment",
    "tool_result",
    "other",
}


def _normalize_component_type(component_type: str | None) -> str:
    if component_type is None:
        return "other"
    normalized = component_type.strip().lower().replace(" ", "_").replace("-", "_")
    normalized = _COMPONENT_ALIASES.get(normalized, normalized)
    return normalized if normalized in _CANONICAL_COMPONENT_TYPES else "other"


def _build_workload_report(
    traces: Iterable[RagRequestTraceRow],
    window_days: int,
    long_context_threshold: int = 8000,
) -> WorkloadReportPayload:
    trace_rows = list(traces)
    request_count = len(trace_rows)
    captured_at_values = sorted(float(trace["captured_at"]) for trace in trace_rows)
    first_captured_at = captured_at_values[0] if captured_at_values else None
    last_captured_at = captured_at_values[-1] if captured_at_values else None
    if request_count == 0:
        requests_per_hour = 0.0
        peak_requests_per_minute = 0
    else:
        span_hours = 1.0
        if first_captured_at is not None and last_captured_at is not None:
            span_hours = max((last_captured_at - first_captured_at) / 3600.0, 1.0)
        requests_per_hour = round(request_count / span_hours, 2)
        minute_buckets: Dict[int, int] = {}
        for captured_at in captured_at_values:
            bucket = int(captured_at // 60)
            minute_buckets[bucket] = minute_buckets.get(bucket, 0) + 1
        peak_requests_per_minute = max(minute_buckets.values(), default=0)

    input_token_values = [
        int(trace["input_token_count"])
        for trace in trace_rows
        if trace["input_token_count"] is not None
    ]
    output_token_values = [
        int(trace["output_token_count"])
        for trace in trace_rows
        if trace["output_token_count"] is not None
    ]
    long_context_count = sum(
        1
        for trace in trace_rows
        if trace["input_token_count"] is not None
        and int(trace["input_token_count"]) >= long_context_threshold
    )
    long_context_rate = round(long_context_count / request_count, 2) if request_count else 0.0

    component_stats: Dict[str, Dict[str, float | int]] = {
        component_type: {"request_count": 0, "token_count": 0}
        for component_type in _CANONICAL_COMPONENT_TYPES
    }
    for trace in trace_rows:
        seen_types: set[str] = set()
        for component in trace["components"]:
            component_type = _normalize_component_type(component.get("type"))
            token_count = int(component["token_count"]) if component["token_count"] is not None else 0
            component_stats[component_type]["token_count"] += token_count
            if component_type not in seen_types:
                component_stats[component_type]["request_count"] += 1
                seen_types.add(component_type)

    total_component_tokens = sum(int(stats["token_count"]) for stats in component_stats.values())
    components: list[WorkloadComponentSummary] = []
    for component_type in _CANONICAL_COMPONENT_TYPES:
        stats = component_stats[component_type]
        component_request_count = int(stats["request_count"])
        component_token_count = int(stats["token_count"])
        components.append({
            "component_type": component_type,
            "request_count": component_request_count,
            "token_count": component_token_count,
            "request_share": round(component_request_count / request_count, 4) if request_count else 0.0,
            "token_share": round(component_token_count / total_component_tokens, 4) if total_component_tokens else 0.0,
        })

    return {
        "traffic": {
            "request_count": request_count,
            "window_days": window_days,
            "first_captured_at": first_captured_at,
            "last_captured_at": last_captured_at,
            "requests_per_hour": requests_per_hour,
            "peak_requests_per_minute": peak_requests_per_minute,
        },
        "tokens": {
            "input_tokens": _build_token_distribution(input_token_values),
            "output_tokens": _build_token_distribution(output_token_values),
            "long_context_threshold": long_context_threshold,
            "long_context_count": long_context_count,
            "long_context_rate": long_context_rate,
        },
        "components": components,
    }


def _build_serving_report(traces: Iterable[RagRequestTraceRow]) -> ServingReportPayload:
    trace_rows = list(traces)
    request_count = len(trace_rows)
    timeout_count = sum(1 for trace in trace_rows if bool(trace["timeout"]))
    error_count = sum(1 for trace in trace_rows if trace["error"] is not None)

    ttft_values = [trace["timings"].get("ttft_ms") for trace in trace_rows if trace["timings"].get("ttft_ms") is not None]
    tpot_values = [trace["timings"].get("tpot_ms") for trace in trace_rows if trace["timings"].get("tpot_ms") is not None]
    total_latency_values = [
        trace["timings"].get("total_latency_ms")
        for trace in trace_rows
        if trace["timings"].get("total_latency_ms") is not None
    ]

    stage_latencies: dict[str, LatencyDistribution] = {}
    stage_values_by_name: dict[str, list[float]] = {stage: [] for stage in _SERVING_STAGE_FIELDS}
    slow_totals: dict[str, dict[str, float | int]] = {
        stage: {"count": 0, "total_ms": 0.0}
        for stage in _SERVING_STAGE_FIELDS
    }
    for trace in trace_rows:
        stage_candidates: list[tuple[str, float]] = []
        timings = trace["timings"]
        for stage in _SERVING_STAGE_FIELDS:
            value = timings.get(stage)
            if value is None:
                continue
            numeric = float(value)
            stage_values_by_name[stage].append(numeric)
            stage_candidates.append((stage, numeric))
        if stage_candidates:
            chosen_stage, chosen_value = sorted(stage_candidates, key=lambda item: (-item[1], item[0]))[0]
            slow_totals[chosen_stage]["count"] += 1
            slow_totals[chosen_stage]["total_ms"] += chosen_value

    for stage in _SERVING_STAGE_FIELDS:
        stage_latencies[stage] = _build_latency_distribution(stage_values_by_name[stage])

    slow_request_contributors: list[ServingSlowContributor] = []
    for stage in _SERVING_STAGE_FIELDS:
        count = int(slow_totals[stage]["count"])
        if count == 0:
            continue
        slow_request_contributors.append({
            "stage": stage,
            "count": count,
            "avg_ms": round(float(slow_totals[stage]["total_ms"]) / count, 2),
        })
    slow_request_contributors.sort(
        key=lambda row: (-row["count"], -row["avg_ms"], row["stage"])
    )

    return {
        "request_count": request_count,
        "timeout_count": timeout_count,
        "timeout_rate": round(timeout_count / request_count, 2) if request_count else 0.0,
        "error_count": error_count,
        "error_rate": round(error_count / request_count, 2) if request_count else 0.0,
        "ttft_ms": _build_latency_distribution(ttft_values),
        "tpot_ms": _build_latency_distribution(tpot_values),
        "total_latency_ms": _build_latency_distribution(total_latency_values),
        "stage_latencies": stage_latencies,
        "slow_request_contributors": slow_request_contributors,
    }


def _normalized_session_id(session_id: str | None) -> str | None:
    if session_id is None:
        return None
    normalized = session_id.strip()
    return normalized or None


def _ordered_session_traces(
    traces: list[RagRequestTraceRow],
) -> list[RagRequestTraceRow]:
    return sorted(traces, key=lambda trace: (float(trace["captured_at"]), int(trace["trace_id"])))


def _first_last_growth(values: Iterable[int | None]) -> tuple[int | None, int | None, int | None]:
    endpoints = [int(value) for value in values if value is not None]
    if not endpoints:
        return None, None, None

    first = endpoints[0]
    last = endpoints[-1]
    return first, last, last - first


def _chat_history_token_count(trace: RagRequestTraceRow) -> int | None:
    total = 0
    found = False
    for component in trace.get("components", []):
        if _normalize_component_type(component.get("type")) != "chat_history":
            continue
        token_count = component.get("token_count")
        if token_count is None:
            continue
        total += int(token_count)
        found = True
    return total if found else None


def _build_session_detail(
    session_id: str,
    traces: list[RagRequestTraceRow],
) -> dict[str, Any]:
    ordered_traces = _ordered_session_traces(traces)
    first_trace = ordered_traces[0]
    last_trace = ordered_traces[-1]
    first_captured_at = float(first_trace["captured_at"])
    last_captured_at = float(last_trace["captured_at"])
    duration_seconds = round(last_captured_at - first_captured_at, 2)

    input_tokens_first, input_tokens_last, input_token_growth = _first_last_growth(
        trace.get("input_token_count") for trace in ordered_traces
    )
    chat_tokens_first, chat_tokens_last, chat_token_growth = _first_last_growth(
        _chat_history_token_count(trace) for trace in ordered_traces
    )

    return {
        "session_id": session_id,
        "request_count": len(ordered_traces),
        "first_captured_at": first_captured_at,
        "last_captured_at": last_captured_at,
        "duration_seconds": duration_seconds,
        "input_tokens_first": input_tokens_first,
        "input_tokens_last": input_tokens_last,
        "input_token_growth": input_token_growth,
        "chat_history_tokens_first": chat_tokens_first,
        "chat_history_tokens_last": chat_tokens_last,
        "chat_history_token_growth": chat_token_growth,
    }


def _session_reuse_keys(component: RagRequestComponent) -> list[str]:
    component_type = _normalize_component_type(component.get("type"))
    if component_type not in _SESSION_REUSE_COMPONENT_TYPES:
        return []

    refs = component.get("refs")
    if isinstance(refs, list) and refs:
        return [
            json.dumps(ref, sort_keys=True, separators=(",", ":"))
            for ref in refs
        ]

    content_hash = component.get("content_hash")
    if content_hash is not None:
        return [str(content_hash)]

    return []


def _build_context_reuse_rows(
    session_groups: dict[str, list[RagRequestTraceRow]],
) -> list[ContextReuseItem]:
    context_reuse: list[ContextReuseItem] = []
    for session_id, traces in session_groups.items():
        ordered_traces = _ordered_session_traces(traces)
        session_request_count = len(ordered_traces)
        reuse_stats: dict[tuple[str, str], dict[str, float | int]] = {}

        for trace in ordered_traces:
            request_keys: set[tuple[str, str]] = set()
            for component in trace.get("components", []):
                component_type = _normalize_component_type(component.get("type"))
                for reuse_key in _session_reuse_keys(component):
                    request_keys.add((component_type, reuse_key))

            for reuse_id in request_keys:
                if reuse_id not in reuse_stats:
                    reuse_stats[reuse_id] = {
                        "first_seen_at": float(trace["captured_at"]),
                        "request_count": 0,
                    }
                reuse_stats[reuse_id]["request_count"] = int(reuse_stats[reuse_id]["request_count"]) + 1

        for (component_type, reuse_key), stats in reuse_stats.items():
            request_count = int(stats["request_count"])
            if request_count < 2:
                continue
            context_reuse.append({
                "session_id": session_id,
                "component_type": component_type,
                "reuse_key": reuse_key,
                "first_seen_at": float(stats["first_seen_at"]),
                "request_count": request_count,
                "reuse_count": request_count - 1,
                "request_share": round(request_count / session_request_count, 4),
            })

    return sorted(
        context_reuse,
        key=lambda row: (row["session_id"], row["component_type"], row["reuse_key"]),
    )


def _build_session_report(traces: Iterable[RagRequestTraceRow]) -> SessionReportPayload:
    trace_rows = list(traces)
    session_groups: dict[str, list[RagRequestTraceRow]] = {}
    unsessioned_request_count = 0

    for trace in trace_rows:
        session_id = _normalized_session_id(trace.get("session_id"))
        if session_id is None:
            unsessioned_request_count += 1
            continue
        session_groups.setdefault(session_id, []).append(trace)

    for session_id, session_traces in list(session_groups.items()):
        session_groups[session_id] = _ordered_session_traces(session_traces)

    sessions = [
        _build_session_detail(session_id, session_traces)
        for session_id, session_traces in sorted(
            session_groups.items(),
            key=lambda item: (float(item[1][0]["captured_at"]), item[0]),
        )
    ]

    session_count = len(sessions)
    turn_counts = [session["request_count"] for session in sessions]
    durations = [session["duration_seconds"] for session in sessions]
    single_turn_session_count = sum(1 for count in turn_counts if count == 1)
    multi_turn_session_count = sum(1 for count in turn_counts if count > 1)

    return {
        "summary": {
            "request_count": len(trace_rows),
            "session_count": session_count,
            "unsessioned_request_count": unsessioned_request_count,
            "single_turn_session_count": single_turn_session_count,
            "multi_turn_session_count": multi_turn_session_count,
            "avg_turns_per_session": round(sum(turn_counts) / session_count, 2) if session_count else 0.0,
            "max_turns_per_session": max(turn_counts, default=0),
            "follow_up_rate": round(multi_turn_session_count / session_count, 2) if session_count else 0.0,
            "avg_session_duration_seconds": round(sum(durations) / session_count, 2) if session_count else 0.0,
            "max_session_duration_seconds": max(durations, default=0.0),
        },
        "sessions": sessions,
        "context_reuse": _build_context_reuse_rows(session_groups),
    }


def _build_corpus_health(
    all_docs: List[DocumentRow],
    ghosts: List[GhostItem],
    obsolete: List[ObsoleteItem],
    stale: List[StaleItem],
    duplicate_pairs: List[DuplicatePair],
) -> CorpusHealth:
    total = len(all_docs)
    if total == 0:
        return {
            "total_docs": 0,
            "ghosts": 0,
            "obsolete": 0,
            "stale": 0,
            "duplicates": 0,
            "noise_estimate": 0.0,
            "bloat_warning": False,
            "recommendation": "Corpus looks healthy.",
        }

    ghost_ids = {doc["doc_id"] for doc in ghosts}
    obsolete_ids = {doc["doc_id"] for doc in obsolete}
    stale_ids = {doc["doc_id"] for doc in stale}
    duplicate_ids = {pair["doc_id_a"] for pair in duplicate_pairs} | {
        pair["doc_id_b"] for pair in duplicate_pairs
    }

    noisy_ids = ghost_ids | obsolete_ids | stale_ids | duplicate_ids
    noise_ratio = round(len(noisy_ids) / total, 2) if total > 0 else 0.0

    return {
        "total_docs": total,
        "ghosts": len(ghost_ids),
        "obsolete": len(obsolete_ids),
        "stale": len(stale_ids),
        "duplicates": len(duplicate_ids),
        "noise_estimate": noise_ratio,
        "bloat_warning": noise_ratio > 0.20,
        "recommendation": (
            f"Consider pruning ~{int(noise_ratio * total)} low-signal documents."
            if noise_ratio > 0.20 else "Corpus looks healthy."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Corpulse
# ─────────────────────────────────────────────────────────────────────────────

class Corpulse:
    """
    Lightweight RAG corpus analytics.

    Usage::

        corp = Corpulse()
        results = vectordb.search(query)
        corp.log_retrieval(results, query=query)
        corp.log_engagement("my-doc-id", event="opened")
        corp.report()
    """

    def __init__(
        self,
        db_path: str = "./corpulse.db",
        backend: StorageBackend | None = None,
        ghost_threshold_days: int = 30,
        duplicate_threshold: float = 0.92,
        stale_threshold_days: int = 14,
        obsolete_pattern: str = r"v\d+",
        top_k_report: int = 20,
        low_confidence_threshold: float = 0.8,
    ):
        """Initialise a Corpulse instance backed by a SQLite database.

        Args:
            db_path: Path to the SQLite database file. Created if it does
                not exist. Defaults to ``"./corpulse.db"``.
            backend: Explicit storage backend instance. When omitted,
                corpulse uses ``SQLiteBackend(db_path)``.
            ghost_threshold_days: Number of days without retrieval before a
                document is flagged as a ghost. Defaults to 30.
            duplicate_threshold: Cosine similarity threshold for duplicate
                detection. Pairs above this value are flagged. Defaults to 0.92.
            stale_threshold_days: Number of days of source-vs-embedding lag
                before an embedding is flagged as stale. Defaults to 14.
            obsolete_pattern: Regex pattern used to detect version tokens in
                filenames (e.g. ``v1``, ``v2``). Defaults to ``r"v\\d+"``.
            top_k_report: Maximum number of documents shown in ``report()``
                output. Defaults to 20.
            low_confidence_threshold: Top-score cutoff used by
                ``low_confidence_rate()`` and ``get_low_confidence_queries()``.
        """
        if backend is not None and db_path != "./corpulse.db":
            raise ValueError("Pass either the default db_path or an explicit backend, not both")

        self.db = backend if backend is not None else SQLiteBackend(db_path)
        self.ghost_threshold_days = ghost_threshold_days
        self.duplicate_threshold = duplicate_threshold
        self.stale_threshold_days = stale_threshold_days
        self.obsolete_pattern = obsolete_pattern
        self.top_k_report = top_k_report
        self.low_confidence_threshold = low_confidence_threshold

    def close(self) -> None:
        """Close the underlying storage backend."""
        self.db.close()

    def __enter__(self) -> Corpulse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ── ingestion ─────────────────────────────────────────────────────────────

    def log_retrieval(
        self,
        results: list[dict[str, Any]],
        query: str = "",
    ) -> None:
        """
        Call this right after your vector DB search.

        Each item in *results* must contain at least ``doc_id``.
        Optional keys: ``filename``, ``score`` (float), ``embedding`` (list/array).

        Example::

            results = [
                {"doc_id": "abc123", "filename": "guide.md", "score": 0.91},
                {"doc_id": "def456", "filename": "faq.md",   "score": 0.87},
            ]
            corp.log_retrieval(results, query="how to install?")

        Args:
            results: List of dicts, each containing at least ``"doc_id"``.
                Optional keys: ``"filename"``, ``"score"`` (float),
                ``"embedding"`` (list or numpy array).
            query: The search query string. Used for query deduplication
                via hashing. Defaults to ``""``.

        Returns:
            None.
        """
        qhash = _hash_query(query)
        ts = _now()
        self.db.insert_query_attempt(qhash, len(results), ts)

        for rank, item in enumerate(results, start=1):
            doc_id   = item["doc_id"]
            filename = item.get("filename", doc_id)
            score    = float(item.get("score", 0.0))
            vec      = item.get("embedding")

            self.db.upsert_document(
                doc_id=doc_id,
                filename=filename,
                embedding=_vec_to_bytes(vec) if vec is not None else None,
                embedded_at=ts if vec is not None else None,
            )
            self.db.insert_retrieval(doc_id, qhash, rank, score, ts)

    def log_engagement(
        self,
        doc_id: str,
        event: str = "opened",
    ) -> None:
        """
        Call this when a user acts on a retrieved document.

        *event* is a free-form label — e.g. "opened", "copied", "thumbs_up".

        Args:
            doc_id: Identifier of the document the user interacted with.
            event: Free-form label for the interaction type.
                Defaults to ``"opened"``.
        """
        self.db.insert_engagement(doc_id, event, _now())

    def log_generation_trace(
        self,
        prompt_text: str,
        retrieved_context_refs: list[dict[str, Any]],
        final_answer_text: str,
        evaluation_labels: list[str] | None = None,
    ) -> None:
        """
        Record an append-only generation trace for future evaluation metrics.

        Args:
            prompt_text: Prompt or query text that initiated generation.
            retrieved_context_refs: Ordered references to the retrieved
                context used for generation.
            final_answer_text: Final generated answer text.
            evaluation_labels: Optional evaluation labels or judgments
                associated with the generation trace.
        """
        self.db.insert_generation_trace(
            prompt_text=prompt_text,
            retrieved_context_refs=retrieved_context_refs,
            final_answer_text=final_answer_text,
            evaluation_labels=evaluation_labels,
            captured_at=_now(),
        )

    def log_rag_request(
        self,
        session_id: str | None = None,
        query: str | None = None,
        request_id: str | None = None,
        components: list[RagRequestComponent] | None = None,
        input_token_count: int | None = None,
        output_token_count: int | None = None,
        timings: RagRequestTimings | None = None,
        timeout: bool = False,
        error: str | None = None,
    ) -> None:
        """
        Record an append-only RAG request trace for observability and replay.

        Args:
            session_id: Optional session or conversation identifier.
            query: Optional raw query text. When provided, corpulse stores
                a stable hash alongside the trace.
            request_id: Optional caller-provided request identifier.
            components: Structured request components such as system prompt,
                vector DB context, chat history, web search, or user input.
            input_token_count: Optional total input token count.
            output_token_count: Optional total output token count.
            timings: Optional stage timing payload in milliseconds.
            timeout: True when the request timed out.
            error: Optional error string or code.
        """
        self.db.insert_rag_request_trace(
            request_id=request_id,
            session_id=session_id,
            query_text=query,
            query_hash=_hash_query(query) if query is not None else None,
            input_token_count=input_token_count,
            output_token_count=output_token_count,
            components=deepcopy(components) if components is not None else [],
            timings=deepcopy(timings) if timings is not None else {},
            timeout=timeout,
            error=error,
            captured_at=_now(),
        )

    def log_source_update(
        self,
        doc_id: str,
        updated_at: float | None = None,
    ) -> None:
        """
        Notify corpulse that a source file was modified.

        *updated_at* defaults to now if omitted.

        Args:
            doc_id: Identifier of the document whose source was modified.
            updated_at: Unix timestamp of the modification. Defaults to
                the current time if ``None``.
        """
        self.db.update_source_timestamp(doc_id, updated_at or _now())

    def register_document(
        self,
        doc_id: str,
        filename: str,
        embedding: list | np.ndarray | None = None,
    ) -> None:
        """
        Optionally pre-register documents with their embeddings so duplicate
        detection works even before the first retrieval.

        Args:
            doc_id: Unique identifier for the document.
            filename: Human-readable filename or label.
            embedding: Optional embedding vector as a list or numpy array.
                When provided, enables duplicate detection for this document
                even before its first retrieval.
        """
        self.db.upsert_document(
            doc_id=doc_id,
            filename=filename,
            embedding=_vec_to_bytes(embedding) if embedding is not None else None,
            embedded_at=_now() if embedding is not None else None,
        )

    def delete_document(self, doc_id: str) -> None:
        """Delete a document and its associated retrieval and engagement history."""
        self.db.delete_document(doc_id)

    def delete_generation_traces(
        self,
        *,
        trace_ids: list[int] | None = None,
        prompt_text: str | None = None,
        evaluation_label: str | None = None,
    ) -> None:
        """Delete generation traces matching the supplied identifiers or demo markers."""
        self.db.delete_generation_traces(
            trace_ids=trace_ids,
            prompt_text=prompt_text,
            evaluation_label=evaluation_label,
        )

    # ── analysis ──────────────────────────────────────────────────────────────

    def get_ghosts(self) -> List[GhostItem]:
        """Documents not retrieved in the last *ghost_threshold_days* days.

        Returns:
            List of dicts with keys: ``doc_id``, ``filename``.
        """
        cutoff = _days_ago(self.ghost_threshold_days)
        all_docs = self.db.all_documents()
        retrieval_rows = self.db.retrieval_counts(since=cutoff)
        return _build_ghosts(all_docs, retrieval_rows)

    def get_duplicates(
        self,
        threshold: float | None = None,
    ) -> List[DuplicatePair]:
        """
        Pairs of documents whose embedding vectors are cosine-similar above
        *threshold* — likely redundant content competing for the same queries.

        Requires scikit-learn and stored embeddings.

        Args:
            threshold: Cosine similarity threshold above which documents are
                considered duplicates. Defaults to ``duplicate_threshold``
                if ``None``.

        Returns:
            List of dicts with keys: ``doc_id_a``, ``filename_a``,
            ``doc_id_b``, ``filename_b``, ``similarity`` (float).
            Sorted by similarity descending.

        Raises:
            RuntimeError: If scikit-learn is not installed.
        """
        threshold = threshold or self.duplicate_threshold
        rows = self.db.all_embeddings()
        return _build_duplicate_pairs(rows, threshold)

    def get_obsolete(self) -> List[ObsoleteItem]:
        """
        Documents likely superseded by a newer version of the same file,
        detected via the *obsolete_pattern* (default: version numbers like v1, v2).

        e.g. if both "api-reference-v1.md" and "api-reference-v2.md" exist,
        v1 is flagged as obsolete.

        Returns:
            List of dicts with keys: ``doc_id``, ``filename``,
            ``superseded_by`` (filename of the newer version).
        """
        all_docs = self.db.all_documents()
        return _build_obsolete_documents(all_docs, self.obsolete_pattern)

    def get_stale_embeddings(self) -> List[StaleItem]:
        """
        Documents where the source file was updated more than
        *stale_threshold_days* days after the last embedding.

        Returns:
            List of dicts with keys: ``doc_id``, ``filename``,
            ``source_updated`` (date string), ``last_embedded`` (date string),
            ``days_behind`` (int). Sorted by days_behind descending.
        """
        all_docs = self.db.all_documents()
        return _build_stale_embeddings(all_docs, self.stale_threshold_days)

    def get_suspects(self, window_days: int | None = None) -> List[SuspectItem]:
        """
        Documents with high retrieval count but low engagement rate —
        retrieved often but users don't act on them. Good re-chunking candidates.

        Args:
            window_days: Lookback window in days. Defaults to
                ``ghost_threshold_days`` if ``None``.

        Returns:
            List of dicts with keys: ``doc_id``, ``filename``,
            ``retrievals`` (int), ``engagement_rate`` (float 0-1).
            Sorted by retrievals descending.
        """
        since = _days_ago(window_days or self.ghost_threshold_days)
        all_docs = self.db.all_documents()
        retrieval_rows = self.db.retrieval_counts(since=since)
        engagement_rows = self.db.engagement_counts(since=since)
        return _build_suspects(all_docs, retrieval_rows, engagement_rows)

    def mean_reciprocal_rank(self, window_days: int | None = None) -> float:
        """Return the Phase 22 proxy MRR from retrieval rank and engagement overlap."""
        since = _days_ago(window_days or self.ghost_threshold_days)
        retrieval_rows = self.db.retrieval_counts(since=since)
        engagement_rows = self.db.engagement_counts(since=since)
        return _build_mean_reciprocal_rank(retrieval_rows, engagement_rows)

    def acceptance_rate(self, window_days: int | None = None) -> float:
        """Return the share of accepted engagement rows in the lookback window.

        Accepted rows are those whose normalized ``event_type`` matches the
        fixed v1.5 allowlist.
        """
        since = _days_ago(window_days or self.ghost_threshold_days)
        event_rows = self.db.engagement_event_counts(since=since)
        return _build_acceptance_rate(event_rows)

    def get_generation_traces(self, window_days: int | None = None) -> list[GenerationTraceRow]:
        """
        Return append-only generation traces from the lookback window.

        Args:
            window_days: Lookback window in days. Defaults to
                ``ghost_threshold_days`` if ``None``.
        """
        since = _days_ago(window_days or self.ghost_threshold_days)
        return self.db.generation_traces(since=since)

    def get_rag_request_traces(self, window_days: int | None = None) -> list[RagRequestTraceRow]:
        """
        Return append-only RAG request traces from the lookback window.

        Args:
            window_days: Lookback window in days. Defaults to
                ``ghost_threshold_days`` if ``None``.
        """
        since = _days_ago(window_days or self.ghost_threshold_days)
        return self.db.rag_request_traces(since=since)

    def export_rag_request_traces_jsonl(
        self,
        destination,
        *,
        window_days: int | None = None,
        include_raw_text: bool = False,
        include_component_metadata: bool = False,
    ) -> int:
        """
        Export append-only RAG request traces as JSONL.

        Args:
            destination: Path or text stream to receive one JSON object per line.
            window_days: Lookback window in days. Defaults to
                ``ghost_threshold_days`` if ``None``.
            include_raw_text: True to include raw query text in exported rows.
            include_component_metadata: True to include component metadata.

        Returns:
            Number of traces written.
        """
        traces = self.get_rag_request_traces(window_days=window_days)
        needs_close = False
        if hasattr(destination, "write"):
            writer = destination
        else:
            writer = Path(destination).open("w", encoding="utf-8")
            needs_close = True
        try:
            for trace in traces:
                writer.write(
                    serialize_rag_request_trace_jsonl(
                        trace,
                        include_raw_text=include_raw_text,
                        include_component_metadata=include_component_metadata,
                    )
                    + "\n"
                )
        finally:
            if needs_close:
                writer.close()
        return len(traces)

    def import_rag_request_traces_jsonl(
        self,
        source,
        *,
        strict: bool = True,
    ) -> RagRequestTraceImportResult:
        """
        Import RAG request traces from JSONL into the active backend.

        Args:
            source: Path or text stream providing one JSON object per line.
            strict: True to fail fast on invalid records. False to continue and
                accumulate errors in the returned result.

        Returns:
            Structured import counts and error messages.
        """
        needs_close = False
        if hasattr(source, "read"):
            reader = source
        else:
            reader = Path(source).open("r", encoding="utf-8")
            needs_close = True
        total = imported = skipped_duplicates = invalid = 0
        errors: list[str] = []
        existing = existing_rag_request_trace_fingerprints(self.get_rag_request_traces(window_days=None))
        try:
            for line_number, line in enumerate(reader, start=1):
                if not line.strip():
                    continue
                total += 1
                try:
                    trace = parse_rag_request_trace_jsonl_line(
                        line,
                        line_number=line_number,
                        strict=strict,
                    )
                except ValueError as exc:
                    invalid += 1
                    message = str(exc)
                    errors.append(message)
                    if strict:
                        raise
                    continue
                if rag_request_trace_fingerprint(trace) in existing:
                    skipped_duplicates += 1
                    continue
                self.db.insert_rag_request_trace(
                    request_id=trace["request_id"],
                    session_id=trace["session_id"],
                    query_text=trace["query_text"],
                    query_hash=trace["query_hash"],
                    input_token_count=trace["input_token_count"],
                    output_token_count=trace["output_token_count"],
                    components=deepcopy(trace["components"]),
                    timings=deepcopy(trace["timings"]),
                    timeout=trace["timeout"],
                    error=trace["error"],
                    captured_at=trace["captured_at"],
                )
                existing.add(rag_request_trace_fingerprint(trace))
                imported += 1
        finally:
            if needs_close:
                reader.close()
        return {
            "total": total,
            "imported": imported,
            "skipped_duplicates": skipped_duplicates,
            "invalid": invalid,
            "errors": errors,
        }

    def _query_rows(self, window_days: int | None = None) -> List[QueryRow]:
        since = _days_ago(window_days or self.ghost_threshold_days)
        return self.db.query_counts(since=since)

    def _query_attempt_rows(self, window_days: int | None = None) -> List[QueryAttemptRow]:
        since = _days_ago(window_days or self.ghost_threshold_days)
        return self.db.query_attempt_counts(since=since)

    def low_confidence_rate(
        self,
        window_days: int | None = None,
        threshold: float | None = None,
    ) -> float:
        """Return the share of queries whose top score falls below *threshold*."""
        query_rows = self._query_rows(window_days)
        confidence_threshold = threshold if threshold is not None else self.low_confidence_threshold
        low_confidence_rows = _build_low_confidence_queries(query_rows, confidence_threshold)
        return _build_query_rate(
            [row for row in query_rows if int(row["cnt"]) > 0],
            low_confidence_rows,
        )

    def get_low_confidence_queries(
        self,
        window_days: int | None = None,
        threshold: float | None = None,
    ) -> List[LowConfidenceQueryRow]:
        """Return query aggregates whose top score falls below *threshold*."""
        query_rows = self._query_rows(window_days)
        confidence_threshold = threshold if threshold is not None else self.low_confidence_threshold
        return _build_low_confidence_queries(query_rows, confidence_threshold)

    def zero_result_rate(self, window_days: int | None = None) -> float:
        """Return the share of query aggregates recorded with zero results."""
        query_rows = self._query_attempt_rows(window_days)
        zero_result_rows = _build_zero_result_queries(query_rows)
        return _build_query_rate(query_rows, zero_result_rows)

    def get_zero_result_queries(
        self,
        window_days: int | None = None,
    ) -> List[ZeroResultQueryRow]:
        """Return query aggregates recorded with zero results."""
        query_rows = self._query_attempt_rows(window_days)
        return _build_zero_result_queries(query_rows)

    def corpus_health(self) -> CorpusHealth:
        """
        High-level corpus noise estimate and bloat warning.

        Returns:
            Dict with keys: ``total_docs`` (int), ``ghosts`` (int),
            ``obsolete`` (int), ``stale`` (int), ``duplicates`` (int),
            ``noise_estimate`` (float 0-1), ``bloat_warning`` (bool),
            ``recommendation`` (str).
        """
        all_docs = self.db.all_documents()
        ghosts = self.get_ghosts()
        obsolete = self.get_obsolete()
        stale = self.get_stale_embeddings()
        duplicate_pairs: List[DuplicatePair] = []
        if _SKLEARN:
            duplicate_pairs = self.get_duplicates()
        return _build_corpus_health(all_docs, ghosts, obsolete, stale, duplicate_pairs)

    # ── reporting ─────────────────────────────────────────────────────────────

    def to_dataframe(self, window_days: int | None = None):
        """Return corpus stats as a pandas DataFrame.

        Args:
            window_days: Lookback window in days for retrieval/engagement
                counts. Defaults to ``ghost_threshold_days`` if ``None``.

        Returns:
            pandas.DataFrame with columns: ``doc_id``, ``filename``,
            ``retrievals``, ``engagements``, ``engagement_rate``, ``status``.
            Sorted by retrievals descending.

        Raises:
            RuntimeError: If pandas is not installed.
        """
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("pip install pandas to use to_dataframe()")

        since  = _days_ago(window_days or self.ghost_threshold_days)
        r_map  = {r["doc_id"]: r for r in self.db.retrieval_counts(since=since)}
        e_map  = {e["doc_id"]: e["cnt"] for e in self.db.engagement_counts(since=since)}
        ghosts = {d["doc_id"] for d in self.get_ghosts()}
        obs    = {d["doc_id"] for d in self.get_obsolete()}
        stale  = {d["doc_id"] for d in self.get_stale_embeddings()}
        rows = _build_dataframe_rows(
            self.db.all_documents(),
            r_map,
            e_map,
            ghosts,
            obs,
            stale,
        )

        return pd.DataFrame(rows).sort_values("retrievals", ascending=False)

    def cleanup_report(self) -> None:
        """Print a prioritised, human-readable action list.

        Prints sections for ghosts, obsolete documents, stale embeddings,
        and re-chunk candidates with counts and top-5 examples in each
        category.

        Returns:
            None. Output is printed to stdout.
        """
        health   = self.corpus_health()
        ghosts   = self.get_ghosts()
        obsolete = self.get_obsolete()
        stale    = self.get_stale_embeddings()
        suspects = self.get_suspects()
        payload = _build_cleanup_payload(
            health,
            ghosts,
            obsolete,
            stale,
            suspects,
            self.ghost_threshold_days,
        )

        print("\n" + "─" * 60)
        print("  corpulse — Cleanup Report")
        print("─" * 60)
        print(f"  Total documents : {payload['total_docs']}")
        print(f"  Noise estimate  : {payload['noise_pct']:.0f}%")
        if payload["bloat_warning"]:
            print(f"  ⚠  {payload['recommendation']}")
        print()

        if ghosts:
            print(f"  👻  GHOSTS  ({payload['ghosts']['count']} docs — never retrieved in "
                  f"{payload['ghost_threshold_days']}d)")
            for g in payload["ghosts"]["top5"]:
                print(f"      · {g['filename']}")
            if payload["ghosts"]["overflow"] > 0:
                print(f"      … and {payload['ghosts']['overflow']} more")
            print()

        if obsolete:
            print(f"  💀  OBSOLETE  ({payload['obsolete']['count']} docs)")
            for o in payload["obsolete"]["top5"]:
                print(f"      · {o['filename']}  →  superseded by {o['superseded_by']}")
            if payload["obsolete"]["overflow"] > 0:
                print(f"      … and {payload['obsolete']['overflow']} more")
            print()

        if stale:
            print(f"  🕓  STALE EMBEDDINGS  ({payload['stale']['count']} docs)")
            for s in payload["stale"]["top5"]:
                print(f"      · {s['filename']}  "
                      f"({s['days_behind']}d behind — "
                      f"source {s['source_updated']}, embedded {s['last_embedded']})")
            if payload["stale"]["overflow"] > 0:
                print(f"      … and {payload['stale']['overflow']} more")
            print()

        if suspects:
            print(f"  🔁  RE-CHUNK CANDIDATES  ({payload['suspects']['count']} docs — high retrieval, low engagement)")
            for s in payload["suspects"]["top5"]:
                print(f"      · {s['filename']}  "
                      f"({s['retrievals']} retrievals, {s['engagement_rate']*100:.0f}% engagement)")
            if payload["suspects"]["overflow"] > 0:
                print(f"      … and {payload['suspects']['overflow']} more")
            print()

        print("─" * 60 + "\n")

    def report(self, window_days: int | None = None) -> None:
        """Print the full corpus health table to stdout.

        Uses tabulate for pretty-printing if installed, falls back to
        plain-text columns otherwise.

        Args:
            window_days: Lookback window in days for retrieval and
                engagement counts. Defaults to ``ghost_threshold_days``
                if ``None``.

        Returns:
            None. Output is printed to stdout.
        """
        try:
            from tabulate import tabulate
            _tabulate = True
        except ImportError:
            _tabulate = False

        since    = _days_ago(window_days or self.ghost_threshold_days)
        all_docs = self.db.all_documents()
        r_map    = {r["doc_id"]: r for r in self.db.retrieval_counts(since=since)}
        e_map    = {e["doc_id"]: e["cnt"] for e in self.db.engagement_counts(since=since)}
        ghosts   = {d["doc_id"] for d in self.get_ghosts()}
        obs      = {d["doc_id"] for d in self.get_obsolete()}
        stale    = {d["doc_id"] for d in self.get_stale_embeddings()}
        health = self.corpus_health()
        rows = _build_report_rows(
            all_docs,
            r_map,
            e_map,
            ghosts,
            obs,
            stale,
            self.top_k_report,
        )
        summary = _build_report_summary(
            all_docs,
            window_days or self.ghost_threshold_days,
            health,
        )
        table_rows = [
            [row["filename"], row["retrievals"], row["engagement_rate"], row["status_display"]]
            for row in rows
        ]
        header = (
            f"\n  corpulse — Corpus Health Report\n"
            f"  {summary['total_docs']} documents · last {summary['window_days']} days"
        )
        if summary["bloat_warning"]:
            header += f" · ⚠ corpus bloat detected ({summary['noise_pct']:.0f}% noise est.)"

        print(header)
        if _tabulate:
            print(tabulate(table_rows,
                           headers=["Document", "Retrieved", "Engagement", "Status"],
                           tablefmt="rounded_outline"))
        else:
            print(f"  {'Document':<35} {'Retrieved':>10} {'Engagement':>12}  Status")
            print("  " + "─" * 70)
            for r in table_rows:
                print(f"  {r[0]:<35} {r[1]:>10} {r[2]:>12}  {r[3]}")

        print(f"\n  👻 ghosts: {summary['ghosts']}  "
              f"💀 obsolete: {summary['obsolete']}  "
              f"⚠ duplicates: {summary['duplicates']}  "
              f"🕓 stale: {summary['stale']}")
        print(f"  Run corpulse.cleanup_report() for a prioritised action list.\n")

    def workload_report(
        self,
        window_days: int | None = None,
        long_context_threshold: int = 8000,
    ) -> WorkloadReportPayload:
        """Return workload analytics for captured RAG request traces.

        Args:
            window_days: Lookback window in days for trace aggregation.
                Defaults to ``ghost_threshold_days`` if ``None``.
            long_context_threshold: Input-token threshold used to flag
                long-context requests. Defaults to 8000.

        Returns:
            WorkloadReportPayload with traffic, token, and component summaries.
        """
        report_window_days = window_days or self.ghost_threshold_days
        traces = self.get_rag_request_traces(window_days=report_window_days)
        return _build_workload_report(
            traces,
            report_window_days,
            long_context_threshold=long_context_threshold,
        )

    def serving_report(
        self,
        window_days: int | None = None,
    ) -> ServingReportPayload:
        """Return serving latency analytics for captured RAG request traces.

        Args:
            window_days: Lookback window in days for trace aggregation.
                Defaults to ``ghost_threshold_days`` if ``None``.

        Returns:
            ServingReportPayload with latency distributions, error rates,
            and slow-request contributor summaries.
        """
        report_window_days = window_days or self.ghost_threshold_days
        traces = self.get_rag_request_traces(window_days=report_window_days)
        return _build_serving_report(traces)

    def session_report(
        self,
        window_days: int | None = None,
    ) -> SessionReportPayload:
        """Return session analytics for captured RAG request traces.

        Args:
            window_days: Lookback window in days for trace aggregation.
                Defaults to ``ghost_threshold_days`` if ``None``.

        Returns:
            SessionReportPayload with session summary, per-session details,
            and repeated-context reuse rows.
        """
        report_window_days = window_days or self.ghost_threshold_days
        traces = self.get_rag_request_traces(window_days=report_window_days)
        return _build_session_report(traces)

    def replay_rag_request_traces(
        self,
        handler: ReplayHandler,
        window_days: int | None = None,
        time_scale: float | None = None,
        max_delay_seconds: float | None = None,
        stop_on_error: bool = False,
    ) -> ReplayReportPayload:
        """Replay captured RAG request traces through a caller-supplied handler.

        Args:
            handler: Callable invoked once per captured trace with a
                ReplayRequest envelope. The return value is ignored and not
                stored.
            window_days: Lookback window in days for trace selection.
                Defaults to ``ghost_threshold_days`` if ``None``.
            time_scale: Optional timing scale. ``None`` means no sleeping;
                ``1.0`` replays captured deltas in real time.
            max_delay_seconds: Optional cap applied to each scheduled delay.
            stop_on_error: True to stop after the first handler exception and
                count remaining traces as skipped.

        Returns:
            ReplayReportPayload with summary counts and per-trace results.
        """
        report_window_days = window_days or self.ghost_threshold_days
        traces = self.get_rag_request_traces(window_days=report_window_days)
        return replay_rag_request_traces(
            traces,
            handler,
            time_scale=time_scale,
            max_delay_seconds=max_delay_seconds,
            stop_on_error=stop_on_error,
        )
