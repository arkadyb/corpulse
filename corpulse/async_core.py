from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, List

import numpy as np

from .core import (
    _SKLEARN,
    _build_cleanup_payload,
    _build_corpus_health,
    _build_dataframe_rows,
    _build_duplicate_pairs,
    _build_acceptance_rate,
    _build_mean_reciprocal_rank,
    _build_low_confidence_queries,
    _build_ghosts,
    _build_obsolete_documents,
    _build_query_rate,
    _build_report_rows,
    _build_report_summary,
    _build_serving_report,
    _build_session_report,
    _build_workload_report,
    _build_stale_embeddings,
    _build_suspects,
    _build_zero_result_queries,
    _days_ago,
    _hash_query,
    _now,
    _vec_to_bytes,
)
from .models import (
    ReportPayload, CleanupPayload, GhostItem, DuplicatePair,
    ObsoleteItem, StaleItem, SuspectItem, CorpusHealth,
    QueryRow, LowConfidenceQueryRow, ZeroResultQueryRow,
    QueryAttemptRow,
    GenerationTraceRow,
    RagRequestComponent,
    RagRequestTimings,
    RagRequestTraceImportResult,
    RagRequestTraceRow,
    WorkloadReportPayload,
    ServingReportPayload,
    SessionReportPayload,
    ReplayReportPayload,
)
from .replay import AsyncReplayHandler, async_replay_rag_request_traces
from .workload_io import (
    existing_rag_request_trace_fingerprints,
    parse_rag_request_trace_jsonl_line,
    rag_request_trace_fingerprint,
    serialize_rag_request_trace_jsonl,
)


class AsyncCorpulse:
    def __init__(
        self,
        backend,
        ghost_threshold_days: int = 30,
        duplicate_threshold: float = 0.92,
        stale_threshold_days: int = 14,
        obsolete_pattern: str = r"v\d+",
        top_k_report: int = 20,
        low_confidence_threshold: float = 0.8,
    ):
        self.db = backend
        self.ghost_threshold_days = ghost_threshold_days
        self.duplicate_threshold = duplicate_threshold
        self.stale_threshold_days = stale_threshold_days
        self.obsolete_pattern = obsolete_pattern
        self.top_k_report = top_k_report
        self.low_confidence_threshold = low_confidence_threshold

    async def log_retrieval(
        self,
        results: list[dict[str, Any]],
        query: str = "",
    ) -> None:
        """Record a retrieval event batch for ranked search results.

        Async equivalent of :meth:`Corpulse.log_retrieval`.

        Args:
            results: Retrieved document records. Each item must include
                ``doc_id`` and may include ``filename``, ``score``, and
                ``embedding``.
            query: Raw user query text used to derive the stored query hash.

        Returns:
            None.
        """
        qhash = _hash_query(query)
        ts = _now()
        await self.db.insert_query_attempt(qhash, len(results), ts)

        for rank, item in enumerate(results, start=1):
            doc_id = item["doc_id"]
            filename = item.get("filename", doc_id)
            score = float(item.get("score", 0.0))
            vec = item.get("embedding")

            await self.db.upsert_document(
                doc_id=doc_id,
                filename=filename,
                embedding=_vec_to_bytes(vec) if vec is not None else None,
                embedded_at=ts if vec is not None else None,
            )
            await self.db.insert_retrieval(doc_id, qhash, rank, score, ts)

    async def log_engagement(
        self,
        doc_id: str,
        event: str = "opened",
    ) -> None:
        """Record a user engagement event for a document.

        Async equivalent of :meth:`Corpulse.log_engagement`.

        Args:
            doc_id: Document identifier tied to the engagement.
            event: Engagement type such as ``"opened"`` or ``"clicked"``.

        Returns:
            None.
        """
        await self.db.insert_engagement(doc_id, event, _now())

    async def log_generation_trace(
        self,
        prompt_text: str,
        retrieved_context_refs: list[dict[str, Any]],
        final_answer_text: str,
        evaluation_labels: list[str] | None = None,
    ) -> None:
        """Record an append-only generation trace for future evaluation metrics.

        Args:
            prompt_text: Prompt or query text that initiated generation.
            retrieved_context_refs: Ordered references to the retrieved
                context used for generation.
            final_answer_text: Final generated answer text.
            evaluation_labels: Optional evaluation labels or judgments
                associated with the generation trace.
        """
        await self.db.insert_generation_trace(
            prompt_text=prompt_text,
            retrieved_context_refs=retrieved_context_refs,
            final_answer_text=final_answer_text,
            evaluation_labels=evaluation_labels,
            captured_at=_now(),
        )

    async def alog_rag_request(
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
        """Record an append-only RAG request trace.

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
        await self.db.insert_rag_request_trace(
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

    async def log_source_update(
        self,
        doc_id: str,
        updated_at: float | None = None,
    ) -> None:
        """Mark a document source as updated.

        Async equivalent of :meth:`Corpulse.log_source_update`.

        Args:
            doc_id: Document identifier whose source changed.
            updated_at: Unix timestamp for the source update. Defaults to
                the current time if omitted.

        Returns:
            None.
        """
        await self.db.update_source_timestamp(doc_id, updated_at or _now())

    async def register_document(
        self,
        doc_id: str,
        filename: str,
        embedding: list | np.ndarray | None = None,
    ) -> None:
        """Register or update a document in the corpus.

        Async equivalent of :meth:`Corpulse.register_document`.

        Args:
            doc_id: Stable document identifier.
            filename: Human-readable document name shown in reports.
            embedding: Optional embedding vector to persist with the
                document.

        Returns:
            None.
        """
        await self.db.upsert_document(
            doc_id=doc_id,
            filename=filename,
            embedding=_vec_to_bytes(embedding) if embedding is not None else None,
            embedded_at=_now() if embedding is not None else None,
        )

    async def delete_document(self, doc_id: str) -> None:
        """Delete a document and its associated retrieval and engagement history."""
        await self.db.delete_document(doc_id)

    async def delete_generation_traces(
        self,
        *,
        trace_ids: list[int] | None = None,
        prompt_text: str | None = None,
        evaluation_label: str | None = None,
    ) -> None:
        """Delete generation traces matching the supplied identifiers or demo markers."""
        await self.db.delete_generation_traces(
            trace_ids=trace_ids,
            prompt_text=prompt_text,
            evaluation_label=evaluation_label,
        )

    async def get_ghosts(self) -> List[GhostItem]:
        """Return documents not retrieved within the ghost threshold window.

        Async equivalent of :meth:`Corpulse.get_ghosts`.

        Returns:
            List[GhostItem]: Ghost document records with identifiers and filenames.
        """
        cutoff = _days_ago(self.ghost_threshold_days)
        retrieval_rows = await self.db.retrieval_counts(since=cutoff)
        all_docs = await self.db.all_documents()
        return _build_ghosts(all_docs, retrieval_rows)

    async def get_duplicates(
        self,
        threshold: float | None = None,
    ) -> List[DuplicatePair]:
        """Return near-duplicate document pairs by cosine similarity.

        Async equivalent of :meth:`Corpulse.get_duplicates`.

        Args:
            threshold: Optional cosine-similarity cutoff. Defaults to
                ``duplicate_threshold`` if omitted.

        Returns:
            List[DuplicatePair]: Duplicate-pair records with filenames and similarity.
        """
        duplicate_threshold = threshold or self.duplicate_threshold
        embedding_rows = await self.db.all_embeddings()
        return _build_duplicate_pairs(embedding_rows, duplicate_threshold)

    async def get_obsolete(self) -> List[ObsoleteItem]:
        """Return documents superseded by newer versioned filenames.

        Async equivalent of :meth:`Corpulse.get_obsolete`.

        Returns:
            List[ObsoleteItem]: Obsolete document records with replacement metadata.
        """
        all_docs = await self.db.all_documents()
        return _build_obsolete_documents(all_docs, self.obsolete_pattern)

    async def get_stale_embeddings(self) -> List[StaleItem]:
        """Return documents whose source is newer than their embedding.

        Async equivalent of :meth:`Corpulse.get_stale_embeddings`.

        Returns:
            List[StaleItem]: Stale-embedding records including lag details.
        """
        all_docs = await self.db.all_documents()
        return _build_stale_embeddings(all_docs, self.stale_threshold_days)

    async def get_suspects(self, window_days: int | None = None) -> List[SuspectItem]:
        """Return high-retrieval, low-engagement suspect documents.

        Async equivalent of :meth:`Corpulse.get_suspects`.

        Args:
            window_days: Lookback window in days for retrieval and
                engagement counts. Defaults to ``ghost_threshold_days``
                if ``None``.

        Returns:
            List[SuspectItem]: Suspect document records with retrieval and
            engagement metrics.
        """
        since = _days_ago(window_days or self.ghost_threshold_days)
        all_docs = await self.db.all_documents()
        retrieval_rows = await self.db.retrieval_counts(since=since)
        engagement_rows = await self.db.engagement_counts(since=since)
        return _build_suspects(all_docs, retrieval_rows, engagement_rows)

    async def mean_reciprocal_rank(self, window_days: int | None = None) -> float:
        """Return the Phase 22 proxy MRR from retrieval rank and engagement overlap."""
        since = _days_ago(window_days or self.ghost_threshold_days)
        retrieval_rows = await self.db.retrieval_counts(since=since)
        engagement_rows = await self.db.engagement_counts(since=since)
        return _build_mean_reciprocal_rank(retrieval_rows, engagement_rows)

    async def acceptance_rate(self, window_days: int | None = None) -> float:
        """Return the share of accepted engagement rows in the lookback window.

        Accepted rows are those whose normalized ``event_type`` matches the
        fixed v1.5 allowlist.
        """
        since = _days_ago(window_days or self.ghost_threshold_days)
        event_rows = await self.db.engagement_event_counts(since=since)
        return _build_acceptance_rate(event_rows)

    async def get_generation_traces(self, window_days: int | None = None) -> list[GenerationTraceRow]:
        """Return append-only generation traces from the lookback window.

        Args:
            window_days: Lookback window in days. Defaults to
                ``ghost_threshold_days`` if ``None``.
        """
        since = _days_ago(window_days or self.ghost_threshold_days)
        return await self.db.generation_traces(since=since)

    async def get_rag_request_traces(self, window_days: int | None = None) -> list[RagRequestTraceRow]:
        """Return append-only RAG request traces from the lookback window.

        Args:
            window_days: Lookback window in days. Defaults to
                ``ghost_threshold_days`` if ``None``.
        """
        since = _days_ago(window_days or self.ghost_threshold_days)
        return await self.db.rag_request_traces(since=since)

    async def aexport_rag_request_traces_jsonl(
        self,
        destination,
        *,
        window_days: int | None = None,
        include_raw_text: bool = False,
        include_component_metadata: bool = False,
    ) -> int:
        """Export append-only RAG request traces as JSONL.

        Args:
            destination: Path or text stream to receive one JSON object per line.
            window_days: Lookback window in days. Defaults to
                ``ghost_threshold_days`` if ``None``.
            include_raw_text: True to include raw query text in exported rows.
            include_component_metadata: True to include component metadata.

        Returns:
            Number of traces written.
        """
        traces = await self.get_rag_request_traces(window_days=window_days)
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

    async def aimport_rag_request_traces_jsonl(
        self,
        source,
        *,
        strict: bool = True,
    ) -> RagRequestTraceImportResult:
        """Import RAG request traces from JSONL into the active backend.

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
        existing = existing_rag_request_trace_fingerprints(
            await self.get_rag_request_traces(window_days=None)
        )
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
                fingerprint = rag_request_trace_fingerprint(trace)
                if fingerprint in existing:
                    skipped_duplicates += 1
                    continue
                await self.db.insert_rag_request_trace(
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
                existing.add(fingerprint)
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

    async def _query_rows(self, window_days: int | None = None) -> List[QueryRow]:
        since = _days_ago(window_days or self.ghost_threshold_days)
        return await self.db.query_counts(since=since)

    async def _query_attempt_rows(self, window_days: int | None = None) -> List[QueryAttemptRow]:
        since = _days_ago(window_days or self.ghost_threshold_days)
        return await self.db.query_attempt_counts(since=since)

    async def low_confidence_rate(
        self,
        window_days: int | None = None,
        threshold: float | None = None,
    ) -> float:
        """Return the share of queries whose top score falls below *threshold*."""
        query_rows = await self._query_rows(window_days)
        confidence_threshold = threshold if threshold is not None else self.low_confidence_threshold
        low_confidence_rows = _build_low_confidence_queries(query_rows, confidence_threshold)
        return _build_query_rate(
            [row for row in query_rows if int(row["cnt"]) > 0],
            low_confidence_rows,
        )

    async def get_low_confidence_queries(
        self,
        window_days: int | None = None,
        threshold: float | None = None,
    ) -> List[LowConfidenceQueryRow]:
        """Return query aggregates whose top score falls below *threshold*."""
        query_rows = await self._query_rows(window_days)
        confidence_threshold = threshold if threshold is not None else self.low_confidence_threshold
        return _build_low_confidence_queries(query_rows, confidence_threshold)

    async def zero_result_rate(self, window_days: int | None = None) -> float:
        """Return the share of query aggregates recorded with zero results."""
        query_rows = await self._query_attempt_rows(window_days)
        zero_result_rows = _build_zero_result_queries(query_rows)
        return _build_query_rate(query_rows, zero_result_rows)

    async def get_zero_result_queries(
        self,
        window_days: int | None = None,
    ) -> List[ZeroResultQueryRow]:
        """Return query aggregates recorded with zero results."""
        query_rows = await self._query_attempt_rows(window_days)
        return _build_zero_result_queries(query_rows)

    async def corpus_health(self) -> CorpusHealth:
        """Return aggregate corpus-health metrics.

        Async equivalent of :meth:`Corpulse.corpus_health`.

        Returns:
            CorpusHealth: Summary metrics including noise estimate, counts, and
            bloat recommendation fields.
        """
        all_docs = await self.db.all_documents()
        if not all_docs:
            return _build_corpus_health([], [], [], [], [])

        ghosts = await self.get_ghosts()
        obsolete = await self.get_obsolete()
        stale = await self.get_stale_embeddings()
        duplicate_pairs: List[DuplicatePair] = []
        if _SKLEARN:
            duplicate_pairs = await self.get_duplicates()

        return _build_corpus_health(
            all_docs,
            ghosts,
            obsolete,
            stale,
            duplicate_pairs,
        )

    async def to_dataframe(self, window_days: int | None = None):
        """Return corpus stats as a pandas DataFrame.

        Async equivalent of :meth:`Corpulse.to_dataframe`. Retrieval and
        engagement counts are fetched from the async backend before building
        the DataFrame.

        Args:
            window_days: Lookback window in days for retrieval/engagement
                counts. Defaults to ``ghost_threshold_days`` if ``None``.

        Returns:
            pandas.DataFrame with columns: ``doc_id``, ``filename``,
            ``retrievals``, ``engagements``, ``engagement_rate``, ``status``.
            Sorted by retrievals descending.

        Raises:
            RuntimeError: If pandas is not installed
                (``pip install pandas`` to resolve).
        """
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("pip install pandas to use to_dataframe()")

        since = _days_ago(window_days or self.ghost_threshold_days)
        all_docs = await self.db.all_documents()
        retrieval_rows = await self.db.retrieval_counts(since=since)
        engagement_rows = await self.db.engagement_counts(since=since)
        ghost_ids = {doc["doc_id"] for doc in await self.get_ghosts()}
        obsolete_ids = {doc["doc_id"] for doc in await self.get_obsolete()}
        stale_ids = {doc["doc_id"] for doc in await self.get_stale_embeddings()}
        rows = _build_dataframe_rows(
            all_docs,
            {row["doc_id"]: row for row in retrieval_rows},
            {row["doc_id"]: row["cnt"] for row in engagement_rows},
            ghost_ids,
            obsolete_ids,
            stale_ids,
        )
        return pd.DataFrame(rows).sort_values("retrievals", ascending=False)

    async def cleanup_report(self) -> CleanupPayload:
        """Return a structured cleanup action payload.

        Unlike sync :meth:`Corpulse.cleanup_report` which prints to stdout,
        this method returns the payload as a dict so callers can format, log,
        or forward it.

        MODEL-04: This method is analysis-only and does not mutate document data.
        It only calls read-only analysis methods and pure payload builders.

        Returns:
            CleanupPayload with sections for ghosts, obsolete, stale, and suspects.
        """
        health = await self.corpus_health()
        ghosts = await self.get_ghosts()
        obsolete = await self.get_obsolete()
        stale = await self.get_stale_embeddings()
        suspects = await self.get_suspects()
        return _build_cleanup_payload(
            health,
            ghosts,
            obsolete,
            stale,
            suspects,
            self.ghost_threshold_days,
        )

    async def report(self, window_days: int | None = None) -> ReportPayload:
        """Return a structured corpus health payload.

        Unlike sync :meth:`Corpulse.report` which prints to stdout, this method
        returns the payload as a dict so callers can format, log, or forward it.

        Args:
            window_days: Lookback window in days for retrieval and engagement
                counts. Defaults to ``ghost_threshold_days`` if ``None``.

        Returns:
            ReportPayload containing summary metrics and document rows.
        """
        report_window_days = window_days or self.ghost_threshold_days
        since = _days_ago(report_window_days)
        all_docs = await self.db.all_documents()
        retrieval_rows = await self.db.retrieval_counts(since=since)
        engagement_rows = await self.db.engagement_counts(since=since)
        ghosts = await self.get_ghosts()
        obsolete = await self.get_obsolete()
        stale = await self.get_stale_embeddings()
        health = await self.corpus_health()
        return {
            "summary": _build_report_summary(
                all_docs,
                report_window_days,
                health,
            ),
            "rows": _build_report_rows(
                all_docs,
                {row["doc_id"]: row for row in retrieval_rows},
                {row["doc_id"]: row["cnt"] for row in engagement_rows},
                {row["doc_id"] for row in ghosts},
                {row["doc_id"] for row in obsolete},
                {row["doc_id"] for row in stale},
                self.top_k_report,
            ),
        }

    async def workload_report(
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
        traces = await self.get_rag_request_traces(window_days=report_window_days)
        return _build_workload_report(
            traces,
            report_window_days,
            long_context_threshold=long_context_threshold,
        )

    async def serving_report(
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
        traces = await self.get_rag_request_traces(window_days=report_window_days)
        return _build_serving_report(traces)

    async def session_report(
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
        traces = await self.get_rag_request_traces(window_days=report_window_days)
        return _build_session_report(traces)

    async def areplay_rag_request_traces(
        self,
        handler: AsyncReplayHandler,
        window_days: int | None = None,
        time_scale: float | None = None,
        max_delay_seconds: float | None = None,
        stop_on_error: bool = False,
    ) -> ReplayReportPayload:
        """Replay captured RAG request traces through an async handler.

        Args:
            handler: Async callable invoked once per captured trace with a
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
        traces = await self.get_rag_request_traces(window_days=report_window_days)
        return await async_replay_rag_request_traces(
            traces,
            handler,
            time_scale=time_scale,
            max_delay_seconds=max_delay_seconds,
            stop_on_error=stop_on_error,
        )

    async def close(self) -> None:
        """Close the underlying async backend.

        Returns:
            None.
        """
        await self.db.close()

    async def __aenter__(self) -> AsyncCorpulse:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
