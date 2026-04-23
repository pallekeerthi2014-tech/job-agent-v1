from app.models.candidate import Candidate, CandidatePreference, CandidateSkill
from app.models.employee import Employee
from app.models.source import JobSource


def test_run_daily_pipeline_endpoint_processes_jobs_and_creates_matches(client, db_session) -> None:
    employee = Employee(name="Avery Ops", email="avery.ops@example.com")
    candidate = Candidate(
        name="Morgan Healthcare BA",
        work_authorization="US Citizen",
        years_experience=7,
        salary_min=120000,
        salary_unit="year",
        active=True,
    )
    source = JobSource(
        name="sample-health-feed",
        adapter_type="configurable_template",
        enabled=True,
        config={
            "sample_jobs": [
                {
                    "id": "job-1",
                    "title": "Healthcare Business Analyst",
                    "company": "CareFirst Analytics",
                    "location": "Remote",
                    "employment_type": "full-time",
                    "apply_url": "https://jobs.example.com/apply/job-1?utm_source=test",
                    "posted_date": "2 hours ago",
                    "description": (
                        "Remote healthcare business analyst role focused on claims, EDI 837/835, "
                        "FHIR and HL7 integrations, HEDIS quality reporting, and no sponsorship."
                    ),
                }
            ],
            "field_mapping": {
                "title": "title",
                "company": "company",
                "location": "location",
                "employment_type": "employment_type",
                "apply_url": "apply_url",
                "posted_date": "posted_date",
                "description": "description",
                "external_job_id": "id",
            },
        },
    )

    db_session.add(employee)
    db_session.flush()
    db_session.add(candidate)
    db_session.flush()
    candidate.assigned_employee = employee.id
    candidate.preference = CandidatePreference(
        candidate_id=candidate.id,
        preferred_titles=["Healthcare Business Analyst"],
        employment_preferences=["full-time"],
        location_preferences=["remote"],
        domain_expertise=["claims", "edi", "interoperability", "quality", "payer"],
        must_have_keywords=["FHIR", "HL7", "EDI"],
        exclude_keywords=[],
    )
    candidate.skills = [
        CandidateSkill(candidate_id=candidate.id, skill_name="FHIR", years_used=4),
        CandidateSkill(candidate_id=candidate.id, skill_name="HL7", years_used=5),
        CandidateSkill(candidate_id=candidate.id, skill_name="EDI", years_used=6),
    ]
    db_session.add(source)
    db_session.commit()

    response = client.post("/api/v1/admin/run-daily-pipeline")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["summary"]["sources_processed"] == 1
    assert payload["summary"]["raw_jobs_stored"] == 1
    assert payload["summary"]["jobs_skipped_irrelevant"] == 0
    assert payload["summary"]["normalized_jobs"] == 1
    assert payload["summary"]["scored_matches"] == 1
    assert payload["summary"]["work_queue_items"] == 1


def test_work_queue_retrieval_supports_filters(client, db_session) -> None:
    employee = Employee(name="Riley Queue", email="riley.queue@example.com")
    candidate = Candidate(
        name="Dana Interop Analyst",
        work_authorization="Green Card",
        years_experience=8,
        salary_min=125000,
        salary_unit="year",
        active=True,
    )
    source = JobSource(
        name="queue-health-feed",
        adapter_type="configurable_template",
        enabled=True,
        config={
            "sample_jobs": [
                {
                    "id": "job-queue-1",
                    "title": "Healthcare Interoperability Analyst",
                    "company": "WellSync",
                    "location": "Remote",
                    "employment_type": "full-time",
                    "apply_url": "https://jobs.example.com/apply/job-queue-1",
                    "posted_date": "4 hours ago",
                    "description": "Remote FHIR HL7 EDI payer integration role. Visa sponsorship available.",
                }
            ],
            "field_mapping": {
                "title": "title",
                "company": "company",
                "location": "location",
                "employment_type": "employment_type",
                "apply_url": "apply_url",
                "posted_date": "posted_date",
                "description": "description",
                "external_job_id": "id",
            },
        },
    )

    db_session.add(employee)
    db_session.flush()
    db_session.add(candidate)
    db_session.flush()
    candidate.assigned_employee = employee.id
    candidate.preference = CandidatePreference(
        candidate_id=candidate.id,
        preferred_titles=["Healthcare Interoperability Analyst"],
        employment_preferences=["full-time"],
        location_preferences=["remote"],
        domain_expertise=["interoperability", "payer"],
        must_have_keywords=["FHIR", "HL7", "EDI"],
        exclude_keywords=[],
    )
    candidate.skills = [
        CandidateSkill(candidate_id=candidate.id, skill_name="FHIR", years_used=4),
        CandidateSkill(candidate_id=candidate.id, skill_name="HL7", years_used=4),
        CandidateSkill(candidate_id=candidate.id, skill_name="EDI", years_used=4),
    ]
    db_session.add(source)
    db_session.commit()

    pipeline_response = client.post("/api/v1/admin/run-daily-pipeline")
    assert pipeline_response.status_code == 200

    response = client.get(
        "/api/v1/work-queues",
        params={
            "employee_id": employee.id,
            "candidate_id": candidate.id,
            "priority": "High",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 1
    queue_item = payload["items"][0]
    assert queue_item["employee_id"] == employee.id
    assert queue_item["candidate_id"] == candidate.id
    assert queue_item["priority_bucket"] == "High"
    assert "Dana Interop Analyst scores" in queue_item["explanation"]


def test_pipeline_excludes_stale_or_unverified_jobs_from_work_queue(client, db_session) -> None:
    employee = Employee(name="Freshness Ops", email="freshness.ops@example.com")
    candidate = Candidate(
        name="Taylor Recent",
        work_authorization="US Citizen",
        years_experience=7,
        salary_min=115000,
        salary_unit="year",
        active=True,
    )
    source = JobSource(
        name="freshness-feed",
        adapter_type="configurable_template",
        enabled=True,
        config={
            "sample_jobs": [
                {
                    "id": "job-recent",
                    "title": "Healthcare Business Analyst",
                    "company": "Recent Health",
                    "location": "Remote",
                    "employment_type": "full-time",
                    "apply_url": "https://jobs.example.com/apply/job-recent",
                    "posted_date": "6 hours ago",
                    "description": "Remote healthcare BA with claims, EDI, and FHIR.",
                },
                {
                    "id": "job-stale",
                    "title": "Healthcare Business Analyst",
                    "company": "Old Health",
                    "location": "Remote",
                    "employment_type": "full-time",
                    "apply_url": "https://jobs.example.com/apply/job-stale",
                    "posted_date": "5 days ago",
                    "description": "Older healthcare BA role with claims and FHIR.",
                },
                {
                    "id": "job-ambiguous",
                    "title": "Healthcare Business Analyst",
                    "company": "Unclear Health",
                    "location": "Remote",
                    "employment_type": "full-time",
                    "apply_url": "https://jobs.example.com/apply/job-ambiguous",
                    "posted_date": "Actively Hiring",
                    "description": "Ambiguous freshness healthcare BA role.",
                },
            ],
            "field_mapping": {
                "title": "title",
                "company": "company",
                "location": "location",
                "employment_type": "employment_type",
                "apply_url": "apply_url",
                "posted_date": "posted_date",
                "description": "description",
                "external_job_id": "id",
            },
        },
    )

    db_session.add(employee)
    db_session.flush()
    db_session.add(candidate)
    db_session.flush()
    candidate.assigned_employee = employee.id
    candidate.preference = CandidatePreference(
        candidate_id=candidate.id,
        preferred_titles=["Healthcare Business Analyst"],
        employment_preferences=["full-time"],
        location_preferences=["remote"],
        domain_expertise=["claims", "edi", "interoperability"],
        must_have_keywords=["FHIR", "EDI"],
        exclude_keywords=[],
    )
    candidate.skills = [
        CandidateSkill(candidate_id=candidate.id, skill_name="FHIR", years_used=4),
        CandidateSkill(candidate_id=candidate.id, skill_name="EDI", years_used=4),
    ]
    db_session.add(source)
    db_session.commit()

    pipeline_response = client.post("/api/v1/admin/run-daily-pipeline")
    assert pipeline_response.status_code == 200

    jobs_response = client.get("/api/v1/jobs", params={"freshness_status": "verified_recent"})
    assert jobs_response.status_code == 200
    assert jobs_response.json()["meta"]["total"] == 1

    queue_response = client.get("/api/v1/work-queues", params={"employee_id": employee.id})
    assert queue_response.status_code == 200
    assert queue_response.json()["meta"]["total"] == 1


def test_pipeline_skips_irrelevant_non_analyst_titles(client, db_session) -> None:
    employee = Employee(name="Filter Ops", email="filter.ops@example.com")
    candidate = Candidate(
        name="Jamie Analyst",
        work_authorization="US Citizen",
        years_experience=6,
        salary_min=105000,
        salary_unit="year",
        active=True,
    )
    source = JobSource(
        name="role-filter-feed",
        adapter_type="configurable_template",
        enabled=True,
        config={
            "sample_jobs": [
                {
                    "id": "job-keep",
                    "title": "Business Analyst",
                    "company": "Relevant Health",
                    "location": "Remote",
                    "employment_type": "full-time",
                    "apply_url": "https://jobs.example.com/apply/job-keep",
                    "posted_date": "3 hours ago",
                    "description": "Healthcare business analyst role.",
                },
                {
                    "id": "job-skip",
                    "title": "Software Engineer",
                    "company": "Irrelevant Health",
                    "location": "Remote",
                    "employment_type": "full-time",
                    "apply_url": "https://jobs.example.com/apply/job-skip",
                    "posted_date": "2 hours ago",
                    "description": "Backend engineering role.",
                },
            ],
            "field_mapping": {
                "title": "title",
                "company": "company",
                "location": "location",
                "employment_type": "employment_type",
                "apply_url": "apply_url",
                "posted_date": "posted_date",
                "description": "description",
                "external_job_id": "id",
            },
        },
    )

    db_session.add(employee)
    db_session.flush()
    db_session.add(candidate)
    db_session.flush()
    candidate.assigned_employee = employee.id
    candidate.preference = CandidatePreference(
        candidate_id=candidate.id,
        preferred_titles=["Business Analyst"],
        employment_preferences=["full-time"],
        location_preferences=["remote"],
        domain_expertise=["claims"],
        must_have_keywords=["FHIR"],
        exclude_keywords=[],
    )
    candidate.skills = [CandidateSkill(candidate_id=candidate.id, skill_name="FHIR", years_used=3)]
    db_session.add(source)
    db_session.commit()

    response = client.post("/api/v1/admin/run-daily-pipeline")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["raw_jobs_stored"] == 1
    assert payload["summary"]["jobs_skipped_irrelevant"] == 1
