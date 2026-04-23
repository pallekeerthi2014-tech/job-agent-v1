from __future__ import annotations

import hashlib
from typing import Any

import httpx

from app.services.source_adapters.base import JobRecord, JobSourceAdapter


class GreenhouseBoardAdapter(JobSourceAdapter):
    def fetch_jobs(self) -> list[dict[str, Any]]:
        board_token = self.config.get("board_token")
        if not board_token:
            raise ValueError("GreenhouseBoardAdapter requires 'board_token'")

        url = self.config.get(
            "url",
            f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true",
        )
        response = httpx.get(url, timeout=self.config.get("timeout_seconds", 20))
        response.raise_for_status()
        payload = response.json()

        jobs = payload.get("jobs", []) if isinstance(payload, dict) else payload
        if not isinstance(jobs, list):
            raise ValueError("Greenhouse response must resolve to a list of jobs")
        return [job for job in jobs if isinstance(job, dict)]

    def normalize_job(self, raw_job: dict[str, Any]) -> JobRecord:
        metadata = raw_job.get("metadata") or []
        location = _extract_location(raw_job)
        description = raw_job.get("content")

        return JobRecord(
            source=self.source_name,
            title=str(raw_job.get("title") or "Untitled role"),
            company=str(self.config.get("company_name") or self.config.get("board_token") or "Unknown company"),
            location=location,
            is_remote=bool(location and "remote" in location.lower()),
            employment_type=_extract_metadata_value(metadata, {"employment type", "commitment", "department"}),
            posted_date=_string_value(raw_job.get("first_published") or raw_job.get("updated_at")),
            apply_url=_string_value(raw_job.get("absolute_url")),
            description=_string_value(description),
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


def _extract_location(raw_job: dict[str, Any]) -> str | None:
    location = raw_job.get("location")
    if isinstance(location, dict):
        return _string_value(location.get("name"))
    return _string_value(location)


def _extract_metadata_value(metadata: list[dict[str, Any]], accepted_names: set[str]) -> str | None:
    for item in metadata:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip().lower()
        if name not in accepted_names:
            continue
        value = item.get("value")
        if isinstance(value, list):
            return ", ".join(str(entry) for entry in value if entry not in (None, ""))
        return _string_value(value)
    return None


def _string_value(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
