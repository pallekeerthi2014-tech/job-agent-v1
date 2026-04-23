from __future__ import annotations

import hashlib
from typing import Any

import httpx

from app.services.source_adapters.base import JobRecord, JobSourceAdapter


class WorkdayJobsAdapter(JobSourceAdapter):
    def fetch_jobs(self) -> list[dict[str, Any]]:
        url = self.config.get("url")
        if not url:
            raise ValueError("WorkdayJobsAdapter requires 'url'")

        response = httpx.get(url, timeout=self.config.get("timeout_seconds", 20))
        response.raise_for_status()
        payload = response.json()

        jobs = payload.get("jobPostings") or payload.get("jobs") or payload.get("results") or []
        if not isinstance(jobs, list):
            raise ValueError("Workday response must resolve to a list of jobs")
        return [job for job in jobs if isinstance(job, dict)]

    def normalize_job(self, raw_job: dict[str, Any]) -> JobRecord:
        location = _extract_location(raw_job)
        company = _string_value(self.config.get("company_name")) or "Unknown company"
        apply_url = _extract_apply_url(raw_job, self.config.get("job_url_prefix"))
        description = _string_value(raw_job.get("bulletFields")) or _string_value(raw_job.get("description"))

        return JobRecord(
            source=self.source_name,
            title=_string_value(raw_job.get("title") or raw_job.get("jobTitle")) or "Untitled role",
            company=company,
            location=location,
            is_remote=bool(location and "remote" in location.lower()),
            employment_type=_string_value(raw_job.get("timeType") or raw_job.get("workerSubType")),
            posted_date=_string_value(raw_job.get("postedOn") or raw_job.get("postedDate") or raw_job.get("postedDateDisplay")),
            apply_url=apply_url,
            description=description,
            external_job_id=_string_value(raw_job.get("bulletFields") and raw_job.get("externalPath")) or _string_value(raw_job.get("id") or raw_job.get("bulletFields")),
            raw_payload=raw_job,
        )

    def dedupe_key(self, raw_job: dict[str, Any]) -> str:
        normalized = self.normalize_job(raw_job)
        value = "|".join(
            [
                normalized.external_job_id or "",
                normalized.title.strip().lower(),
                normalized.company.strip().lower(),
                (normalized.location or "").strip().lower(),
            ]
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _extract_location(raw_job: dict[str, Any]) -> str | None:
    locations = raw_job.get("locationsText")
    if isinstance(locations, str) and locations.strip():
        return locations

    if isinstance(locations, list):
        flattened = [str(item).strip() for item in locations if item not in (None, "")]
        if flattened:
            return ", ".join(flattened)

    location = raw_job.get("location")
    if isinstance(location, dict):
        for key in ("city", "name"):
            value = location.get(key)
            if value not in (None, ""):
                return str(value)
    return _string_value(location)


def _extract_apply_url(raw_job: dict[str, Any], prefix: str | None) -> str | None:
    for key in ("applyUrl", "externalUrl", "url"):
        value = _string_value(raw_job.get(key))
        if value:
            return value

    external_path = _string_value(raw_job.get("externalPath"))
    if external_path and prefix:
        return prefix.rstrip("/") + "/" + external_path.lstrip("/")
    return external_path


def _string_value(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
