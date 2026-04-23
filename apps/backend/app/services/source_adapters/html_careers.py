from __future__ import annotations

import hashlib
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import httpx

from app.services.source_adapters.base import JobRecord, JobSourceAdapter


class GenericHTMLCareersPageAdapter(JobSourceAdapter):
    def fetch_jobs(self) -> list[dict[str, Any]]:
        html = self._load_html()
        parser = CareersHTMLParser(
            job_selector=self.config.get("job_selector", "job-card"),
            title_selector=self.config.get("title_selector", "job-title"),
            location_selector=self.config.get("location_selector", "job-location"),
            link_selector=self.config.get("link_selector", "job-link"),
            posted_selector=self.config.get("posted_selector", "job-posted-date"),
            company_name=self.config.get("company_name"),
        )
        parser.feed(html)
        return parser.jobs

    def normalize_job(self, raw_job: dict[str, Any]) -> JobRecord:
        description = raw_job.get("description")
        location = raw_job.get("location")
        return JobRecord(
            source=self.source_name,
            title=raw_job.get("title") or "Untitled role",
            company=raw_job.get("company") or self.config.get("company_name") or "Unknown company",
            location=location,
            is_remote=bool(location and "remote" in location.lower()),
            employment_type=self.config.get("default_employment_type"),
            apply_url=raw_job.get("apply_url"),
            description=description,
            keywords_extracted=_extract_html_keywords(description),
            raw_payload=raw_job,
        )

    def dedupe_key(self, raw_job: dict[str, Any]) -> str:
        candidate = "|".join(
            [
                raw_job.get("title", "").strip().lower(),
                raw_job.get("company", "").strip().lower(),
                raw_job.get("location", "").strip().lower(),
                raw_job.get("apply_url", "").strip().lower(),
            ]
        )
        return hashlib.sha256(candidate.encode("utf-8")).hexdigest()

    def _load_html(self) -> str:
        if "url" in self.config:
            response = httpx.get(self.config["url"], timeout=self.config.get("timeout_seconds", 20))
            response.raise_for_status()
            return response.text
        if "path" in self.config:
            return Path(self.config["path"]).read_text(encoding="utf-8")
        raise ValueError("GenericHTMLCareersPageAdapter requires either 'url' or 'path'")


class CareersHTMLParser(HTMLParser):
    def __init__(
        self,
        job_selector: str,
        title_selector: str,
        location_selector: str,
        link_selector: str,
        posted_selector: str,
        company_name: str | None,
    ) -> None:
        super().__init__()
        self.job_selector = job_selector
        self.title_selector = title_selector
        self.location_selector = location_selector
        self.link_selector = link_selector
        self.posted_selector = posted_selector
        self.company_name = company_name
        self.jobs: list[dict[str, Any]] = []
        self._current_job: dict[str, Any] | None = None
        self._capture_field: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        class_name = attributes.get("class", "")

        if self.job_selector in class_name:
            self._current_job = {"company": self.company_name}

        if self._current_job is None:
            return

        if self.title_selector in class_name:
            self._capture_field = "title"
        elif self.location_selector in class_name:
            self._capture_field = "location"
        elif self.posted_selector in class_name:
            self._capture_field = "posted_date"
        elif self.link_selector in class_name and tag == "a":
            self._current_job["apply_url"] = attributes.get("href")
            self._capture_field = "description"

    def handle_data(self, data: str) -> None:
        if self._current_job is None or self._capture_field is None:
            return
        text = data.strip()
        if not text:
            return

        current = self._current_job.get(self._capture_field, "")
        separator = " " if current else ""
        self._current_job[self._capture_field] = f"{current}{separator}{text}"

    def handle_endtag(self, tag: str) -> None:
        if self._current_job is None:
            return

        if tag == "a" and self._capture_field == "description":
            self._capture_field = None
            return

        if tag == "div" and self._current_job.get("title"):
            self.jobs.append(self._current_job)
            self._current_job = None
            self._capture_field = None
            return

        self._capture_field = None


def _extract_html_keywords(description: str | None) -> list[str]:
    if not description:
        return []
    candidates = ["fhir", "hl7", "edi", "claims", "hedis", "healthcare"]
    text = description.lower()
    return [candidate.upper() if candidate == "edi" else candidate.upper() for candidate in candidates if candidate in text]
