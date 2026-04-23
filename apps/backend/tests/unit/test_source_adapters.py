from app.services.source_adapters.greenhouse import GreenhouseBoardAdapter
from app.services.source_adapters.lever import LeverPostingsAdapter
from app.services.source_adapters.registry import build_source_adapter


def test_greenhouse_adapter_normalizes_basic_job_payload() -> None:
    adapter = GreenhouseBoardAdapter("Greenhouse Test", {"board_token": "demo", "company_name": "Demo Co"})

    record = adapter.normalize_job(
        {
            "id": 101,
            "title": "Healthcare Business Analyst",
            "absolute_url": "https://boards.greenhouse.io/demo/jobs/101",
            "updated_at": "2026-04-23T05:00:00Z",
            "location": {"name": "Remote"},
            "content": "Healthcare BA with claims and FHIR.",
        }
    )

    assert record.title == "Healthcare Business Analyst"
    assert record.company == "Demo Co"
    assert record.location == "Remote"
    assert record.is_remote is True
    assert record.apply_url == "https://boards.greenhouse.io/demo/jobs/101"
    assert record.posted_date == "2026-04-23T05:00:00Z"


def test_lever_adapter_normalizes_basic_job_payload() -> None:
    adapter = LeverPostingsAdapter("Lever Test", {"company_handle": "demo", "company_name": "Demo Co"})

    record = adapter.normalize_job(
        {
            "id": "abc123",
            "text": "Healthcare Interoperability Analyst",
            "hostedUrl": "https://jobs.lever.co/demo/abc123",
            "createdAtText": "6 hours ago",
            "categories": {
                "location": "Remote",
                "commitment": "Full-time",
            },
            "descriptionPlain": "FHIR HL7 integration analyst role.",
        }
    )

    assert record.title == "Healthcare Interoperability Analyst"
    assert record.company == "Demo Co"
    assert record.location == "Remote"
    assert record.is_remote is True
    assert record.apply_url == "https://jobs.lever.co/demo/abc123"
    assert record.posted_date == "6 hours ago"


def test_registry_builds_new_board_adapters() -> None:
    greenhouse = build_source_adapter("greenhouse_board", "GH", {"board_token": "demo"})
    lever = build_source_adapter("lever_postings", "Lever", {"company_handle": "demo"})

    assert isinstance(greenhouse, GreenhouseBoardAdapter)
    assert isinstance(lever, LeverPostingsAdapter)
