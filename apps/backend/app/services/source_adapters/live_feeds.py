"""
live_feeds.py — Live Feed Source Adapter (Phase 2)
Path: apps/backend/app/services/source_adapters/live_feeds.py

Implements LiveFeedAdapter which fetches from four live job sources:
  - The Muse API        (free, no key required, reliable)
  - Arbeitnow API       (free, no key required, reliable)
  - USAJobs REST API    (free, requires USAJOBS_API_KEY)
  - RemoteOK JSON API   (free, no key required)

Previously used Indeed/Dice RSS which were deprecated in 2023 and return 0.
Registered as adapter_type="live_feed" in the source adapter registry.
One row in the JobSource table activates all four feeds simultaneously.
Deduplication is handled upstream via SHA-256 hash of source+URL.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

import httpx

from app.services.source_adapters.base import JobRecord, JobSourceAdapter

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Role relevance keywords (lightweight pre-filter before ingestion.py filter)
# ──────────────────────────────────────────────────────────────────────────────
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


def _is_relevant(title: str, description: str = "") -> bool:
    """Quick relevance check — let ingestion.py do the definitive filter."""
    title_lower = title.lower()
    desc_lower = (description or "").lower()
    has_include = any(kw in title_lower for kw in _HEALTHCARE_BA_INCLUDE)
    has_exclude = any(kw in title_lower for kw in _HEALTHCARE_BA_EXCLUDE)
    return has_include and not has_exclude


def _extract_keywords(text: str) -> list[str]:
    """Pull Healthcare BA keywords from free text."""
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
    """Strip basic HTML tags from feed descriptions."""
    return re.sub(r"<[^>]+>", " ", text or "").strip()


# ──────────────────────────────────────────────────────────────────────────────
# Individual feed fetchers
# ──────────────────────────────────────────────────────────────────────────────

def _fetch_themuse(query: str = "Business Analyst", category: str = "Data and Analytics") -> list[dict[str, Any]]:
    """
    Fetch from The Muse public API — free, no API key required.
    Returns jobs with _feed_source='themuse'.
    Docs: https://www.themuse.com/developers/api/v2
    """
    results: list[dict[str, Any]] = []
    try:
        # Fetch pages 1–3 (100 jobs max)
        for page in range(1, 4):
            params = {
                "category": category,
                "page": str(page),
                "descending": "true",
            }
            with httpx.Client(timeout=15, headers={"User-Agent": "job-agent-v1"}) as client:
                resp = client.get("https://www.themuse.com/api/public/jobs", params=params)
                resp.raise_for_status()
                data = resp.json()

            for job in data.get("results", []):
                locations = job.get("locations", [])
                loc_name = locations[0].get("name", "") if locations else ""
                levels = job.get("levels", [])
                emp_type = levels[0].get("name", "") if levels else None

                # Use publication date from the API
                pub_date = (job.get("publication_date") or "")[:10]

                results.append({
                    "_feed_source": "themuse",
                    "title": job.get("name", ""),
                    "company": job.get("company", {}).get("name", "Unknown"),
                    "location": loc_name,
                    "url": job.get("refs", {}).get("landing_page", ""),
                    "description": _clean_html(job.get("contents", "")),
                    "published": pub_date,
                    "id": str(job.get("id", "")),
                    "employment_type": emp_type,
                    "is_remote": "remote" in loc_name.lower() or "flexible" in loc_name.lower(),
                })

            # Stop early if fewer than a full page returned
            if len(data.get("results", [])) < 20:
                break

        logger.info("themuse.fetched", extra={"count": len(results)})
        return results
    except Exception as exc:
        logger.warning("themuse.failed: %s", exc)
        return []


def _fetch_arbeitnow(query: str = "healthcare business analyst") -> list[dict[str, Any]]:
    """
    Fetch from Arbeitnow free job board API — no key required, international roles.
    Returns jobs with _feed_source='arbeitnow'.
    Docs: https://arbeitnow.com/api
    """
    results: list[dict[str, Any]] = []
    try:
        params = {"search": query, "page": "1"}
        with httpx.Client(timeout=15, headers={"User-Agent": "job-agent-v1"}) as client:
            resp = client.get("https://www.arbeitnow.com/api/job-board-api", params=params)
            resp.raise_for_status()
            data = resp.json()

        for job in data.get("data", []):
            pub_ts = job.get("created_at", "")
            # created_at is a unix timestamp integer in Arbeitnow API
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
                "description": _clean_html(job.get("description", "")),
                "published": pub_date,
                "id": str(job.get("slug", job.get("url", ""))),
                "employment_type": "full-time",
                "is_remote": job.get("remote", False),
            })

        logger.info("arbeitnow.fetched", extra={"count": len(results)})
        return results
    except Exception as exc:
        logger.warning("arbeitnow.failed: %s", exc)
        return []


def _fetch_usajobs(keyword: str = "Healthcare Business Analyst", api_key: str = "") -> list[dict[str, Any]]:
    """
    Fetch from USAJobs REST API v3.
    Requires USAJOBS_API_KEY and USAJOBS_USER_AGENT (email) in config.
    Returns raw job dicts with _feed_source='usajobs'.
    """
    if not api_key:
        logger.debug("usajobs.skipped: USAJOBS_API_KEY not set")
        return []

    headers = {
        "Authorization-Key": api_key,
        "User-Agent": "job-agent-v1@thinksuccessitconsulting.com",
        "Host": "data.usajobs.gov",
    }
    params = {
        "Keyword": keyword,
        "ResultsPerPage": "50",
        "SortField": "OpenDate",
        "SortDirection": "Desc",
    }
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get("https://data.usajobs.gov/api/search", headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("SearchResult", {}).get("SearchResultItems", []):
            jd = item.get("MatchedObjectDescriptor", {})
            results.append({
                "_feed_source": "usajobs",
                "title": jd.get("PositionTitle", ""),
                "company": jd.get("OrganizationName", "Unknown"),
                "location": jd.get("PositionLocationDisplay", ""),
                "url": jd.get("ApplyURI", [""])[0] if jd.get("ApplyURI") else jd.get("PositionURI", ""),
                "description": _clean_html(jd.get("QualificationSummary", "")),
                "published": jd.get("PublicationStartDate", ""),
                "id": jd.get("PositionID", ""),
                "salary_min": _safe_int(jd.get("PositionRemuneration", [{}])[0].get("MinimumRange")) if jd.get("PositionRemuneration") else None,
                "salary_max": _safe_int(jd.get("PositionRemuneration", [{}])[0].get("MaximumRange")) if jd.get("PositionRemuneration") else None,
                "employment_type": jd.get("PositionSchedule", [{}])[0].get("Name") if jd.get("PositionSchedule") else None,
            })
        logger.info("usajobs.fetched", extra={"count": len(results)})
        return results
    except Exception as exc:
        logger.warning("usajobs.failed: %s", exc)
        return []


def _fetch_remoteok(tag: str = "healthcare") -> list[dict[str, Any]]:
    """
    Fetch from RemoteOK public JSON API.
    Returns raw job dicts with _feed_source='remoteok'.
    """
    url = f"https://remoteok.com/api?tag={tag}"
    try:
        with httpx.Client(timeout=15, headers={"User-Agent": "job-agent-v1"}) as client:
            resp = client.get(url)
            resp.raise_for_status()
            jobs = resp.json()

        # First item is usually a legal disclaimer — skip it
        results = []
        for job in jobs:
            if not isinstance(job, dict) or "id" not in job:
                continue
            results.append({
                "_feed_source": "remoteok",
                "title": job.get("position", ""),
                "company": job.get("company", "Unknown"),
                "location": "Remote",
                "url": job.get("url", f"https://remoteok.com/jobs/{job['id']}"),
                "description": _clean_html(job.get("description", "")),
                "published": job.get("date", ""),
                "id": str(job.get("id", "")),
                "tags": job.get("tags", []),
                "is_remote": True,
            })
        logger.info("remoteok.fetched", extra={"count": len(results)})
        return results
    except Exception as exc:
        logger.warning("remoteok.failed: %s", exc)
        return []


def _safe_int(value: Any) -> int | None:
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Adapter class
# ──────────────────────────────────────────────────────────────────────────────

class LiveFeedAdapter(JobSourceAdapter):
    """
    Aggregates four live job feed sources into the standard adapter interface.

    Config keys (all optional):
        themuse_query       (str)  default: "Business Analyst"
        themuse_category    (str)  default: "Data and Analytics"
        arbeitnow_query     (str)  default: "healthcare business analyst"
        usajobs_keyword     (str)  default: "Healthcare Business Analyst"
        usajobs_api_key     (str)  required for USAJobs; falls back to env USAJOBS_API_KEY
        remoteok_tag        (str)  default: "healthcare"
        enable_themuse      (bool) default: True
        enable_arbeitnow    (bool) default: True
        enable_usajobs      (bool) default: False  (requires API key)
        enable_remoteok     (bool) default: True

    Legacy config keys still accepted but ignored (feeds deprecated):
        enable_indeed, indeed_query, indeed_location
        enable_dice, dice_query
    """

    def __init__(self, source_name: str, config: dict[str, Any] | None = None) -> None:
        super().__init__(source_name, config)
        self._themuse_query    = self.config.get("themuse_query", "Business Analyst")
        self._themuse_category = self.config.get("themuse_category", "Data and Analytics")
        self._arbeitnow_query  = self.config.get("arbeitnow_query", "healthcare business analyst")
        self._usajobs_keyword  = self.config.get("usajobs_keyword", "Healthcare Business Analyst")
        self._usajobs_api_key  = self.config.get("usajobs_api_key", "")
        self._remoteok_tag     = self.config.get("remoteok_tag", "healthcare")
        self._enable_themuse   = self.config.get("enable_themuse", True)
        self._enable_arbeitnow = self.config.get("enable_arbeitnow", True)
        self._enable_usajobs   = self.config.get("enable_usajobs", False)
        self._enable_remoteok  = self.config.get("enable_remoteok", True)

        # Try to pull USAJobs key from env if not in config
        if not self._usajobs_api_key:
            import os
            self._usajobs_api_key = os.getenv("USAJOBS_API_KEY", "")

    def fetch_jobs(self) -> list[dict[str, Any]]:
        """Fetch from all enabled live feeds. Each feed failure is isolated."""
        all_jobs: list[dict[str, Any]] = []

        if self._enable_themuse:
            all_jobs.extend(_fetch_themuse(self._themuse_query, self._themuse_category))

        if self._enable_arbeitnow:
            all_jobs.extend(_fetch_arbeitnow(self._arbeitnow_query))

        if self._enable_usajobs:
            all_jobs.extend(_fetch_usajobs(self._usajobs_keyword, self._usajobs_api_key))

        if self._enable_remoteok:
            all_jobs.extend(_fetch_remoteok(self._remoteok_tag))

        logger.info(
            "live_feeds.fetch_complete",
            extra={"source": self.source_name, "total_fetched": len(all_jobs)},
        )
        return all_jobs

    def normalize_job(self, raw_job: dict[str, Any]) -> JobRecord:
        """Convert a raw feed entry into a standardised JobRecord."""
        feed_src = raw_job.get("_feed_source", "unknown")
        title = raw_job.get("title", "").strip()
        company = raw_job.get("company", "Unknown").strip()
        location = raw_job.get("location", "").strip()
        apply_url = raw_job.get("url", "").strip()
        description = raw_job.get("description", "").strip()
        published = raw_job.get("published", "")

        full_text = f"{title} {description}"
        is_remote = raw_job.get("is_remote", False) or _detect_remote(f"{location} {description}")

        # Employment type
        employment_type = raw_job.get("employment_type")
        if not employment_type:
            text_lower = full_text.lower()
            if "contract" in text_lower:
                employment_type = "contract"
            elif "part-time" in text_lower or "part time" in text_lower:
                employment_type = "part-time"
            elif "full-time" in text_lower or "full time" in text_lower:
                employment_type = "full-time"

        # Use a clean short source label so the dashboard filter is readable
        _source_label_map = {
            "themuse": "The Muse",
            "arbeitnow": "Arbeitnow",
            "remoteok": "RemoteOK",
            "usajobs": "USAJobs",
            "indeed": "Indeed",
            "dice": "Dice",
        }
        clean_source = _source_label_map.get(feed_src, feed_src.title())

        return JobRecord(
            source=clean_source,
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
        """SHA-256 of feed source + job URL — same job on multiple boards deduplicates."""
        feed_src = raw_job.get("_feed_source", "unknown")
        job_url = raw_job.get("url", raw_job.get("id", ""))
        key = f"{feed_src}:{job_url}".lower().strip()
        return hashlib.sha256(key.encode()).hexdigest()[:64]
