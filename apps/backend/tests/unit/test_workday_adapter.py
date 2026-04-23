from app.services.source_adapters.registry import build_source_adapter
from app.services.source_adapters.workday import WorkdayJobsAdapter


def test_workday_adapter_normalizes_basic_job_payload() -> None:
    adapter = WorkdayJobsAdapter(
        "Workday Test",
        {
            "url": "https://example.myworkdayjobs.com/jobs",
            "job_url_prefix": "https://example.myworkdayjobs.com/en-US/careers",
            "company_name": "Example Health",
        },
    )

    record = adapter.normalize_job(
        {
            "title": "Healthcare Business Analyst",
            "externalPath": "JR-1001",
            "postedOn": "2026-04-23T05:00:00Z",
            "locationsText": "Remote",
            "timeType": "Full time",
            "description": "Healthcare BA with claims and FHIR.",
        }
    )

    assert record.title == "Healthcare Business Analyst"
    assert record.company == "Example Health"
    assert record.location == "Remote"
    assert record.is_remote is True
    assert record.apply_url == "https://example.myworkdayjobs.com/en-US/careers/JR-1001"
    assert record.posted_date == "2026-04-23T05:00:00Z"


def test_registry_builds_workday_adapter() -> None:
    adapter = build_source_adapter("workday_jobs", "Workday", {"url": "https://example/jobs"})
    assert isinstance(adapter, WorkdayJobsAdapter)
