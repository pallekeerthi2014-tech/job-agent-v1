from __future__ import annotations

import hashlib
from typing import Any

from app.services.source_adapters.base import JobRecord, JobSourceAdapter


class ConfigurableSourceAdapterTemplate(JobSourceAdapter):
    def fetch_jobs(self) -> list[dict[str, Any]]:
        return list(self.config.get("sample_jobs", []))

    def normalize_job(self, raw_job: dict[str, Any]) -> JobRecord:
        mapping = self.config.get("field_mapping", {})
        defaults = self.config.get("defaults", {})

        def mapped(field_name: str, fallback: Any = None) -> Any:
            source_field = mapping.get(field_name)
            if source_field:
                return raw_job.get(source_field, defaults.get(field_name, fallback))
            return defaults.get(field_name, fallback)

        return JobRecord(
            source=self.source_name,
            title=mapped("title", "Untitled role"),
            company=mapped("company", "Unknown company"),
            location=mapped("location"),
            is_remote=bool(mapped("is_remote", False)),
            employment_type=mapped("employment_type"),
            salary_min=_coerce_int(mapped("salary_min")),
            salary_max=_coerce_int(mapped("salary_max")),
            posted_date=mapped("posted_date"),
            apply_url=mapped("apply_url"),
            description=mapped("description"),
            domain_tags=_coerce_list(mapped("domain_tags", [])),
            visa_hints=_coerce_list(mapped("visa_hints", [])),
            keywords_extracted=_coerce_list(mapped("keywords_extracted", [])),
            external_job_id=mapped("external_job_id"),
            raw_payload=raw_job,
        )

    def dedupe_key(self, raw_job: dict[str, Any]) -> str:
        strategy = self.config.get("dedupe_fields", ["external_job_id", "title", "company", "location"])
        normalized = self.normalize_job(raw_job)
        value_map = {
            "external_job_id": normalized.external_job_id or "",
            "title": normalized.title,
            "company": normalized.company,
            "location": normalized.location or "",
            "apply_url": normalized.apply_url or "",
        }
        digest_source = "|".join(str(value_map.get(field_name, raw_job.get(field_name, ""))).strip().lower() for field_name in strategy)
        return hashlib.sha256(digest_source.encode("utf-8")).hexdigest()


def _coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value)]

