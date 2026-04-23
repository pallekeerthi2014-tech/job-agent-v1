from __future__ import annotations

import logging
from dataclasses import asdict

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.logging_utils import log_event
from app.services.pipeline import run_daily_pipeline

logger = logging.getLogger(__name__)


def run_daily_pipeline_job() -> None:
    db = SessionLocal()
    try:
        summary = run_daily_pipeline(db)
        log_event(
            logging.INFO,
            "scheduler.job.success",
            job_id="daily-job-agent-pipeline",
            summary=asdict(summary),
        )
    except Exception as exc:
        log_event(
            logging.ERROR,
            "scheduler.job.failure",
            job_id="daily-job-agent-pipeline",
            error=str(exc),
        )
        logger.exception("Daily pipeline job failed")
    finally:
        db.close()


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)
    scheduler.add_job(
        run_daily_pipeline_job,
        CronTrigger(
            hour=settings.daily_job_hour,
            minute=settings.daily_job_minute,
            timezone=settings.scheduler_timezone,
        ),
        id="daily-job-agent-pipeline",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    return scheduler
