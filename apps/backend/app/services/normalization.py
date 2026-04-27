from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.job import JobNormalized, JobRaw
from app.parsers.freshness import validate_job_freshness
from app.parsers.normalizer import normalize_job_payload


class JobNormalizationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def normalize_jobs(self) -> int:
        # Only process raw jobs whose dedupe_hash is not yet in job_normalized.
        # This avoids re-processing thousands of rows on every pipeline run.
        existing_hashes: set[str] = set(
            self.db.scalars(select(JobNormalized.dedupe_hash).where(JobNormalized.dedupe_hash.isnot(None)))
        )

        raw_jobs = list(self.db.scalars(select(JobRaw).order_by(JobRaw.fetched_at.desc())))
        normalized_count = 0

        for raw_job in raw_jobs:
            payload = self._normalize_raw_job(raw_job)
            dedupe_hash = payload.get("dedupe_hash")

            if dedupe_hash and dedupe_hash in existing_hashes:
                # Already normalized — skip (ingestion keeps job_raw clean so
                # we only see genuinely new rows here after Bug 2 fix)
                continue

            self.db.add(JobNormalized(**payload))
            if dedupe_hash:
                existing_hashes.add(dedupe_hash)
            normalized_count += 1

        self.db.commit()
        return normalized_count

    def _normalize_raw_job(self, raw_job: JobRaw) -> dict:
        payload = raw_job.raw_payload
        title = _string_value(payload.get("title") or payload.get("job_title")) or "Untitled role"
        company = _string_value(payload.get("company") or payload.get("company_name")) or "Unknown company"
        location = _location_value(payload.get("location") or payload.get("job_location"))
        employment_type = _string_value(payload.get("employment_type") or payload.get("type"))
        apply_url = _string_value(payload.get("apply_url") or payload.get("url") or payload.get("job_url") or payload.get("absolute_url"))
        description = _string_value(payload.get("description") or payload.get("job_description") or payload.get("content"))
        salary_min = _coerce_int(payload.get("salary_min") or payload.get("min_salary"))
        salary_max = _coerce_int(payload.get("salary_max") or payload.get("max_salary"))
        posted_value = (
            payload.get("posted_date")
            or payload.get("date_posted")
            or payload.get("first_published")
            or payload.get("posted_at")
            or payload.get("posted")
            or payload.get("listing_age")
            or payload.get("posted_text")
            or payload.get("updated_at")
        )
        freshness = validate_job_freshness(
            posted_value,
            fetched_at=raw_job.fetched_at,
            max_age_hours=settings.fresh_job_max_age_hours,
        )

        normalized = normalize_job_payload(
            source=raw_job.source,
            title=title,
            company=company,
            description=description,
            location=location,
            employment_type=employment_type,
            apply_url=apply_url,
            salary_min=salary_min,
            salary_max=salary_max,
        )
        normalized["posted_date"] = freshness.posted_date
        normalized["posted_at_text"] = freshness.posted_at_text
        normalized["freshness_status"] = freshness.freshness_status
        normalized["freshness_age_hours"] = freshness.freshness_age_hours
        return normalized


def normalize_jobs(db: Session) -> int:
    return JobNormalizationService(db).normalize_jobs()


def _string_value(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _location_value(value: object) -> str | None:
    if isinstance(value, dict):
        return _string_value(value.get("name") or value.get("location"))
    return _string_value(value)


def _coerce_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return None
