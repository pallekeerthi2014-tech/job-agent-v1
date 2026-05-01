"""
linkedin.py — LinkedIn Jobs adapter (guest API, no auth required)

Uses LinkedIn's undocumented public guest jobs endpoint:
  GET https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
      ?keywords=<query>&location=<loc>&f_TPR=r<seconds>&start=<offset>

Returns HTML job cards parsed with BeautifulSoup. No login, no cookies, no API key.
Rate limiting: ~5 req/min per IP — adapter enforces configurable delays.

Config keys:
  search_queries      list[str]  Search keywords (multiple = more unique results)
  location            str        e.g. "United States"  (default)
  days_back           int        How many days back to search  (default 30)
  max_pages_per_query int        Pages per keyword (25 results/page, default 4 → ~100/keyword)
  delay_seconds       float      Sleep between requests  (default 2.0)
  include_titles      list[str]  Standard title filter (same as all adapters)
  exclude_titles      list[str]  Standard title filter
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.services.source_adapters.base import JobRecord, JobSourceAdapter

logger = logging.getLogger(__name__)

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.linkedin.com/",
    "Connection": "keep-alive",
}

_DEFAULT_QUERIES = [
    "healthcare business analyst",
    "clinical data analyst healthcare",
    "health informatics analyst",
    "epic analyst",
    "payer business analyst",
    "revenue cycle analyst",
    "managed care analyst",
]

_RESULTS_PER_PAGE = 25  # LinkedIn's page size


def _parse_cards(html: str) -> list[dict[str, Any]]:
    """Parse job cards from LinkedIn guest API HTML response."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_=re.compile(r"base-card"))
    jobs: list[dict[str, Any]] = []
    for card in cards:
        urn = card.get("data-entity-urn", "")
        job_id = urn.split(":")[-1] if ":" in urn else ""
        if not job_id:
            continue

        title_tag = card.find(class_=re.compile(r"base-search-card__title"))
        company_tag = card.find(class_=re.compile(r"base-search-card__subtitle"))
        location_tag = card.find(class_=re.compile(r"job-search-card__location"))
        date_tag = card.find("time")
        link_tag = card.find("a", class_=re.compile(r"base-card__full-link"))

        title = title_tag.get_text(strip=True) if title_tag else ""
        company = company_tag.get_text(strip=True) if company_tag else ""
        location = location_tag.get_text(strip=True) if location_tag else ""
        posted_date = date_tag.get("datetime", "") if date_tag else ""
        url = link_tag.get("href", "") if link_tag else f"https://www.linkedin.com/jobs/view/{job_id}/"

        # Strip tracking params from URL
        url = url.split("?")[0] if "?" in url else url

        jobs.append({
            "job_id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "posted_date": posted_date[:10] if posted_date else "",
            "apply_url": url,
        })
    return jobs


class LinkedInJobsAdapter(JobSourceAdapter):
    """
    Fetches jobs from LinkedIn's public guest search API.
    Supports multiple search queries and automatic pagination.
    """

    def __init__(self, source_name: str, config: dict[str, Any] | None = None) -> None:
        super().__init__(source_name, config)
        self._queries: list[str] = self.config.get("search_queries", _DEFAULT_QUERIES)
        self._location: str = self.config.get("location", "United States")
        self._days_back: int = int(self.config.get("days_back", 30))
        self._max_pages: int = int(self.config.get("max_pages_per_query", 4))
        self._delay: float = float(self.config.get("delay_seconds", 2.0))

    def fetch_jobs(self) -> list[dict[str, Any]]:
        seen_ids: set[str] = set()
        all_jobs: list[dict[str, Any]] = []
        f_tpr = f"r{self._days_back * 86400}"

        with httpx.Client(
            timeout=20,
            headers=_BROWSER_HEADERS,
            follow_redirects=True,
        ) as client:
            for query in self._queries:
                query_count = 0
                for page in range(self._max_pages):
                    start = page * _RESULTS_PER_PAGE
                    try:
                        resp = client.get(
                            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
                            params={
                                "keywords": query,
                                "location": self._location,
                                "f_TPR": f_tpr,
                                "start": str(start),
                            },
                        )
                        if resp.status_code == 429:
                            logger.warning(
                                "linkedin.rate_limited query=%r page=%d — stopping", query, page
                            )
                            time.sleep(self._delay * 3)
                            break
                        if resp.status_code != 200:
                            logger.warning(
                                "linkedin.bad_status status=%d query=%r", resp.status_code, query
                            )
                            break

                        cards = _parse_cards(resp.text)
                        if not cards:
                            break  # no more results for this query

                        new = 0
                        for job in cards:
                            jid = job["job_id"]
                            if jid not in seen_ids:
                                seen_ids.add(jid)
                                all_jobs.append(job)
                                new += 1

                        query_count += len(cards)
                        logger.debug(
                            "linkedin.page query=%r page=%d cards=%d new=%d",
                            query, page, len(cards), new,
                        )

                        if len(cards) < _RESULTS_PER_PAGE // 2:
                            break  # sparse page — likely end of results

                    except Exception as exc:
                        logger.warning("linkedin.fetch_error query=%r page=%d: %s", query, page, exc)
                        break
                    finally:
                        time.sleep(self._delay)

                logger.info("linkedin.query_done query=%r count=%d", query, query_count)

        logger.info(
            "linkedin.fetch_complete source=%s total_unique=%d", self.source_name, len(all_jobs)
        )
        return all_jobs

    def normalize_job(self, raw_job: dict[str, Any]) -> JobRecord:
        title = raw_job.get("title", "").strip()
        company = raw_job.get("company", "Unknown").strip()
        location = raw_job.get("location", "").strip()
        apply_url = raw_job.get("apply_url", "").strip()
        posted_date = raw_job.get("posted_date", "")

        is_remote = bool(re.search(r"\bremote\b", location, re.IGNORECASE))

        return JobRecord(
            source=self.source_name,
            title=title or "Untitled",
            company=company or "Unknown",
            location=location or None,
            is_remote=is_remote,
            employment_type=None,
            posted_date=posted_date or None,
            apply_url=apply_url or None,
            description=None,  # would require a second request per job
            domain_tags=[],
            visa_hints=[],
            keywords_extracted=[],
            external_job_id=raw_job.get("job_id", ""),
            raw_payload=raw_job,
        )

    def dedupe_key(self, raw_job: dict[str, Any]) -> str:
        job_id = raw_job.get("job_id", "")
        key = f"linkedin:{job_id}"
        return hashlib.sha256(key.encode()).hexdigest()[:64]
