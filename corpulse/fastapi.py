from __future__ import annotations

import logging
from typing import Callable, List, Optional

try:
    from fastapi import APIRouter, Depends, HTTPException, Query
except ImportError:
    APIRouter = None
    Depends = None
    HTTPException = None
    Query = None

from .async_core import AsyncCorpulse
from .models import (
    CleanupPayload,
    DuplicatePair,
    GhostItem,
    ObsoleteItem,
    ReportPayload,
    StaleItem,
    SuspectItem,
)

logger = logging.getLogger(__name__)


def get_corpulse_router(
    get_corpulse: Callable[..., AsyncCorpulse],
    tags: Optional[List[str]] = None,
) -> APIRouter:
    """Create a FastAPI router with AsyncCorpulse analysis endpoints.

    Args:
        get_corpulse: A dependency-injectable function that returns an
            AsyncCorpulse instance (e.g., tenant-scoped).
        tags: Optional list of tags to apply to all routes. Defaults to ["corpulse"].

    Returns:
        APIRouter: A FastAPI router ready to be included in an app.

    Raises:
        ImportError: If fastapi is not installed.
    """
    if APIRouter is None:
        raise ImportError(
            "fastapi is required to use get_corpulse_router. "
            "Install it with: pip install corpulse[fastapi]"
        )

    router = APIRouter(tags=tags or ["corpulse"])

    @router.get("/report", response_model=ReportPayload)
    async def get_report(
        window_days: Optional[int] = Query(None, description="Lookback window in days"),
        corpulse: AsyncCorpulse = Depends(get_corpulse),
    ) -> ReportPayload:
        """Return a structured corpus health report."""
        return await corpulse.report(window_days=window_days)

    @router.get("/cleanup-report", response_model=CleanupPayload)
    async def get_cleanup_report(
        corpulse: AsyncCorpulse = Depends(get_corpulse),
    ) -> CleanupPayload:
        """Return a structured cleanup action payload."""
        return await corpulse.cleanup_report()

    @router.get("/ghosts", response_model=List[GhostItem])
    async def get_ghosts(
        corpulse: AsyncCorpulse = Depends(get_corpulse),
    ) -> List[GhostItem]:
        """Return documents not retrieved within the ghost threshold window."""
        return await corpulse.get_ghosts()

    @router.get("/duplicates", response_model=List[DuplicatePair])
    async def get_duplicates(
        threshold: Optional[float] = Query(None, description="Cosine similarity threshold"),
        corpulse: AsyncCorpulse = Depends(get_corpulse),
    ) -> List[DuplicatePair]:
        """Return near-duplicate document pairs by cosine similarity."""
        try:
            return await corpulse.get_duplicates(threshold=threshold)
        except RuntimeError as e:
            # AsyncCorpulse raises RuntimeError if scikit-learn is missing
            if "scikit-learn" in str(e):
                raise HTTPException(
                    status_code=501,
                    detail="Duplicate detection requires scikit-learn. Install it with: pip install scikit-learn",
                )
            raise

    @router.get("/obsolete", response_model=List[ObsoleteItem])
    async def get_obsolete(
        corpulse: AsyncCorpulse = Depends(get_corpulse),
    ) -> List[ObsoleteItem]:
        """Return documents superseded by newer versioned filenames."""
        return await corpulse.get_obsolete()

    @router.get("/stale", response_model=List[StaleItem])
    async def get_stale(
        corpulse: AsyncCorpulse = Depends(get_corpulse),
    ) -> List[StaleItem]:
        """Return documents whose source is newer than their embedding."""
        return await corpulse.get_stale_embeddings()

    @router.get("/suspects", response_model=List[SuspectItem])
    async def get_suspects(
        window_days: Optional[int] = Query(None, description="Lookback window in days"),
        corpulse: AsyncCorpulse = Depends(get_corpulse),
    ) -> List[SuspectItem]:
        """Return high-retrieval, low-engagement suspect documents."""
        return await corpulse.get_suspects(window_days=window_days)

    return router
