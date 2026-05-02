from __future__ import annotations

from app.models.candidate import Candidate, CandidatePreference, CandidateSkill
from app.models.job import JobNormalized
from app.services.resume_tailoring import build_tailoring_suggestions


def test_tailoring_flags_requested_skills_without_resume_evidence() -> None:
    candidate = Candidate(
        id=1,
        name="Taylor Candidate",
        resume_text="Healthcare analyst with SQL, claims, and UAT experience.",
    )
    candidate.skills = [
        CandidateSkill(candidate_id=1, skill_name="SQL"),
        CandidateSkill(candidate_id=1, skill_name="UAT"),
    ]
    candidate.preference = CandidatePreference(
        candidate_id=1,
        preferred_titles=[],
        employment_preferences=[],
        location_preferences=[],
        domain_expertise=["Healthcare"],
        must_have_keywords=["Claims"],
        exclude_keywords=[],
    )
    job = JobNormalized(
        id=10,
        source="test",
        title="Healthcare Business Analyst",
        company="Acme Health",
        is_remote=True,
        description="Need SQL, UAT, Facets, and HL7 experience.",
        keywords_extracted=["SQL", "UAT", "Facets", "HL7"],
    )

    suggestions, gaps = build_tailoring_suggestions(
        candidate,
        job,
        recruiter_context="Recruiter asked to highlight Facets if available.",
    )

    assert any("SQL" in item["skill_tags"] or "UAT" in item["skill_tags"] for item in suggestions)
    gap_skills = {gap["skill"] for gap in gaps}
    assert "Facets" in gap_skills
    assert "HL7" in gap_skills
