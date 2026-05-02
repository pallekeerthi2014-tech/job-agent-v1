from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.candidate import Candidate, CandidateSkill
from app.models.job import JobNormalized


def test_create_resume_tailoring_draft(client, db_session: Session, auth_headers) -> None:
    candidate = Candidate(
        name="Resume Ready",
        assigned_employee=None,
        resume_filename="candidate_1.docx",
        resume_text="Healthcare BA with SQL, claims, UAT, and EDI project experience.",
        active=True,
    )
    db_session.add(candidate)
    db_session.flush()
    candidate.skills = [
        CandidateSkill(candidate_id=candidate.id, skill_name="SQL"),
        CandidateSkill(candidate_id=candidate.id, skill_name="UAT"),
    ]
    job = JobNormalized(
        source="test",
        title="Healthcare Business Analyst",
        company="Acme Health",
        is_remote=True,
        freshness_status="verified_recent",
        description="Looking for SQL, UAT, Facets, and EDI.",
        keywords_extracted=["SQL", "UAT", "Facets", "EDI"],
        domain_tags=["healthcare"],
        visa_hints=[],
        duplicate_reasons=[],
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(candidate)
    db_session.refresh(job)

    response = client.post(
        "/api/v1/resume-tailoring/drafts",
        headers=auth_headers,
        json={
            "candidate_id": candidate.id,
            "job_id": job.id,
            "recruiter_context": "Recruiter asked for Facets if the candidate has it.",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["candidate_id"] == candidate.id
    assert payload["job_id"] == job.id
    assert payload["suggested_edits"]
    assert any(gap["skill"] == "Facets" for gap in payload["skill_gaps"])
