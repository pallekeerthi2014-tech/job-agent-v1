from datetime import datetime, timezone

from app.parsers.freshness import validate_job_freshness


def test_validate_job_freshness_accepts_recent_relative_times() -> None:
    reference_time = datetime(2026, 4, 22, 12, 0, tzinfo=timezone.utc)

    result = validate_job_freshness("23 hours ago", fetched_at=reference_time)

    assert result.freshness_status == "verified_recent"
    assert result.freshness_age_hours == 23
    assert result.posted_date.isoformat() == "2026-04-21"


def test_validate_job_freshness_marks_old_jobs_stale() -> None:
    reference_time = datetime(2026, 4, 22, 12, 0, tzinfo=timezone.utc)

    result = validate_job_freshness("3 days ago", fetched_at=reference_time)

    assert result.freshness_status == "verified_stale"
    assert result.freshness_age_hours == 72


def test_validate_job_freshness_rejects_ambiguous_labels() -> None:
    reference_time = datetime(2026, 4, 22, 12, 0, tzinfo=timezone.utc)

    result = validate_job_freshness("Actively Hiring", fetched_at=reference_time)

    assert result.freshness_status == "unverified"
    assert result.freshness_age_hours is None
    assert result.posted_date is None
