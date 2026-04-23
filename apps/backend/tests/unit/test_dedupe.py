from datetime import date

from app.models.job import JobNormalized
from app.parsers.normalizer import canonicalize_apply_url, normalized_description_content_hash
from app.services.dedupe import JobDedupeService


def test_dedupe_marks_probable_duplicates_and_keeps_latest_active(db_session) -> None:
    canonical_url = canonicalize_apply_url("https://jobs.example.com/role/1?utm_source=linkedin")
    description_hash = normalized_description_content_hash("FHIR and claims integration for payer operations")

    older_job = JobNormalized(
        source="feed-a",
        title="Healthcare Business Analyst",
        company="HealthCo",
        location="Remote",
        apply_url="https://jobs.example.com/role/1?utm_source=linkedin",
        canonical_apply_url=canonical_url,
        description="FHIR and claims integration for payer operations",
        normalized_description_hash=description_hash,
        posted_date=date(2026, 4, 20),
        domain_tags=["claims"],
        visa_hints=[],
        keywords_extracted=["FHIR"],
        dedupe_hash="older",
        duplicate_reasons=[],
        is_active=True,
    )
    newer_job = JobNormalized(
        source="feed-b",
        title="Healthcare Business Analyst",
        company="HealthCo",
        location="Remote",
        apply_url="https://jobs.example.com/role/1?utm_medium=email",
        canonical_apply_url=canonical_url,
        description="FHIR and claims integration for payer operations",
        normalized_description_hash=description_hash,
        posted_date=date(2026, 4, 21),
        domain_tags=["claims"],
        visa_hints=[],
        keywords_extracted=["FHIR"],
        dedupe_hash="newer",
        duplicate_reasons=[],
        is_active=True,
    )

    db_session.add_all([older_job, newer_job])
    db_session.commit()

    results = JobDedupeService(db_session).mark_probable_duplicates()

    db_session.refresh(older_job)
    db_session.refresh(newer_job)

    assert any(result.active_job_id == newer_job.id for result in results)
    assert newer_job.is_active is True
    assert older_job.is_active is False
    assert older_job.probable_duplicate_of_job_id == newer_job.id
    assert "canonical_apply_url" in older_job.duplicate_reasons
