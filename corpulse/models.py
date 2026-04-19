from __future__ import annotations

from typing import TypedDict, List, Union


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
