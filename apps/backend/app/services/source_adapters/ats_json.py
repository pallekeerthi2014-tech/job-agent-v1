from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import httpx

from app.services.source_adapters.base import JobRecord, JobSourceAdapter


class GenericATSJsonFeedAdapter(JobSourceAdapter):
    def fetch_jobs(self) -> list[dict[str, Any]]:
        if "url" in self.config:
            response = httpx.get(self.config["url"], timeout=self.config.get("timeout_seconds", 20))
            response.raise_for_status()
            payload = response.json()
        elif "path" in self.config:
            payload = json.loads(Path(self.config["path"]).read_text(encoding="utf-8"))
        else:
            raise ValueError("GenericATSJsonFeedAdapter requires either 'url' or 'path'")

        jobs_key = self.config.get("jobs_key", "jobs")
        if isinstance(payload, dict):
            records = payload.get(jobs_key, [])
        else:
            records = payload

        if not isinstance(records, list):
            raise ValueError("Fetched JSON feed must resolve to a list of jobs")

        return [record for record in records if isinstance(record, dict)]

    def normalize_job(self, raw_job: dict[str, Any]) -> JobRecord:
        return JobRecord(
            source=self.source_name,
            title=_first_value(raw_job, self.config.get("title_fields", ["title", "job_title"])) or "Untitled role",
            company=_first_value(raw_job, self.config.get("company_fields", ["company", "company_name"])) or "Unknown company",
            location=_first_value(raw_job, self.config.get("location_fields", ["location", "job_location"])),
            is_remote=bool(_first_value(raw_job, self.config.get("remote_fields", ["is_remote", "remote"])) or False),
            employment_type=_first_value(raw_job, self.config.get("employment_type_fields", ["employment_type", "type"])),
            salary_min=_coerce_int(_first_value(raw_job, self.config.get("salary_min_fields", ["salary_min", "min_salary"]))),
            salary_max=_coerce_int(_first_value(raw_job, self.config.get("salary_max_fields", ["salary_max", "max_salary"]))),
            posted_date=_string_value(_first_value(raw_job, self.config.get("posted_date_fields", ["posted_date", "date_posted"]))),
            apply_url=_first_value(raw_job, self.config.get("apply_url_fields", ["apply_url", "url", "job_url"])),
            description=_first_value(raw_job, self.config.get("description_fields", ["description", "job_description"])),
            domain_tags=_list_value(raw_job.get(self.config.get("domain_tags_field", "domain_tags"))),
            visa_hints=_list_value(raw_job.get(self.config.get("visa_hints_field", "visa_hints"))),
            keywords_extracted=_extract_keywords(raw_job),
            external_job_id=_string_value(_first_value(raw_job, self.config.get("external_id_fields", ["id", "external_job_id", "job_id"]))),
            raw_payload=raw_job,
        )

    def dedupe_key(self, raw_job: dict[str, Any]) -> str:
        record = self.normalize_job(raw_job)
        candidate = "|".join(
            [
                record.external_job_id or "",
                record.title.strip().lower(),
                record.company.strip().lower(),
                (record.location or "").strip().lower(),
            ]
        )
        return hashlib.sha256(candidate.encode("utf-8")).hexdigest()


def _first_value(raw_job: dict[str, Any], field_names: list[str]) -> Any:
    for field_name in field_names:
        value = raw_job.get(field_name)
        if value not in (None, "", []):
            return value
    return None


def _coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _string_value(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _list_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value)]


def _extract_keywords(raw_job: dict[str, Any]) -> list[str]:
    tokens = []
    for field_name in ("keywords", "tags", "skills"):
        tokens.extend(_list_value(raw_job.get(field_name)))
    return tokens

