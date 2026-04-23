from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db import crud
from app.schemas.application import ApplicationCreate, ApplicationPage, ApplicationRead
from app.schemas.candidate import (
    CandidatePage,
    CandidateCreate,
    CandidatePreferenceCreate,
    CandidatePreferenceRead,
    CandidatePreferenceUpsert,
    CandidateRead,
    CandidateUpdate,
    CandidateSkillCreate,
    CandidateSkillRead,
)
from app.schemas.employee import EmployeeCreate, EmployeeRead
from app.schemas.job import JobNormalizedCreate, JobNormalizedPage, JobNormalizedRead, JobRawCreate, JobRawRead
from app.schemas.match import JobCandidateMatchCreate, JobCandidateMatchPage, JobCandidateMatchRead
from app.schemas.pagination import PageMeta
from app.schemas.work_queue import EmployeeWorkQueuePage
from app.services.pipeline import run_daily_pipeline

router = APIRouter(prefix="/api/v1")


@router.get("/candidates", response_model=CandidatePage)
def list_candidates(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="id"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    candidate_id: int | None = Query(default=None),
    employee_id: int | None = Query(default=None),
) -> CandidatePage:
    total, items = crud.list_candidates(
        db,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        candidate_id=candidate_id,
        employee_id=employee_id,
    )
    return CandidatePage(items=items, meta=PageMeta(total=total, limit=limit, offset=offset))


@router.post("/candidates", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate(payload: CandidateCreate, db: Session = Depends(get_db)) -> CandidateRead:
    return crud.create_candidate(db, payload)


@router.get("/candidates/{candidate_id}", response_model=CandidateRead)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)) -> CandidateRead:
    candidate = crud.get_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


@router.put("/candidates/{candidate_id}", response_model=CandidateRead)
def update_candidate(
    candidate_id: int,
    payload: CandidateUpdate,
    db: Session = Depends(get_db),
) -> CandidateRead:
    candidate = crud.update_candidate(db, candidate_id, payload)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


@router.delete("/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)) -> Response:
    deleted = crud.delete_candidate(db, candidate_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/candidate-preferences", response_model=list[CandidatePreferenceRead])
def list_candidate_preferences(db: Session = Depends(get_db)) -> list[CandidatePreferenceRead]:
    return crud.list_candidate_preferences(db)


@router.put("/candidate-preferences/{candidate_id}", response_model=CandidatePreferenceRead)
def upsert_candidate_preference(
    candidate_id: int,
    payload: CandidatePreferenceUpsert,
    db: Session = Depends(get_db),
) -> CandidatePreferenceRead:
    return crud.upsert_candidate_preference(
        db,
        CandidatePreferenceCreate(candidate_id=candidate_id, **payload.model_dump()),
    )


@router.get("/candidate-skills", response_model=list[CandidateSkillRead])
def list_candidate_skills(
    candidate_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CandidateSkillRead]:
    return crud.list_candidate_skills(db, candidate_id=candidate_id)


@router.post("/candidate-skills", response_model=CandidateSkillRead, status_code=status.HTTP_201_CREATED)
def create_candidate_skill(payload: CandidateSkillCreate, db: Session = Depends(get_db)) -> CandidateSkillRead:
    return crud.create_candidate_skill(db, payload)


@router.get("/employees", response_model=list[EmployeeRead])
def list_employees(db: Session = Depends(get_db)) -> list[EmployeeRead]:
    return crud.list_employees(db)


@router.post("/employees", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)) -> EmployeeRead:
    return crud.create_employee(db, payload)


@router.get("/jobs/raw", response_model=list[JobRawRead])
def list_jobs_raw(db: Session = Depends(get_db)) -> list[JobRawRead]:
    return crud.list_jobs_raw(db)


@router.post("/jobs/raw", response_model=JobRawRead, status_code=status.HTTP_201_CREATED)
def create_job_raw(payload: JobRawCreate, db: Session = Depends(get_db)) -> JobRawRead:
    return crud.create_job_raw(db, payload)


@router.get("/jobs", response_model=JobNormalizedPage)
@router.get("/jobs/normalized", response_model=JobNormalizedPage, include_in_schema=False)
def list_jobs_normalized(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="posted_date"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    source: str | None = Query(default=None),
    posted_date: date | None = Query(default=None),
    freshness_status: str | None = Query(default=None),
) -> JobNormalizedPage:
    total, items = crud.list_jobs_normalized(
        db,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        source=source,
        posted_date=posted_date,
        freshness_status=freshness_status,
    )
    return JobNormalizedPage(items=items, meta=PageMeta(total=total, limit=limit, offset=offset))


@router.post("/jobs", response_model=JobNormalizedRead, status_code=status.HTTP_201_CREATED)
@router.post("/jobs/normalized", response_model=JobNormalizedRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_job_normalized(payload: JobNormalizedCreate, db: Session = Depends(get_db)) -> JobNormalizedRead:
    return crud.create_job_normalized(db, payload)


@router.get("/matches", response_model=JobCandidateMatchPage)
def list_matches(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="score"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    candidate_id: int | None = Query(default=None),
    employee_id: int | None = Query(default=None),
    score: float | None = Query(default=None),
    priority: int | None = Query(default=None),
) -> JobCandidateMatchPage:
    total, items = crud.list_job_candidate_matches(
        db,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        candidate_id=candidate_id,
        employee_id=employee_id,
        min_score=score,
        priority=priority,
    )
    return JobCandidateMatchPage(items=items, meta=PageMeta(total=total, limit=limit, offset=offset))


@router.post("/matches", response_model=JobCandidateMatchRead, status_code=status.HTTP_201_CREATED)
def create_match(payload: JobCandidateMatchCreate, db: Session = Depends(get_db)) -> JobCandidateMatchRead:
    return crud.create_job_candidate_match(db, payload)


@router.get("/applications", response_model=ApplicationPage)
def list_applications(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="applied_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    candidate_id: int | None = Query(default=None),
    employee_id: int | None = Query(default=None),
) -> ApplicationPage:
    total, items = crud.list_applications(
        db,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        candidate_id=candidate_id,
        employee_id=employee_id,
    )
    return ApplicationPage(items=items, meta=PageMeta(total=total, limit=limit, offset=offset))


@router.post("/applications", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)) -> ApplicationRead:
    return crud.create_application(db, payload)


@router.get("/work-queues", response_model=EmployeeWorkQueuePage)
def list_work_queues(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="score"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    candidate_id: int | None = Query(default=None),
    employee_id: int | None = Query(default=None),
    priority: str | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
) -> EmployeeWorkQueuePage:
    total, items = crud.list_employee_work_queues(
        db,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        candidate_id=candidate_id,
        employee_id=employee_id,
        priority_bucket=priority,
        status=status_value,
    )
    return EmployeeWorkQueuePage(items=items, meta=PageMeta(total=total, limit=limit, offset=offset))


@router.post("/admin/run-daily-pipeline")
def run_daily_pipeline_endpoint(db: Session = Depends(get_db)) -> dict:
    summary = run_daily_pipeline(db)
    return {
        "status": "ok",
        "summary": {
            "raw_jobs_stored": summary.raw_jobs_stored,
            "sources_processed": summary.sources_processed,
            "source_failures": summary.source_failures,
            "jobs_skipped_irrelevant": summary.jobs_skipped_irrelevant,
            "normalized_jobs": summary.normalized_jobs,
            "duplicate_groups": summary.duplicate_groups,
            "scored_matches": summary.scored_matches,
            "work_queue_items": summary.work_queue_items,
        },
    }
