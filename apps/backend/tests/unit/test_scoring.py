from app.models.candidate import Candidate, CandidatePreference, CandidateSkill
from app.models.job import JobNormalized
from app.scoring.engine import _score_title_match, score_candidate_to_job


def test_score_title_match_prefers_exact_match() -> None:
    candidate = Candidate(
        name="Taylor Analyst",
        work_authorization="US Citizen",
        years_experience=7,
        active=True,
    )
    candidate.preference = CandidatePreference(
        candidate_id=1,
        preferred_titles=["Senior Healthcare Business Analyst", "Healthcare BA"],
        employment_preferences=["full-time"],
        location_preferences=["remote"],
        domain_expertise=["claims", "payer"],
        must_have_keywords=["FHIR", "HL7", "EDI"],
        exclude_keywords=[],
    )

    job = JobNormalized(
        source="test",
        title="Senior Healthcare Business Analyst",
        company="CareAxis",
        location="Remote",
        is_remote=True,
        employment_type="full-time",
        domain_tags=["claims", "payer"],
        visa_hints=["us work authorization required"],
        keywords_extracted=["FHIR", "HL7"],
        duplicate_reasons=[],
    )

    assert _score_title_match(candidate, job) == 25.0


def test_score_candidate_to_job_returns_weighted_result_and_explanation() -> None:
    candidate = Candidate(
        name="Jordan Interop",
        work_authorization="Green Card",
        years_experience=8,
        active=True,
    )
    candidate.preference = CandidatePreference(
        candidate_id=1,
        preferred_titles=["Healthcare Interoperability Analyst"],
        employment_preferences=["full-time"],
        location_preferences=["remote", "texas"],
        domain_expertise=["interoperability", "payer"],
        must_have_keywords=["FHIR", "HL7", "EDI"],
        exclude_keywords=[],
    )
    candidate.skills = [
        CandidateSkill(candidate_id=1, skill_name="FHIR", years_used=4),
        CandidateSkill(candidate_id=1, skill_name="HL7", years_used=5),
        CandidateSkill(candidate_id=1, skill_name="EDI", years_used=6),
    ]

    job = JobNormalized(
        source="test",
        title="Healthcare Interoperability Analyst",
        company="CareBridge",
        location="Remote - Texas",
        is_remote=True,
        employment_type="full-time",
        domain_tags=["interoperability", "payer"],
        visa_hints=["us work authorization required"],
        keywords_extracted=["FHIR", "HL7", "EDI"],
        description="FHIR and HL7 integration work for payer interoperability programs.",
        duplicate_reasons=[],
    )

    result = score_candidate_to_job(candidate, job)

    assert result.total_score == 100.0
    assert result.priority_bucket == "High"
    assert result.title_score == 25.0
    assert result.domain_score == 20.0
    assert result.skills_score == 20.0
    assert result.experience_score == 10.0
    assert result.employment_preference_score == 10.0
    assert result.visa_score == 10.0
    assert result.location_score == 5.0
    assert "Jordan Interop scores 100.00/100" in result.explanation
