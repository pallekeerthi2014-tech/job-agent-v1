from __future__ import annotations

import hashlib
from typing import Any

import httpx

from app.services.source_adapters.base import JobRecord, JobSourceAdapter


class LeverPostingsAdapter(JobSourceAdapter):
    def fetch_jobs(self) -> list[dict[str, Any]]:
        company_handle = self.config.get("company_handle")
        if not company_handle:
            raise ValueError("LeverPostingsAdapter requires 'company_handle'")

        url = self.config.get(
            "url",
            f"https://api.lever.co/v0/postings/{company_handle}?mode=json",
        )
        response = httpx.get(url, timeout=self.config.get("timeout_seconds", 20))
        response.raise_for_status()
        payload = response.json()

        if not isinstance(payload, list):
            raise ValueError("Lever response must be a list of jobs")
        return [job for job in payload if isinstance(job, dict)]

    def normalize_job(self, raw_job: dict[str, Any]) -> JobRecord:
        categories = raw_job.get("categories") or {}
        location = _string_value(categories.get("location")) or _string_value(raw_job.get("location"))

        return JobRecord(
            source=self.source_name,
            title=_string_value(raw_job.get("text")) or "Untitled role",
            company=_string_value(self.config.get("company_name") or self.config.get("company_handle")) or "Unknown company",
            location=location,
            is_remote=bool(location and "remote" in location.lower()),
            employment_type=_string_value(categories.get("commitment") or categories.get("team")),
            posted_date=_string_value(raw_job.get("createdAtText") or raw_job.get("createdAt")),
            apply_url=_string_value(raw_job.get("hostedUrl") or raw_job.get("applyUrl")),
            description=_string_value(raw_job.get("descriptionPlain") or raw_job.get("description")),
            external_job_id=_string_value(raw_job.get("id")),
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


def _string_value(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
