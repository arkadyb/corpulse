from __future__ import annotations

from typing import Any, List, Union

from typing_extensions import TypedDict


# ─────────────────────────────────────────────────────────────────────────────
# Backend Models
# ─────────────────────────────────────────────────────────────────────────────

class DocumentRow(TypedDict):
    doc_id: str
    filename: str
    embedding_vec: bytes | None
    embedded_at: float | None
    source_updated_at: float | None


class RetrievalRow(TypedDict):
    doc_id: str
    cnt: int
    avg_rank: float | None
    avg_score: float | None


class QueryRow(TypedDict):
    query_hash: str
    cnt: int
    avg_rank: float | None
    avg_score: float | None
    min_rank: int | None
    max_rank: int | None
    min_score: float | None
    max_score: float | None
    first_retrieved_at: float | None
    last_retrieved_at: float | None


class QueryAttemptRow(TypedDict):
    query_hash: str
    cnt: int
    result_cnt: int
    first_attempted_at: float
    last_attempted_at: float


class LowConfidenceQueryRow(QueryRow):
    """Query aggregate row surfaced by low-confidence analytics."""


class ZeroResultQueryRow(QueryAttemptRow):
    """Query aggregate row surfaced by zero-result analytics."""


class EngagementRow(TypedDict):
    doc_id: str
    cnt: int


class EngagementEventRow(TypedDict):
    event_type: str
    cnt: int


class GenerationTraceRow(TypedDict):
    trace_id: int
    prompt_text: str
    retrieved_context_refs: list[dict[str, Any]]
    final_answer_text: str
    evaluation_labels: list[str] | None
    captured_at: float


class RagRequestComponent(TypedDict):
    type: str
    token_count: int | None
    refs: list[dict[str, Any]] | None
    content_hash: str | None
    metadata: dict[str, Any] | None


class RagRequestTimings(TypedDict, total=False):
    ttft_ms: float
    tpot_ms: float
    retrieval_ms: float
    rerank_ms: float
    generation_ms: float
    queue_ms: float
    total_latency_ms: float


class RagRequestTraceRow(TypedDict):
    trace_id: int
    request_id: str | None
    session_id: str | None
    query_text: str | None
    query_hash: str | None
    input_token_count: int | None
    output_token_count: int | None
    components: list[RagRequestComponent]
    timings: RagRequestTimings
    timeout: bool
    error: str | None
    captured_at: float


class RagRequestTraceImportResult(TypedDict):
    total: int
    imported: int
    skipped_duplicates: int
    invalid: int
    errors: list[str]


class EmbeddingRow(TypedDict):
    doc_id: str
    filename: str
    embedding_vec: bytes


# ─────────────────────────────────────────────────────────────────────────────
# API Models — Analysis
# ─────────────────────────────────────────────────────────────────────────────

class DuplicatePair(TypedDict):
    doc_id_a: str
    filename_a: str
    doc_id_b: str
    filename_b: str
    similarity: float


class CorpusHealth(TypedDict):
    total_docs: int
    ghosts: int
    obsolete: int
    stale: int
    duplicates: int
    noise_estimate: float
    bloat_warning: bool
    recommendation: str


# ─────────────────────────────────────────────────────────────────────────────
# API Models — Report
# ─────────────────────────────────────────────────────────────────────────────

class ReportRow(TypedDict):
    filename: str
    retrievals: int
    engagement_rate: str
    status: str
    status_display: str


class ReportSummary(TypedDict):
    total_docs: int
    window_days: int
    bloat_warning: bool
    noise_pct: float
    ghosts: int
    obsolete: int
    duplicates: int
    stale: int
    recommendation: str


class ReportPayload(TypedDict):
    summary: ReportSummary
    rows: List[ReportRow]


class TokenDistribution(TypedDict):
    count: int
    total: int
    avg: float
    p50: float | None
    p95: float | None
    max: float | None


class WorkloadTrafficSummary(TypedDict):
    request_count: int
    window_days: int
    first_captured_at: float | None
    last_captured_at: float | None
    requests_per_hour: float
    peak_requests_per_minute: int


class WorkloadTokenSummary(TypedDict):
    input_tokens: TokenDistribution
    output_tokens: TokenDistribution
    long_context_threshold: int
    long_context_count: int
    long_context_rate: float


class WorkloadComponentSummary(TypedDict):
    component_type: str
    request_count: int
    token_count: int
    request_share: float
    token_share: float


class WorkloadReportPayload(TypedDict):
    traffic: WorkloadTrafficSummary
    tokens: WorkloadTokenSummary
    components: list[WorkloadComponentSummary]


class LatencyDistribution(TypedDict):
    count: int
    avg_ms: float
    p50_ms: float | None
    p95_ms: float | None
    max_ms: float | None


class ServingSlowContributor(TypedDict):
    stage: str
    count: int
    avg_ms: float


class ServingReportPayload(TypedDict):
    request_count: int
    timeout_count: int
    timeout_rate: float
    error_count: int
    error_rate: float
    ttft_ms: LatencyDistribution
    tpot_ms: LatencyDistribution
    total_latency_ms: LatencyDistribution
    stage_latencies: dict[str, LatencyDistribution]
    slow_request_contributors: list[ServingSlowContributor]


class SessionSummary(TypedDict):
    request_count: int
    session_count: int
    unsessioned_request_count: int
    single_turn_session_count: int
    multi_turn_session_count: int
    avg_turns_per_session: float
    max_turns_per_session: int
    follow_up_rate: float
    avg_session_duration_seconds: float
    max_session_duration_seconds: float


class SessionDetail(TypedDict):
    session_id: str
    request_count: int
    first_captured_at: float
    last_captured_at: float
    duration_seconds: float
    input_tokens_first: int | None
    input_tokens_last: int | None
    input_token_growth: int | None
    chat_history_tokens_first: int | None
    chat_history_tokens_last: int | None
    chat_history_token_growth: int | None


class ContextReuseItem(TypedDict):
    session_id: str
    component_type: str
    reuse_key: str
    first_seen_at: float
    request_count: int
    reuse_count: int
    request_share: float


class SessionReportPayload(TypedDict):
    summary: SessionSummary
    sessions: list[SessionDetail]
    context_reuse: list[ContextReuseItem]


class ReplayRequest(TypedDict):
    sequence_index: int
    trace_id: int
    request_id: str | None
    session_id: str | None
    query_text: str | None
    query_hash: str | None
    input_token_count: int | None
    output_token_count: int | None
    components: list[RagRequestComponent]
    timings: RagRequestTimings
    timeout: bool
    error: str | None
    captured_at: float
    scheduled_delay_seconds: float


class ReplayResult(TypedDict):
    sequence_index: int
    trace_id: int
    request_id: str | None
    session_id: str | None
    ok: bool
    error: str | None
    started_at: float
    completed_at: float
    duration_seconds: float
    scheduled_delay_seconds: float


class ReplaySummary(TypedDict):
    trace_count: int
    replayed_count: int
    succeeded_count: int
    failed_count: int
    skipped_count: int
    total_scheduled_delay_seconds: float
    total_runtime_seconds: float


class ReplayReportPayload(TypedDict):
    summary: ReplaySummary
    results: list[ReplayResult]


# ─────────────────────────────────────────────────────────────────────────────
# API Models — Cleanup
# ─────────────────────────────────────────────────────────────────────────────

class GhostItem(TypedDict):
    doc_id: str
    filename: str


class ObsoleteItem(TypedDict):
    doc_id: str
    filename: str
    superseded_by: str


class StaleItem(TypedDict):
    doc_id: str
    filename: str
    source_updated: str
    last_embedded: str
    days_behind: int


class SuspectItem(TypedDict):
    doc_id: str
    filename: str
    retrievals: int
    engagement_rate: float


CleanupItem = Union[GhostItem, ObsoleteItem, StaleItem, SuspectItem]


class CleanupSection(TypedDict):
    count: int
    top5: List[CleanupItem]
    overflow: int


class CleanupPayload(TypedDict):
    total_docs: int
    noise_pct: float
    bloat_warning: bool
    recommendation: str
    ghost_threshold_days: int
    ghosts: CleanupSection
    obsolete: CleanupSection
    stale: CleanupSection
    suspects: CleanupSection
