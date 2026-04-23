from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import JobRaw
from app.models.source import JobSource
from app.services.logging_utils import log_event
from app.services.role_filtering import (
    DEFAULT_ANALYST_EXCLUDE_TITLES,
    DEFAULT_ANALYST_INCLUDE_TITLES,
    is_relevant_analyst_role,
)
from app.services.source_adapters.registry import build_source_adapter


def fetch_jobs_from_enabled_sources(db: Session) -> dict[str, int]:
    sources = list(db.scalars(select(JobSource).where(JobSource.enabled.is_(True)).order_by(JobSource.id.asc())))
    totals = {"sources_processed": 0, "raw_jobs_stored": 0, "source_failures": 0, "jobs_skipped_irrelevant": 0}

    for source in sources:
        totals["sources_processed"] += 1
        try:
            adapter = build_source_adapter(source.adapter_type, source.name, source.config)
            raw_jobs = adapter.fetch_jobs()
            stored = 0
            skipped_irrelevant = 0
            include_titles = source.config.get("include_titles", DEFAULT_ANALYST_INCLUDE_TITLES)
            exclude_titles = source.config.get("exclude_titles", DEFAULT_ANALYST_EXCLUDE_TITLES)

            for raw_job in raw_jobs:
                normalized_record = adapter.normalize_job(raw_job)
                if not is_relevant_analyst_role(
                    normalized_record.title,
                    include_titles=include_titles,
                    exclude_titles=exclude_titles,
                ):
                    skipped_irrelevant += 1
                    continue

                external_id = normalized_record.external_job_id or adapter.dedupe_key(raw_job)
                db.add(
                    JobRaw(
                        source=source.name,
                        external_job_id=external_id,
                        raw_payload=raw_job,
                    )
                )
                stored += 1

            source.last_run_at = datetime.now(timezone.utc)
            source.last_error = None
            totals["raw_jobs_stored"] += stored
            totals["jobs_skipped_irrelevant"] += skipped_irrelevant
            log_event(
                logging.INFO,
                "pipeline.fetch_source.success",
                source=source.name,
                stored=stored,
                skipped_irrelevant=skipped_irrelevant,
            )
        except Exception as exc:
            source.last_run_at = datetime.now(timezone.utc)
            source.last_error = str(exc)
            totals["source_failures"] += 1
            log_event(logging.ERROR, "pipeline.fetch_source.failure", source=source.name, error=str(exc))

    db.commit()
    return totals
