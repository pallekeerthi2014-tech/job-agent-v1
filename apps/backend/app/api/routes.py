from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_authenticated_user, require_super_admin
from app.db import crud
from app.models.candidate import Candidate
from app.models.employee import Employee
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationPage, ApplicationRead
from app.schemas.candidate import (
    CandidateCreate,
    CandidatePage,
    CandidatePreferenceCreate,
    CandidatePreferenceRead,
    CandidatePreferenceUpsert,
    CandidateRead,
    CandidateSkillCreate,
    CandidateSkillRead,
    CandidateUpdate,
)
from app.schemas.employee import EmployeeCreate, EmployeeRead
from app.schemas.job import JobNormalizedCreate, JobNormalizedPage, JobNormalizedRead, JobRawCreate, JobRawRead
from app.schemas.match import JobCandidateMatchCreate, JobCandidateMatchPage, JobCandidateMatchRead
from app.schemas.pagination import PageMeta
from app.schemas.user import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    TokenResponse,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.schemas.work_queue import EmployeeWorkQueuePage
from app.services.auth import (
    authenticate_user,
    build_password_reset,
    create_access_token,
    get_user_by_email,
    reset_password_with_token,
)
from app.services.emailer import send_password_reset_email, smtp_enabled
from app.services.pipeline import run_daily_pipeline

router = APIRouter(prefix="/api/v1")


def _scoped_employee_id(current_user: User, requested_employee_id: int | None) -> int | None:
    if current_user.role == "super_admin":
        return requested_employee_id
    if current_user.employee_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Employee account is not linked")
    if requested_employee_id is not None and requested_employee_id != current_user.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another employee's records")
    return current_user.employee_id


def _get_candidate_or_404(db: Session, candidate_id: int) -> Candidate:
    candidate = crud.get_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


def _ensure_candidate_access(current_user: User, candidate: Candidate) -> None:
    if current_user.role == "super_admin":
        return
    if current_user.employee_id is None or candidate.assigned_employee != current_user.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access this candidate")


def _build_user_create_payload(db: Session, payload: UserCreate) -> UserCreate:
    if get_user_by_email(db, payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists")

    employee_id = payload.employee_id
    if payload.role == "employee":
        if employee_id is None:
            employee = crud.create_employee(db, EmployeeCreate(name=payload.name, email=payload.email))
            employee_id = employee.id
        elif crud.get_employee(db, employee_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    else:
        employee_id = None

    return UserCreate(
        name=payload.name,
        email=payload.email,
        password=payload.password,
        role=payload.role,
        is_active=payload.is_active,
        employee_id=employee_id,
    )


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(user), user=user)


@router.get("/auth/me", response_model=UserRead)
def get_me(current_user: User = Depends(require_authenticated_user)) -> UserRead:
    return current_user


@router.post("/auth/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> ForgotPasswordResponse:
    user = get_user_by_email(db, payload.email)
    if user is None or not user.is_active:
        return ForgotPasswordResponse(
            message="If an active account exists for this email, a reset link has been prepared.",
            delivery="preview",
        )

    reset_token, reset_url = build_password_reset(db, user)
    if smtp_enabled():
        send_password_reset_email(recipient_email=user.email, recipient_name=user.name, reset_url=reset_url)
        return ForgotPasswordResponse(
            message="Password reset email sent.",
            delivery="email",
            reset_url=reset_url,
        )

    return ForgotPasswordResponse(
        message="SMTP is not configured, so a reset preview token is returned for local development.",
        delivery="preview",
        reset_token=reset_token,
        reset_url=reset_url,
    )


@router.post("/auth/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    user = reset_password_with_token(db, payload.token, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    return MessageResponse(message="Password updated successfully.")


@router.get("/admin/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> list[UserRead]:
    return crud.list_users(db)


@router.post("/admin/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> UserRead:
    return crud.create_user(db, _build_user_create_payload(db, payload))


@router.put("/admin/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> UserRead:
    user = crud.update_user(db, user_id, payload)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/candidates", response_model=CandidatePage)
def list_candidates(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="id"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    candidate_id: int | None = Query(default=None),
    employee_id: int | None = Query(default=None),
    current_user: User = Depends(require_authenticated_user),
) -> CandidatePage:
    scoped_employee_id = _scoped_employee_id(current_user, employee_id)
    if candidate_id is not None and current_user.role != "super_admin":
        candidate = _get_candidate_or_404(db, candidate_id)
        _ensure_candidate_access(current_user, candidate)
    total, items = crud.list_candidates(
        db,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        candidate_id=candidate_id,
        employee_id=scoped_employee_id,
    )
    return CandidatePage(items=items, meta=PageMeta(total=total, limit=limit, offset=offset))


@router.post("/candidates", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate(
    payload: CandidateCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> CandidateRead:
    return crud.create_candidate(db, payload)


@router.get("/candidates/{candidate_id}", response_model=CandidateRead)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
) -> CandidateRead:
    candidate = _get_candidate_or_404(db, candidate_id)
    _ensure_candidate_access(current_user, candidate)
    return candidate


@router.put("/candidates/{candidate_id}", response_model=CandidateRead)
def update_candidate(
    candidate_id: int,
    payload: CandidateUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> CandidateRead:
    candidate = crud.update_candidate(db, candidate_id, payload)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


@router.delete("/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> Response:
    deleted = crud.delete_candidate(db, candidate_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/candidate-preferences", response_model=list[CandidatePreferenceRead])
def list_candidate_preferences(
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> list[CandidatePreferenceRead]:
    return crud.list_candidate_preferences(db)


@router.put("/candidate-preferences/{candidate_id}", response_model=CandidatePreferenceRead)
def upsert_candidate_preference(
    candidate_id: int,
    payload: CandidatePreferenceUpsert,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> CandidatePreferenceRead:
    return crud.upsert_candidate_preference(
        db,
        CandidatePreferenceCreate(candidate_id=candidate_id, **payload.model_dump()),
    )


@router.get("/candidate-skills", response_model=list[CandidateSkillRead])
def list_candidate_skills(
    candidate_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> list[CandidateSkillRead]:
    return crud.list_candidate_skills(db, candidate_id=candidate_id)


@router.post("/candidate-skills", response_model=CandidateSkillRead, status_code=status.HTTP_201_CREATED)
def create_candidate_skill(
    payload: CandidateSkillCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> CandidateSkillRead:
    return crud.create_candidate_skill(db, payload)


@router.get("/employees", response_model=list[EmployeeRead])
def list_employees(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
) -> list[EmployeeRead]:
    if current_user.role == "super_admin":
        return crud.list_employees(db)
    if current_user.employee_id is None:
        return []
    employee = crud.get_employee(db, current_user.employee_id)
    return [employee] if employee else []


@router.post("/employees", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> EmployeeRead:
    return crud.create_employee(db, payload)


@router.get("/jobs/raw", response_model=list[JobRawRead])
def list_jobs_raw(
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> list[JobRawRead]:
    return crud.list_jobs_raw(db)


@router.post("/jobs/raw", response_model=JobRawRead, status_code=status.HTTP_201_CREATED)
def create_job_raw(
    payload: JobRawCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> JobRawRead:
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
    _: User = Depends(require_authenticated_user),
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
def create_job_normalized(
    payload: JobNormalizedCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> JobNormalizedRead:
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
    current_user: User = Depends(require_authenticated_user),
) -> JobCandidateMatchPage:
    scoped_employee_id = _scoped_employee_id(current_user, employee_id)
    if candidate_id is not None and current_user.role != "super_admin":
        candidate = _get_candidate_or_404(db, candidate_id)
        _ensure_candidate_access(current_user, candidate)
    total, items = crud.list_job_candidate_matches(
        db,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        candidate_id=candidate_id,
        employee_id=scoped_employee_id,
        min_score=score,
        priority=priority,
    )
    return JobCandidateMatchPage(items=items, meta=PageMeta(total=total, limit=limit, offset=offset))


@router.post("/matches", response_model=JobCandidateMatchRead, status_code=status.HTTP_201_CREATED)
def create_match(
    payload: JobCandidateMatchCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> JobCandidateMatchRead:
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
    current_user: User = Depends(require_authenticated_user),
) -> ApplicationPage:
    scoped_employee_id = _scoped_employee_id(current_user, employee_id)
    if candidate_id is not None and current_user.role != "super_admin":
        candidate = _get_candidate_or_404(db, candidate_id)
        _ensure_candidate_access(current_user, candidate)
    total, items = crud.list_applications(
        db,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        candidate_id=candidate_id,
        employee_id=scoped_employee_id,
    )
    return ApplicationPage(items=items, meta=PageMeta(total=total, limit=limit, offset=offset))


@router.post("/applications", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
) -> ApplicationRead:
    candidate = _get_candidate_or_404(db, payload.candidate_id)
    _ensure_candidate_access(current_user, candidate)

    employee_id = payload.employee_id
    if current_user.role != "super_admin":
        if current_user.employee_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Employee account is not linked")
        if employee_id is not None and employee_id != current_user.employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot apply on behalf of another employee")
        employee_id = current_user.employee_id

    return crud.create_application(
        db,
        ApplicationCreate(
            candidate_id=payload.candidate_id,
            job_id=payload.job_id,
            employee_id=employee_id,
            status=payload.status,
            notes=payload.notes,
        ),
    )


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
    current_user: User = Depends(require_authenticated_user),
) -> EmployeeWorkQueuePage:
    scoped_employee_id = _scoped_employee_id(current_user, employee_id)
    if candidate_id is not None and current_user.role != "super_admin":
        candidate = _get_candidate_or_404(db, candidate_id)
        _ensure_candidate_access(current_user, candidate)
    total, items = crud.list_employee_work_queues(
        db,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        candidate_id=candidate_id,
        employee_id=scoped_employee_id,
        priority_bucket=priority,
        status=status_value,
    )
    return EmployeeWorkQueuePage(items=items, meta=PageMeta(total=total, limit=limit, offset=offset))


@router.post("/admin/run-daily-pipeline")
def run_daily_pipeline_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> dict:
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
