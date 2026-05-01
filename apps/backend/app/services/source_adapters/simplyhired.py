"""
simplyhired.py — SimplyHired job board adapter (HTML scraper)

SimplyHired search returns 20 results per page with structured HTML
(data-testid attributes, reliable across pagination). No API key required.

URL pattern:
  GET https://www.simplyhired.com/search?q=<query>&l=<location>&fdb=<days>&pn=<page>

Config keys:
  search_query    str        e.g. "healthcare business analyst"
  location        str        e.g. "united states"   (default)
  days_back       int        Filter: posted within N days  (default 30)
  max_pages       int        Max pages to fetch per run  (default 5 → ~100 results)
  delay_seconds   float      Sleep between page requests  (default 2.0)
  include_titles  list[str]  Standard title include filter
  exclude_titles  list[str]  Standard title exclude filter
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
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

_RESULTS_PER_PAGE = 20


def _parse_page(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all(attrs={"data-testid": "searchSerpJob"})
    jobs: list[dict[str, Any]] = []
    for card in cards:
        job_key = card.get("data-jobkey", "")
        title_tag = card.find(attrs={"data-testid": "searchSerpJobTitle"})
        if not title_tag:
            title_tag = card.find("h2") or card.find("h3")
        company_tag = card.find(attrs={"data-testid": "companyName"}) or card.find(attrs={"data-testid": "searchSerpJobCompanyName"})
        loc_tag = card.find(attrs={"data-testid": "searchSerpJobLocation"})
        date_tag = card.find(attrs={"data-testid": "searchSerpJobAge"}) or card.find("time")
        salary_tag = card.find(attrs={"data-testid": "searchSerpJobSalaryEst"})

        title = title_tag.get_text(strip=True) if title_tag else ""
        company = company_tag.get_text(strip=True) if company_tag else ""
        location = loc_tag.get_text(strip=True) if loc_tag else ""
        posted_raw = date_tag.get_text(strip=True) if date_tag else ""
        salary_text = salary_tag.get_text(strip=True) if salary_tag else ""

        if not title or not job_key:
            continue

        url = f"https://www.simplyhired.com/job/{job_key}"
        jobs.append({
            "job_key": job_key,
            "title": title,
            "company": company,
            "location": location,
            "posted_raw": posted_raw,
            "salary_text": salary_text,
            "apply_url": url,
        })
    return jobs


def _parse_salary(text: str) -> tuple[int | None, int | None]:
    """Extract min/max salary from text like '$80K - $120K a year'."""
    nums = re.findall(r"\$?([\d,]+)(?:K|k)?", text)
    values = []
    for n in nums:
        try:
            v = float(n.replace(",", ""))
            if "K" in text or "k" in text:
                v *= 1000
            values.append(int(v))
        except ValueError:
            pass
    if len(values) >= 2:
        return min(values), max(values)
    if len(values) == 1:
        return values[0], None
    return None, None


class SimplyHiredAdapter(JobSourceAdapter):
    """Scrapes SimplyHired job search using structured HTML (data-testid selectors)."""

    def __init__(self, source_name: str, config: dict[str, Any] | None = None) -> None:
        super().__init__(source_name, config)
        self._query: str = self.config.get("search_query", "healthcare business analyst")
        self._location: str = self.config.get("location", "united states")
        self._days_back: int = int(self.config.get("days_back", 30))
        self._max_pages: int = int(self.config.get("max_pages", 5))
        self._delay: float = float(self.config.get("delay_seconds", 2.5))

    def fetch_jobs(self) -> list[dict[str, Any]]:
        all_jobs: list[dict[str, Any]] = []
        seen_keys: set[str] = set()

        with httpx.Client(timeout=20, headers=_BROWSER_HEADERS, follow_redirects=True) as client:
            for page_num in range(1, self._max_pages + 1):
                try:
                    params: dict[str, str] = {
                        "q": self._query,
                        "l": self._location,
                        "fdb": str(self._days_back),
                    }
                    if page_num > 1:
                        params["pn"] = str(page_num)

                    resp = client.get("https://www.simplyhired.com/search", params=params)

                    if resp.status_code == 429:
                        logger.warning("simplyhired.rate_limited page=%d", page_num)
                        break
                    if resp.status_code != 200:
                        logger.warning("simplyhired.bad_status status=%d page=%d", resp.status_code, page_num)
                        break

                    cards = _parse_page(resp.text)
                    if not cards:
                        logger.debug("simplyhired.empty_page page=%d — stopping", page_num)
                        break

                    for job in cards:
                        k = job["job_key"]
                        if k not in seen_keys:
                            seen_keys.add(k)
                            all_jobs.append(job)

                    logger.debug("simplyhired.page page=%d cards=%d total=%d", page_num, len(cards), len(all_jobs))

                    if len(cards) < _RESULTS_PER_PAGE:
                        break  # last page

                except Exception as exc:
                    logger.warning("simplyhired.fetch_error page=%d: %s", page_num, exc)
                    break
                finally:
                    if page_num < self._max_pages:
                        time.sleep(self._delay)

        logger.info("simplyhired.fetch_complete source=%s total=%d", self.source_name, len(all_jobs))
        return all_jobs

    def normalize_job(self, raw_job: dict[str, Any]) -> JobRecord:
        title = raw_job.get("title", "").strip()
        company = raw_job.get("company", "Unknown").strip()
        location = raw_job.get("location", "").strip()
        apply_url = raw_job.get("apply_url", "").strip()
        salary_text = raw_job.get("salary_text", "")

        is_remote = bool(re.search(r"\bremote\b", location, re.IGNORECASE))
        salary_min, salary_max = _parse_salary(salary_text)

        return JobRecord(
            source=self.source_name,
            title=title or "Untitled",
            company=company or "Unknown",
            location=location or None,
            is_remote=is_remote,
            employment_type=None,
            salary_min=salary_min,
            salary_max=salary_max,
            posted_date=None,  # SimplyHired gives relative ("3 days ago") not absolute date
            apply_url=apply_url or None,
            description=None,
            domain_tags=[],
            visa_hints=[],
            keywords_extracted=[],
            external_job_id=raw_job.get("job_key", ""),
            raw_payload=raw_job,
        )

    def dedupe_key(self, raw_job: dict[str, Any]) -> str:
        key = f"simplyhired:{raw_job.get('job_key', '')}"
        return hashlib.sha256(key.encode()).hexdigest()[:64]
