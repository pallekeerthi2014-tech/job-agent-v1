"""
live_feeds.py — Live Feed Source Adapter (Phase 2, production-hardened)

Fetches from four live job sources with automatic retry + exponential backoff:
  - The Muse API   (free, no key required)
  - Arbeitnow API  (free, no key required)
  - USAJobs REST   (free, requires USAJOBS_API_KEY)
  - RemoteOK JSON  (free, no key required)

Each feed is fully isolated — one feed failing never blocks the others.
Retry policy: up to 3 attempts with 2-second base delay (exponential backoff).
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.core.config import settings
from app.services.source_adapters.base import JobRecord, JobSourceAdapter

logger = logging.getLogger(__name__)

# ── Retry policy shared across all feed fetchers ──────────────────────────────
_RETRY_POLICY = dict(
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=False,
)

# ── Role relevance keywords ───────────────────────────────────────────────────
_HEALTHCARE_BA_INCLUDE = [
    "business analyst", "healthcare analyst", "clinical analyst",
    "health information", "health it", "ehr", "epic", "cerner",
    "payer", "provider", "revenue cycle", "managed care",
]
_HEALTHCARE_BA_EXCLUDE = [
    "data engineer", "software engineer", "devops", "qa engineer",
    "marketing analyst", "financial analyst", "sales analyst",
]
HEALTHCARE_BA_KEYWORDS = [
    "healthcare", "health care", "clinical", "ehr", "epic", "cerner",
    "hipaa", "hl7", "fhir", "payer", "provider", "revenue cycle",
    "medicaid", "medicare", "managed care",
]

_WHATSAPP_MAX_CHARS = 1_600


def _is_relevant(title: str, description: str = "") -> bool:
    title_lower = title.lower()
    has_include = any(kw in title_lower for kw in _HEALTHCARE_BA_INCLUDE)
    has_exclude = any(kw in title_lower for kw in _HEALTHCARE_BA_EXCLUDE)
    return has_include and not has_exclude


def _extract_keywords(text: str) -> list[str]:
    text_lower = text.lower()
    return [kw for kw in HEALTHCARE_BA_KEYWORDS if kw in text_lower]


def _detect_remote(text: str) -> bool:
    return bool(re.search(r"\bremote\b", text, re.IGNORECASE))


def _detect_visa_hints(text: str) -> list[str]:
    hints: list[str] = []
    text_lower = text.lower()
    if "no sponsorship" in text_lower or "no visa" in text_lower:
        hints.append("no sponsorship")
    if "sponsorship available" in text_lower or "visa sponsor" in text_lower:
        hints.append("visa sponsorship available")
    if "us work authorization" in text_lower or "must be authorized" in text_lower:
        hints.append("us work authorization required")
    if "us citizen" in text_lower and "clearance" in text_lower:
        hints.append("citizenship preferred")
    return hints


def _detect_domain_tags(text: str) -> list[str]:
    tags: list[str] = []
    text_lower = text.lower()
    domain_map = {
        "payer": ["payer", "insurance", "health plan", "managed care"],
        "provider": ["provider", "hospital", "clinic", "physician"],
        "revenue_cycle": ["revenue cycle", "rcm", "billing", "claims"],
        "ehr_emr": ["ehr", "emr", "epic", "cerner", "meditech", "allscripts"],
        "government": ["medicaid", "medicare", "cms", "government"],
        "clinical": ["clinical", "clinical trials", "clinical operations"],
    }
    for tag, keywords in domain_map.items():
        if any(kw in text_lower for kw in keywords):
            tags.append(tag)
    return tags


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def _safe_int(value: Any) -> int | None:
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None


# ── Individual feed fetchers (each with isolated retry) ───────────────────────

def _fetch_themuse(query: str = "Business Analyst", category: str = "Data and Analytics") -> list[dict[str, Any]]:
    """Fetch from The Muse public API with retry/backoff."""
    results: list[dict[str, Any]] = []

    @retry(**_RETRY_POLICY)
    def _get_page(page: int) -> dict:
        with httpx.Client(timeout=20, headers={"User-Agent": "ThinkSuccess-JobAgent/1.0"}) as client:
            resp = client.get(
                "https://www.themuse.com/api/public/jobs",
                params={"category": category, "page": str(page), "descending": "true"},
            )
            resp.raise_for_status()
            return resp.json()

    try:
        for page in range(1, 4):
            try:
                data = _get_page(page)
            except Exception as exc:
                logger.warning("themuse.page_%d.failed: %s", page, exc)
                break

            for job in data.get("results", []):
                locations = job.get("locations", [])
                loc_name = locations[0].get("name", "") if locations else ""
                levels = job.get("levels", [])
                emp_type = levels[0].get("name", "") if levels else None
                pub_date = (job.get("publication_date") or "")[:10]
                results.append({
                    "_feed_source": "themuse",
                    "title": job.get("name", ""),
                    "company": job.get("company", {}).get("name", "Unknown"),
                    "location": loc_name,
                    "url": job.get("refs", {}).get("landing_page", ""),
                    "description": _clean_html(job.get("contents", ""))[:3000],
                    "published": pub_date,
                    "id": str(job.get("id", "")),
                    "employment_type": emp_type,
                    "is_remote": "remote" in loc_name.lower() or "flexible" in loc_name.lower(),
                })
            if len(data.get("results", [])) < 20:
                break

        logger.info("themuse.fetched count=%d", len(results))
    except Exception as exc:
        logger.warning("themuse.failed: %s", exc)

    return results


def _fetch_arbeitnow(query: str = "healthcare business analyst") -> list[dict[str, Any]]:
    """Fetch from Arbeitnow with retry/backoff."""
    results: list[dict[str, Any]] = []

    @retry(**_RETRY_POLICY)
    def _get() -> dict:
        with httpx.Client(timeout=20, headers={"User-Agent": "ThinkSuccess-JobAgent/1.0"}) as client:
            resp = client.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params={"search": query, "page": "1"},
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = _get()
        for job in data.get("data", []):
            pub_ts = job.get("created_at", "")
            pub_date = ""
            if isinstance(pub_ts, int):
                from datetime import datetime, timezone
                pub_date = datetime.fromtimestamp(pub_ts, tz=timezone.utc).strftime("%Y-%m-%d")
            elif isinstance(pub_ts, str) and len(pub_ts) >= 10:
                pub_date = pub_ts[:10]
            results.append({
                "_feed_source": "arbeitnow",
                "title": job.get("title", ""),
                "company": job.get("company_name", "Unknown"),
                "location": job.get("location", ""),
                "url": job.get("url", ""),
                "description": _clean_html(job.get("description", ""))[:3000],
                "published": pub_date,
                "id": str(job.get("slug", job.get("url", ""))),
                "employment_type": "full-time",
                "is_remote": job.get("remote", False),
            })
        logger.info("arbeitnow.fetched count=%d", len(results))
    except Exception as exc:
        logger.warning("arbeitnow.failed: %s", exc)

    return results


def _fetch_usajobs(keyword: str = "Healthcare Business Analyst") -> list[dict[str, Any]]:
    """Fetch from USAJobs REST API v3 with retry/backoff. Requires USAJOBS_API_KEY."""
    api_key = settings.usajobs_api_key
    if not api_key:
        logger.debug("usajobs.skipped: USAJOBS_API_KEY not set")
        return []

    headers = {
        "Authorization-Key": api_key,
        "User-Agent": settings.usajobs_user_agent_email,
        "Host": "data.usajobs.gov",
    }

    @retry(**_RETRY_POLICY)
    def _get() -> dict:
        with httpx.Client(timeout=20) as client:
            resp = client.get(
                "https://data.usajobs.gov/api/search",
                headers=headers,
                params={"Keyword": keyword, "ResultsPerPage": "50", "SortField": "OpenDate", "SortDirection": "Desc"},
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = _get()
        results = []
        for item in data.get("SearchResult", {}).get("SearchResultItems", []):
            jd = item.get("MatchedObjectDescriptor", {})
            rem = jd.get("PositionRemuneration", [{}])
            sched = jd.get("PositionSchedule", [{}])
            results.append({
                "_feed_source": "usajobs",
                "title": jd.get("PositionTitle", ""),
                "company": jd.get("OrganizationName", "Unknown"),
                "location": jd.get("PositionLocationDisplay", ""),
                "url": (jd.get("ApplyURI") or [""])[0] or jd.get("PositionURI", ""),
                "description": _clean_html(jd.get("QualificationSummary", ""))[:3000],
                "published": jd.get("PublicationStartDate", ""),
                "id": jd.get("PositionID", ""),
                "salary_min": _safe_int(rem[0].get("MinimumRange")) if rem else None,
                "salary_max": _safe_int(rem[0].get("MaximumRange")) if rem else None,
                "employment_type": sched[0].get("Name") if sched else None,
            })
        logger.info("usajobs.fetched count=%d", len(results))
        return results
    except Exception as exc:
        logger.warning("usajobs.failed: %s", exc)
        return []


def _fetch_remoteok(tag: str = "healthcare") -> list[dict[str, Any]]:
    """Fetch from RemoteOK JSON API with retry/backoff."""
    results: list[dict[str, Any]] = []

    @retry(**_RETRY_POLICY)
    def _get() -> list:
        with httpx.Client(
            timeout=20,
            headers={"User-Agent": "ThinkSuccess-JobAgent/1.0", "Accept": "application/json"},
        ) as client:
            resp = client.get(f"https://remoteok.com/api?tag={tag}")
            resp.raise_for_status()
            return resp.json()

    try:
        jobs = _get()
        for job in jobs:
            if not isinstance(job, dict) or "id" not in job:
                continue
            results.append({
                "_feed_source": "remoteok",
                "title": job.get("position", ""),
                "company": job.get("company", "Unknown"),
                "location": "Remote",
                "url": job.get("url", f"https://remoteok.com/jobs/{job['id']}"),
                "description": _clean_html(job.get("description", ""))[:3000],
                "published": job.get("date", ""),
                "id": str(job.get("id", "")),
                "tags": job.get("tags", []),
                "is_remote": True,
            })
        logger.info("remoteok.fetched count=%d", len(results))
    except Exception as exc:
        logger.warning("remoteok.failed: %s", exc)

    return results


def _fetch_remotive(search: str = "healthcare analyst", category: str = "business") -> list[dict[str, Any]]:
    """Fetch from Remotive.com public API — free, no auth, structured JSON."""
    results: list[dict[str, Any]] = []

    @retry(**_RETRY_POLICY)
    def _get() -> dict:
        with httpx.Client(timeout=20, headers={"User-Agent": "ThinkSuccess-JobAgent/1.0"}) as client:
            resp = client.get(
                "https://remotive.com/api/remote-jobs",
                params={"category": category, "search": search, "limit": "100"},
            )
            resp.raise_for_status()
            return resp.json()

    try:
        data = _get()
        for job in data.get("jobs", []):
            results.append({
                "_feed_source": "remotive",
                "title": job.get("title", ""),
                "company": job.get("company_name", "Unknown"),
                "location": job.get("candidate_required_location", "Remote"),
                "url": job.get("url", ""),
                "description": _clean_html(job.get("description", ""))[:3000],
                "published": (job.get("publication_date") or "")[:10],
                "id": str(job.get("id", "")),
                "employment_type": job.get("job_type", ""),
                "salary_text": job.get("salary", ""),
                "is_remote": True,
            })
        logger.info("remotive.fetched count=%d", len(results))
    except Exception as exc:
        logger.warning("remotive.failed: %s", exc)

    return results


# ── Adapter class ─────────────────────────────────────────────────────────────

class LiveFeedAdapter(JobSourceAdapter):
    """
    Aggregates five live job feed sources into the standard adapter interface.
    Each feed is isolated — one failing never blocks the others.
    All HTTP calls use tenacity retry with exponential backoff (max 3 attempts).

    Config keys (all optional):
        themuse_query, themuse_category, arbeitnow_query,
        usajobs_keyword, remoteok_tag, remotive_search, remotive_category,
        enable_themuse (bool, default True)
        enable_arbeitnow (bool, default True)
        enable_usajobs (bool, default False — requires USAJOBS_API_KEY)
        enable_remoteok (bool, default True)
        enable_remotive (bool, default True)
    """

    def __init__(self, source_name: str, config: dict[str, Any] | None = None) -> None:
        super().__init__(source_name, config)
        self._themuse_query    = self.config.get("themuse_query", "Business Analyst")
        self._themuse_category = self.config.get("themuse_category", "Data and Analytics")
        self._arbeitnow_query  = self.config.get("arbeitnow_query", "healthcare business analyst")
        self._usajobs_keyword  = self.config.get("usajobs_keyword", "Healthcare Business Analyst")
        self._remoteok_tag     = self.config.get("remoteok_tag", "healthcare")
        self._remotive_search  = self.config.get("remotive_search", "healthcare analyst")
        self._remotive_category= self.config.get("remotive_category", "business")
        self._enable_themuse   = self.config.get("enable_themuse", True)
        self._enable_arbeitnow = self.config.get("enable_arbeitnow", True)
        self._enable_usajobs   = self.config.get("enable_usajobs", bool(settings.usajobs_api_key))
        self._enable_remoteok  = self.config.get("enable_remoteok", True)
        self._enable_remotive  = self.config.get("enable_remotive", True)

    def fetch_jobs(self) -> list[dict[str, Any]]:
        all_jobs: list[dict[str, Any]] = []
        if self._enable_themuse:
            all_jobs.extend(_fetch_themuse(self._themuse_query, self._themuse_category))
        if self._enable_arbeitnow:
            all_jobs.extend(_fetch_arbeitnow(self._arbeitnow_query))
        if self._enable_usajobs:
            all_jobs.extend(_fetch_usajobs(self._usajobs_keyword))
        if self._enable_remoteok:
            all_jobs.extend(_fetch_remoteok(self._remoteok_tag))
        if self._enable_remotive:
            all_jobs.extend(_fetch_remotive(self._remotive_search, self._remotive_category))
        logger.info("live_feeds.fetch_complete source=%s total=%d", self.source_name, len(all_jobs))
        return all_jobs

    def normalize_job(self, raw_job: dict[str, Any]) -> JobRecord:
        feed_src = raw_job.get("_feed_source", "unknown")
        title = raw_job.get("title", "").strip()
        company = raw_job.get("company", "Unknown").strip()
        location = raw_job.get("location", "").strip()
        apply_url = raw_job.get("url", "").strip()
        description = raw_job.get("description", "").strip()
        published = raw_job.get("published", "")
        full_text = f"{title} {description}"
        is_remote = raw_job.get("is_remote", False) or _detect_remote(f"{location} {description}")

        employment_type = raw_job.get("employment_type")
        if not employment_type:
            text_lower = full_text.lower()
            if "contract" in text_lower:
                employment_type = "contract"
            elif "part-time" in text_lower or "part time" in text_lower:
                employment_type = "part-time"
            elif "full-time" in text_lower or "full time" in text_lower:
                employment_type = "full-time"

        _source_label_map = {
            "themuse": "The Muse", "arbeitnow": "Arbeitnow",
            "remoteok": "RemoteOK", "usajobs": "USAJobs",
            "remotive": "Remotive",
        }

        return JobRecord(
            source=_source_label_map.get(feed_src, feed_src.title()),
            title=title,
            company=company,
            location=location or ("Remote" if is_remote else None),
            is_remote=is_remote,
            employment_type=employment_type,
            salary_min=raw_job.get("salary_min"),
            salary_max=raw_job.get("salary_max"),
            posted_date=published[:10] if len(published) >= 10 else None,
            apply_url=apply_url or None,
            description=description or None,
            domain_tags=_detect_domain_tags(full_text),
            visa_hints=_detect_visa_hints(full_text),
            keywords_extracted=_extract_keywords(full_text),
            external_job_id=self.dedupe_key(raw_job),
            raw_payload=raw_job,
        )

    def dedupe_key(self, raw_job: dict[str, Any]) -> str:
        feed_src = raw_job.get("_feed_source", "unknown")
        job_url = raw_job.get("url", raw_job.get("id", ""))
        key = f"{feed_src}:{job_url}".lower().strip()
        return hashlib.sha256(key.encode()).hexdigest()[:64]
