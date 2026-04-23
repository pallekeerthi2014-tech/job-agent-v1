from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone


STRICT_MAX_AGE_HOURS = 168

_AMBIGUOUS_PATTERNS = (
    r"\breposted\b",
    r"\bongoing\b",
    r"\bopen until filled\b",
    r"\bactive hiring\b",
    r"\bfew days ago\b",
    r"\brecently\b",
)


@dataclass(slots=True)
class FreshnessValidationResult:
    posted_date: date | None
    posted_at_text: str | None
    freshness_status: str
    freshness_age_hours: int | None

    @property
    def is_recent(self) -> bool:
        return self.freshness_status == "verified_recent"


def validate_job_freshness(
    posted_value: object,
    *,
    fetched_at: datetime | None = None,
    max_age_hours: int = STRICT_MAX_AGE_HOURS,
) -> FreshnessValidationResult:
    reference_time = _ensure_utc(fetched_at or datetime.now(timezone.utc))
    posted_at_text = _string_value(posted_value)

    if posted_value in (None, ""):
        return FreshnessValidationResult(None, posted_at_text, "unverified", None)

    parsed_at = _parse_posted_at(posted_value, reference_time)
    if parsed_at is None:
        return FreshnessValidationResult(None, posted_at_text, "unverified", None)

    age_delta = reference_time - parsed_at
    age_hours = max(int(age_delta.total_seconds() // 3600), 0)
    status = "verified_recent" if age_delta <= timedelta(hours=max_age_hours) else "verified_stale"
    return FreshnessValidationResult(parsed_at.date(), posted_at_text, status, age_hours)


def _parse_posted_at(posted_value: object, reference_time: datetime) -> datetime | None:
    if isinstance(posted_value, datetime):
        return _ensure_utc(posted_value)
    if isinstance(posted_value, date):
        return datetime.combine(posted_value, datetime.min.time(), tzinfo=timezone.utc)

    if not isinstance(posted_value, str):
        return None

    cleaned = re.sub(r"\s+", " ", posted_value.strip())
    if not cleaned:
        return None

    lowered = cleaned.lower()
    if any(re.search(pattern, lowered) for pattern in _AMBIGUOUS_PATTERNS):
        return None

    if lowered in {"today", "just posted", "just now"}:
        return reference_time
    if lowered == "yesterday":
        return reference_time - timedelta(hours=24)

    minute_match = re.fullmatch(r"(\d+)\s+minutes?\s+ago", lowered)
    if minute_match:
        return reference_time - timedelta(minutes=int(minute_match.group(1)))

    hour_match = re.fullmatch(r"(\d+)\s+hours?\s+ago", lowered)
    if hour_match:
        return reference_time - timedelta(hours=int(hour_match.group(1)))

    day_match = re.fullmatch(r"(\d+)\s+days?\s+ago", lowered)
    if day_match:
        return reference_time - timedelta(days=int(day_match.group(1)))

    for parser in (_parse_iso_datetime, _parse_known_date_formats):
        parsed = parser(cleaned)
        if parsed is not None:
            return parsed

    return None


def _parse_iso_datetime(value: str) -> datetime | None:
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return _ensure_utc(parsed)
    except ValueError:
        pass

    try:
        parsed_date = date.fromisoformat(normalized)
        return datetime.combine(parsed_date, datetime.min.time(), tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_known_date_formats(value: str) -> datetime | None:
    for fmt in ("%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _string_value(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
