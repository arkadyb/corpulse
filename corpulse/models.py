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


class EngagementRow(TypedDict):
    doc_id: str
    cnt: int


class EmbeddingRow(TypedDict):
    doc_id: str
    filename: str
    embedding_vec: bytes


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
