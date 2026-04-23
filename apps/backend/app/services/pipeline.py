from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from app.services.dedupe import mark_probable_duplicates
from app.services.ingestion import fetch_jobs_from_enabled_sources
from app.services.logging_utils import log_event
from app.services.matching import score_job_candidate_matches
from app.services.normalization import normalize_jobs
from app.services.work_queue import create_employee_work_queues


@dataclass(slots=True)
class PipelineRunSummary:
    raw_jobs_stored: int = 0
    sources_processed: int = 0
    source_failures: int = 0
    jobs_skipped_irrelevant: int = 0
    normalized_jobs: int = 0
    duplicate_groups: int = 0
    scored_matches: int = 0
    work_queue_items: int = 0


def run_daily_pipeline(db: Session) -> PipelineRunSummary:
    summary = PipelineRunSummary()
    log_event(logging.INFO, "pipeline.run.started")

    try:
        fetch_totals = fetch_jobs_from_enabled_sources(db)
        summary.raw_jobs_stored = fetch_totals["raw_jobs_stored"]
        summary.sources_processed = fetch_totals["sources_processed"]
        summary.source_failures = fetch_totals["source_failures"]
        summary.jobs_skipped_irrelevant = fetch_totals["jobs_skipped_irrelevant"]
        log_event(logging.INFO, "pipeline.step.completed", step="fetch_and_store_raw", **fetch_totals)

        summary.normalized_jobs = normalize_jobs(db)
        log_event(logging.INFO, "pipeline.step.completed", step="normalize_jobs", normalized_jobs=summary.normalized_jobs)

        dedupe_results = mark_probable_duplicates(db)
        summary.duplicate_groups = len(dedupe_results)
        log_event(logging.INFO, "pipeline.step.completed", step="dedupe_jobs", duplicate_groups=summary.duplicate_groups)

        summary.scored_matches = score_job_candidate_matches(db)
        log_event(logging.INFO, "pipeline.step.completed", step="score_matches", scored_matches=summary.scored_matches)

        summary.work_queue_items = create_employee_work_queues(db)
        log_event(logging.INFO, "pipeline.step.completed", step="create_work_queues", work_queue_items=summary.work_queue_items)

        log_event(logging.INFO, "pipeline.run.completed", **asdict(summary))
        return summary
    except Exception as exc:
        db.rollback()
        log_event(logging.ERROR, "pipeline.run.failed", error=str(exc))
        raise
