"""
scheduler.py — 15-Minute Real-Time Polling Pipeline (Phase 2)

Phase 2 changes vs Phase 1:
  - Polling interval: every 15 minutes (was: once daily via CronTrigger)
  - Pipeline: ingest → normalize → dedupe → score → dispatch alerts → work queues
  - Alert dispatch fires for newly ingested jobs above ALERT_MIN_SCORE threshold
  - Midnight cleanup job is retained unchanged
  - max_instances=1 guard prevents pipeline overlap on slow cycles
  - POLL_INTERVAL_MINUTES env var controls the interval (default: 15)
"""
from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import timedelta

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.job import JobNormalized
from app.services.alert_service import AlertDispatchSummary, dispatch_job_alerts, send_source_silence_alerts
from app.services.dedupe import mark_probable_duplicates
from app.services.ingestion import fetch_jobs_from_enabled_sources
from app.services.logging_utils import log_event
from app.services.matching import score_job_candidate_matches
from app.services.normalization import normalize_jobs
from app.services.work_queue import create_employee_work_queues

logger = logging.getLogger(__name__)


def _poll_interval_minutes() -> int:
    try:
        return int(os.getenv("POLL_INTERVAL_MINUTES", "15"))
    except ValueError:
        return 15


@dataclass
class RealtimePipelineRunSummary:
    raw_jobs_stored: int = 0
    sources_processed: int = 0
    source_failures: int = 0
    jobs_skipped_irrelevant: int = 0
    normalized_jobs: int = 0
    duplicate_groups: int = 0
    scored_matches: int = 0
    new_job_ids_count: int = 0
    whatsapp_alerts_sent: int = 0
    email_alerts_sent: int = 0
    work_queue_items: int = 0


def run_realtime_pipeline_job() -> None:
    """
    Full 15-minute pipeline cycle:
      1. Ingest from all enabled sources (live feeds + any existing adapters)
      2. Normalize raw → JobNormalized (dedup by hash)
      3. Mark probable duplicates
      4. Score all active candidates × jobs
      5. Dispatch Slack / email alerts for new high-scoring matches
      6. Update employee work queues
    """
    db = SessionLocal()
    summary = RealtimePipelineRunSummary()
    try:
        log_event(logging.INFO, "scheduler.realtime.started")

        # Capture existing normalized job IDs before ingestion (for delta detection)
        existing_job_ids: set[int] = set(db.scalars(select(JobNormalized.id)))

        # Step 1: Ingest
        fetch_totals = fetch_jobs_from_enabled_sources(db)
        summary.raw_jobs_stored = fetch_totals["raw_jobs_stored"]
        summary.sources_processed = fetch_totals["sources_processed"]
        summary.source_failures = fetch_totals["source_failures"]
        summary.jobs_skipped_irrelevant = fetch_totals["jobs_skipped_irrelevant"]
        log_event(logging.INFO, "scheduler.step.fetch", **fetch_totals)

        # Step 2: Normalize
        summary.normalized_jobs = normalize_jobs(db)
        log_event(logging.INFO, "scheduler.step.normalize", normalized_jobs=summary.normalized_jobs)

        # Step 3: Deduplicate
        dedupe_results = mark_probable_duplicates(db)
        summary.duplicate_groups = len(dedupe_results)
        log_event(logging.INFO, "scheduler.step.dedupe", duplicate_groups=summary.duplicate_groups)

        # Step 4: Score
        summary.scored_matches = score_job_candidate_matches(db)
        log_event(logging.INFO, "scheduler.step.score", scored_matches=summary.scored_matches)

        # Step 5: Identify new jobs (delta since cycle start)
        all_job_ids: set[int] = set(db.scalars(select(JobNormalized.id)))
        new_job_ids: list[int] = list(all_job_ids - existing_job_ids)
        summary.new_job_ids_count = len(new_job_ids)
        log_event(logging.INFO, "scheduler.step.new_jobs_detected", count=len(new_job_ids))

        # Step 6: Dispatch alerts for new high-scoring matches
        if new_job_ids:
            alert_summary: AlertDispatchSummary = dispatch_job_alerts(db, new_job_ids)
            summary.whatsapp_alerts_sent = alert_summary.whatsapp_sent
            summary.email_alerts_sent = alert_summary.email_sent
        log_event(
            logging.INFO, "scheduler.step.alerts",
            whatsapp_sent=summary.whatsapp_alerts_sent,
            email_sent=summary.email_alerts_sent,
        )

        # Step 7: Update work queues
        summary.work_queue_items = create_employee_work_queues(db)
        log_event(logging.INFO, "scheduler.step.work_queue", items=summary.work_queue_items)

        log_event(logging.INFO, "scheduler.realtime.completed", **asdict(summary))

        # Step 8: Check for silent sources (enabled but no successful run in 24 h)
        _check_and_alert_silent_sources(db)

    except Exception as exc:
        db.rollback()
        log_event(logging.ERROR, "scheduler.realtime.failed", error=str(exc))
        logger.exception("Realtime pipeline job failed")
    finally:
        db.close()


def _check_and_alert_silent_sources(db: "Session") -> None:  # type: ignore[name-defined]
    """Alert the team about any enabled source with no successful run in the past 24 h."""
    from app.models.source import JobSource
    from datetime import datetime, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    sources = db.scalars(select(JobSource).where(JobSource.enabled.is_(True))).all()

    silent: list[tuple[str, str | None]] = []
    for s in sources:
        last_ok = s.last_successful_run_at
        if last_ok is None or last_ok < cutoff:
            last_ok_str = last_ok.strftime("%Y-%m-%d %H:%M UTC") if last_ok else None
            silent.append((s.name, last_ok_str))

    if silent:
        log_event(
            logging.WARNING,
            "scheduler.silence_check.silent_sources",
            count=len(silent),
            names=[n for n, _ in silent],
        )
        try:
            send_source_silence_alerts(silent, db=db)
        except Exception as exc:
            logger.warning("scheduler.silence_alert.failed: %s", exc)
    else:
        log_event(logging.INFO, "scheduler.silence_check.all_healthy")


def run_midnight_cleanup_job() -> None:
    """Retained from Phase 1. Runs daily at midnight for housekeeping."""
    db = SessionLocal()
    try:
        from app.services.pipeline import run_daily_pipeline
        summary = run_daily_pipeline(db)
        log_event(logging.INFO, "scheduler.midnight_cleanup.success", **asdict(summary))
    except Exception as exc:
        log_event(logging.ERROR, "scheduler.midnight_cleanup.failure", error=str(exc))
        logger.exception("Midnight cleanup job failed")
    finally:
        db.close()


def build_scheduler() -> BackgroundScheduler:
    """
    Build and return a configured BackgroundScheduler with two jobs:
      1. Realtime pipeline — every POLL_INTERVAL_MINUTES (default: 15)
      2. Midnight cleanup  — daily at midnight UTC (retained from Phase 1)
    """
    scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)
    interval = _poll_interval_minutes()

    # Job 1: Real-time polling pipeline
    scheduler.add_job(
        run_realtime_pipeline_job,
        IntervalTrigger(minutes=interval, timezone=settings.scheduler_timezone),
        id="realtime-job-agent-pipeline",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )
    logger.info("scheduler.configured: realtime pipeline every %d minutes", interval)

    # Job 2: Midnight cleanup (Phase 1 daily job — retained)
    scheduler.add_job(
        run_midnight_cleanup_job,
        CronTrigger(hour=0, minute=0, timezone=settings.scheduler_timezone),
        id="midnight-cleanup-job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    logger.info("scheduler.configured: midnight cleanup retained")

    return scheduler
