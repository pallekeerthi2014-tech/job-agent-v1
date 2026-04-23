from app.parsers.normalizer import (
    detect_remote,
    extract_healthcare_domain_tags,
    extract_salary_ranges,
    extract_work_authorization_hints,
)


def test_detect_remote_matches_text_and_location() -> None:
    assert detect_remote("This is a remote healthcare BA role with WFH flexibility.", "Chicago, IL") is True
    assert detect_remote("Hybrid business analyst role", "Remote - USA") is True
    assert detect_remote("Onsite claims analyst role", "Dallas, TX") is False


def test_extract_salary_ranges_handles_numeric_and_k_formats() -> None:
    assert extract_salary_ranges("Compensation is $95,000-$120,000 plus bonus.") == (95000, 120000)
    assert extract_salary_ranges("Target pay is 110k to 135k for the right candidate.") == (110000, 135000)
    assert extract_salary_ranges("Competitive salary, DOE.") == (None, None)


def test_extract_healthcare_domain_tags_returns_expected_tags() -> None:
    text = (
        "Support claims adjudication, EDI 837 flows, FHIR APIs, HEDIS reporting, "
        "Medicaid programs, and population health analytics."
    )
    assert extract_healthcare_domain_tags(text) == [
        "claims",
        "edi",
        "interoperability",
        "payer",
        "population-health",
        "quality",
    ]


def test_extract_work_authorization_hints_detects_multiple_patterns() -> None:
    text = (
        "US work authorization required. No sponsorship available for this opening. "
        "US citizen candidates are preferred."
    )
    assert extract_work_authorization_hints(text) == [
        "citizenship preferred",
        "no sponsorship",
        "us work authorization required",
    ]
