"""
jsearch.py â JSearch API adapter (RapidAPI)

JSearch aggregates job postings from LinkedIn, Indeed, Glassdoor, ZipRecruiter,
and 20+ other boards â returning structured JSON with salary, skills, and full
job descriptions. No scraping, no ToS risk, fully official REST API.

RapidAPI Hub: https://rapidapi.com/letscrape-6bfbfa26a8-letscrape/api/jsearch
Endpoint: GET https://jsearch.p.rapidapi.com/search

Required env var:  RAPIDAPI_KEY   (set in Railway dashboard â Variables)

Config keys:
  search_queries      list[str]   Keywords to search (multiple queries deduplicated)
  location            str         e.g. "United States"  (default)
  date_posted         str         "all" | "today" | "3days" | "week" | "month"  (default "week")
  num_pages           int         Pages per query â each page = 10 results (default 3 â 30/query)
  remote_only         bool        Restrict to remote jobs only (default False)
  delay_seconds       float       Sleep between queries (default 1.5)
  include_titles      list[str]   Standard title allowlist filter
  exclude_titles      list[str]   Standard title blocklist filter
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.services.source_adapters.base import JobRecord, JobSourceAdapter
from app.services.role_filtering import is_relevant_analyst_role

logger = logging.getLogger(__name__)

_BASE_URL = "https://jsearch.p.rapidapi.com/search"
_HOST = "jsearch.p.rapidapi.com"

_DEFAULT_QUERIES = [
    "healthcare business analyst",
    "clinical systems analyst",
    "health informatics analyst",
    "epic ehr analyst",
    "payer business analyst",
    "revenue cycle analyst",
    "managed care analyst",
    "health IT business analyst",
]

_DEFAULT_INCLUDE_TITLES = [
    "business analyst",
    "data analyst",
    "clinical analyst",
    "healthcare analyst",
    "systems analyst",
    "health informatics",
    "ehr analyst",
    "epic analyst",
    "payer analyst",
    "revenue cycle",
    "managed care",
    "operations analyst",
    "implementation",
    "informatics",
]

_DEFAULT_EXCLUDE_TITLES = [
    "data engineer",
    "software engineer",
    "devops",
    "marketing analyst",
    "financial analyst",
    "sales analyst",
    "actuar",
    "physician",
    "nurse",
    "therapist",
]


class JSearchAdapter(JobSourceAdapter):
    """Fetches jobs from JSearch (RapidAPI) â aggregates LinkedIn, Indeed, Glassdoor & more."""

    def __init__(self, source_name: str, config: dict[str, Any] | None = None) -> None:
        super().__init__(source_name, config)
        self._api_key: str = os.environ.get("RAPIDAPI_KEY", "")
        if not self._api_key:
            logger.warning(
                "[JSearch] RAPIDAPI_KEY env var not set â adapter will return no jobs. "
                "Set it in Railway dashboard â Variables."
            )

    # âââ fetch_jobs ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

    def fetch_jobs(self) -> list[dict[str, Any]]:
        if not self._api_key:
            return []

        queries: list[str] = self.config.get("search_queries", _DEFAULT_QUERIES)
        location: str = self.config.get("location", "United States")
        date_posted: str = self.config.get("date_posted", "week")
        num_pages: int = int(self.config.get("num_pages", 3))
        remote_only: bool = bool(self.config.get("remote_only", False))
        delay: float = float(self.config.get("delay_seconds", 1.5))

        include_titles: list[str] = self.config.get("include_titles", _DEFAULT_INCLUDE_TITLES)
        exclude_titles: list[str] = self.config.get("exclude_titles", _DEFAULT_EXCLUDE_TITLES)

        seen_ids: set[str] = set()
        all_jobs: list[dict[str, Any]] = []

        headers = {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": _HOST,
        }

        with httpx.Client(timeout=20.0) as client:
            for query in queries:
                full_query = f"{query} in {location}" if location else query
                logger.info("[JSearch] Querying: %s (pages=%d)", full_query, num_pages)

                for page in range(1, num_pages + 1):
                    params: dict[str, Any] = {
                        "query": full_query,
                        "page": str(page),
                        "num_pages": "1",
                        "date_posted": date_posted,
                    }
                    if remote_only:
                        params["remote_jobs_only"] = "true"

                    try:
                        resp = client.get(_BASE_URL, headers=headers, params=params)
                        resp.raise_for_status()
                        data = resp.json()
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code == 429:
                            logger.warning("[JSearch] Rate limit hit â stopping query '%s'", query)
                        else:
                            logger.error("[JSearch] HTTP %s for query '%s'", exc.response.status_code, query)
                        break
                    except Exception as exc:
                        logger.error("[JSearch] Request failed for query '%s': %s", query, exc)
                        break

                    jobs_batch = data.get("data", [])
                    if not jobs_batch:
                        break  # No more pages

                    for job in jobs_batch:
                        job_id = job.get("job_id", "")
                        if not job_id or job_id in seen_ids:
                            continue

                        title = job.get("job_title", "")
                        if not is_relevant_analyst_role(title, include_titles=include_titles, exclude_titles=exclude_titles):
                            continue

                        seen_ids.add(job_id)
                        job["_source_query"] = query
                        all_jobs.append(job)

                    if page < num_pages:
                        time.sleep(delay)

                time.sleep(delay)

        logger.info("[JSearch] Fetched %d relevant jobs across %d queries", len(all_jobs), len(queries))
        return all_jobs

    # âââ normalize_job âââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

    def normalize_job(self, raw: dict[str, Any]) -> JobRecord:
        # Build location string
        city = raw.get("job_city") or ""
        state = raw.get("job_state") or ""
        country = raw.get("job_country") or ""
        location_parts = [p for p in [city, state, country] if p]
        location = ", ".join(location_parts) if location_parts else None

        # Parse posted date
        posted_date: str | None = None
        ts = raw.get("job_posted_at_timestamp")
        if ts:
            try:
                posted_date = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
            except Exception:
                pass
        if not posted_date:
            posted_date = raw.get("job_posted_at_datetime_utc", "")[:10] or None

        # Salary
        sal_min = raw.get("job_min_salary")
        sal_max = raw.get("job_max_salary")
        sal_period = (raw.get("job_salary_period") or "").upper()
        # Normalise hourly â annual
        if sal_period == "HOUR":
            sal_min = int(sal_min * 2080) if sal_min else None
            sal_max = int(sal_max * 2080) if sal_max else None
        else:
            sal_min = int(sal_min) if sal_min else None
            sal_max = int(sal_max) if sal_max else None

        # Publisher tag for domain_tags
        publisher = raw.get("job_publisher", "JSearch")
        domain_tags = [publisher] if publisher else ["JSearch"]

        # Extract required skills if present
        skills: list[str] = raw.get("job_required_skills") or []

        emp_type = raw.get("job_employment_type", "")
        employment_type = emp_type.title() if emp_type else None

        return JobRecord(
            source=self.source_name,
            title=raw.get("job_title", ""),
            company=raw.get("employer_name", ""),
            location=location,
            is_remote=bool(raw.get("job_is_remote", False)),
            employment_type=employment_type,
            salary_min=sal_min,
            salary_max=sal_max,
            posted_date=posted_date,
            apply_url=raw.get("job_apply_link") or raw.get("job_google_link"),
            description=raw.get("job_description", ""),
            domain_tags=domain_tags,
            keywords_extracted=skills[:20],
            external_job_id=raw.get("job_id", ""),
            raw_payload=raw,
        )

    # âââ dedupe_key ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

    def dedupe_key(self, raw: dict[str, Any]) -> str:
        job_id = raw.get("job_id", "")
        if job_id:
            return f"jsearch:{job_id}"
        # Fallback: hash title + company + posted date
        title = (raw.get("job_title") or "").lower().strip()
        company = (raw.get("employer_name") or "").lower().strip()
        date = raw.get("job_posted_at_datetime_utc", "")[:10]
        blob = f"{title}|{company}|{date}"
        return "jsearch:" + hashlib.md5(blob.encode()).hexdigest()
