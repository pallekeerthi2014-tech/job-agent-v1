from __future__ import annotations

import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_authenticated_user, require_super_admin, require_candidate_user
from app.db import crud
from app.models.alert_recipient import AlertRecipient
from app.models.candidate import Candidate
from app.models.employee import Employee
from app.models.job import JobNormalized
from app.models.match_score import JobCandidateMatch
from app.models.user import User
from app.models.work_queue import EmployeeWorkQueue
from app.schemas.alert_recipient import AlertRecipientCreate, AlertRecipientRead, AlertRecipientUpdate
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
    CandidateProfileUpdate,
    CandidateSelfRegister,
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
from app.schemas.work_queue import EmployeeWorkQueuePage, WorkQueueReportPayload
from app.services.auth import (
    authenticate_user,
    build_password_reset,
    create_access_token,
    get_user_by_email,
    reset_password_with_token,
)
from app.services.emailer import send_password_reset_email, smtp_enabled
from app.services.pipeline import run_daily_pipeline

# Resume storage directory Ã¢ÂÂ mounted as a Docker volume in production
_RESUME_DIR = Path(os.getenv("RESUME_STORAGE_PATH", "/app/resumes"))

from app.schemas.source import (
    AdapterTypeList, SourceCreate, SourceRead, SourceRunResult,
    SourceTestRequest, SourceTestResult, SourceUpdate,
)
from app.services.source_management import (
    create_source as svc_create_source,
    delete_source as svc_delete_source,
    get_source as svc_get_source,
    list_sources as svc_list_sources,
    run_source_now as svc_run_source_now,
    source_stats as svc_source_stats,
    test_source_config as svc_test_source_config,
    update_source as svc_update_source,
)
from app.services.source_adapters.form_schemas import get_adapter_form_schemas

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


# Ã¢ÂÂÃ¢ÂÂ Employee CRUD (admin) Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

@router.put("/admin/employees/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> EmployeeRead:
    employee = db.scalar(select(Employee).where(Employee.id == employee_id))
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    employee.name = payload.name
    employee.email = payload.email
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/admin/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> Response:
    employee = db.scalar(select(Employee).where(Employee.id == employee_id))
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.delete(employee)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Ã¢ÂÂÃ¢ÂÂ WhatsApp Alert Recipients Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

@router.get("/admin/whatsapp-recipients", response_model=list[AlertRecipientRead])
def list_whatsapp_recipients(
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> list[AlertRecipientRead]:
    return list(db.scalars(select(AlertRecipient).order_by(AlertRecipient.id.asc())))


@router.post("/admin/whatsapp-recipients", response_model=AlertRecipientRead, status_code=status.HTTP_201_CREATED)
def create_whatsapp_recipient(
    payload: AlertRecipientCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> AlertRecipientRead:
    # Normalise to E.164 with whatsapp: prefix stripped for storage
    number = payload.phone_number.strip()
    if number.startswith("whatsapp:"):
        number = number[len("whatsapp:"):]
    existing = db.scalar(select(AlertRecipient).where(AlertRecipient.phone_number == number))
    if existing:
        raise HTTPException(status_code=409, detail="Phone number already registered")
    recipient = AlertRecipient(phone_number=number, label=payload.label, is_active=payload.is_active)
    db.add(recipient)
    db.commit()
    db.refresh(recipient)
    return recipient


@router.put("/admin/whatsapp-recipients/{recipient_id}", response_model=AlertRecipientRead)
def update_whatsapp_recipient(
    recipient_id: int,
    payload: AlertRecipientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> AlertRecipientRead:
    recipient = db.scalar(select(AlertRecipient).where(AlertRecipient.id == recipient_id))
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    if payload.label is not None:
        recipient.label = payload.label
    if payload.is_active is not None:
        recipient.is_active = payload.is_active
    db.commit()
    db.refresh(recipient)
    return recipient


@router.delete("/admin/whatsapp-recipients/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_whatsapp_recipient(
    recipient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> Response:
    recipient = db.scalar(select(AlertRecipient).where(AlertRecipient.id == recipient_id))
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    db.delete(recipient)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Ã¢ÂÂÃ¢ÂÂ Candidate resume upload Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

@router.post("/candidates/{candidate_id}/resume", response_model=CandidateRead)
async def upload_resume(
    candidate_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> CandidateRead:
    candidate = db.scalar(select(Candidate).where(Candidate.id == candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    allowed = {".pdf", ".doc", ".docx", ".txt"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}. Allowed: {allowed}")

    _RESUME_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"candidate_{candidate_id}{suffix}"
    dest = _RESUME_DIR / safe_name

    content = await file.read()
    dest.write_bytes(content)

    # Extract plain text for scoring
    resume_text: str | None = None
    try:
        if suffix == ".pdf":
            import pypdf  # type: ignore
            import io
            reader = pypdf.PdfReader(io.BytesIO(content))
            resume_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif suffix in {".doc", ".docx"}:
            import mammoth  # type: ignore
            result = mammoth.extract_raw_text({"bytes": content})
            resume_text = result.value
        else:
            resume_text = content.decode("utf-8", errors="ignore")
    except Exception:
        resume_text = None  # Store file even if text extraction fails

    candidate.resume_filename = safe_name
    candidate.resume_text = (resume_text or "").strip() or None
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("/candidates/{candidate_id}/resume")
def download_resume(
    candidate_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated_user),
) -> Response:
    from fastapi.responses import FileResponse
    candidate = db.scalar(select(Candidate).where(Candidate.id == candidate_id))
    if not candidate or not candidate.resume_filename:
        raise HTTPException(status_code=404, detail="No resume on file for this candidate")
    path = _RESUME_DIR / candidate.resume_filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Resume file not found on disk")
    return FileResponse(str(path), filename=candidate.resume_filename)


# Ã¢ÂÂÃ¢ÂÂ Work queue: report a job as invalid/outdated/not-relevant Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

@router.post("/work-queues/{queue_id}/report", response_model=dict)
def report_work_queue_item(
    queue_id: int,
    payload: WorkQueueReportPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
) -> dict:
    allowed_statuses = {"invalid", "outdated", "not_relevant"}
    if payload.report_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"report_status must be one of {allowed_statuses}")

    item = db.scalar(select(EmployeeWorkQueue).where(EmployeeWorkQueue.id == queue_id))
    if not item:
        raise HTTPException(status_code=404, detail="Work queue item not found")

    # Employees can only report their own items
    if current_user.role != "super_admin" and item.employee_id != current_user.employee_id:
        raise HTTPException(status_code=403, detail="Access denied")

    item.report_status = payload.report_status
    item.report_reason = payload.report_reason
    item.reported_at = datetime.now(timezone.utc)
    item.status = "skipped"
    db.commit()
    return {"status": "ok", "report_status": item.report_status}


# Ã¢ÂÂÃ¢ÂÂ Analytics Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

@router.get("/analytics/overview")
def analytics_overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> dict[str, Any]:
    # Jobs by source
    jobs_by_source = [
        {"source": src, "count": cnt}
        for src, cnt in db.execute(
            select(JobNormalized.source, func.count().label("cnt"))
            .where(JobNormalized.is_active.is_(True))
            .group_by(JobNormalized.source)
            .order_by(func.count().desc())
        ).all()
    ]

    # Freshness breakdown
    freshness_rows = db.execute(
        select(JobNormalized.freshness_status, func.count().label("cnt"))
        .group_by(JobNormalized.freshness_status)
    ).all()
    freshness = {row.freshness_status: row.cnt for row in freshness_rows}

    # Application funnel
    total_queue = db.scalar(select(func.count()).select_from(EmployeeWorkQueue)) or 0
    applied = db.scalar(select(func.count()).select_from(EmployeeWorkQueue).where(EmployeeWorkQueue.status == "applied")) or 0
    skipped = db.scalar(select(func.count()).select_from(EmployeeWorkQueue).where(EmployeeWorkQueue.status == "skipped")) or 0
    pending = db.scalar(select(func.count()).select_from(EmployeeWorkQueue).where(EmployeeWorkQueue.status == "pending")) or 0

    # Reported job issues by source
    reported_rows = db.execute(
        select(JobNormalized.source, EmployeeWorkQueue.report_status, func.count().label("cnt"))
        .join(JobNormalized, EmployeeWorkQueue.job_id == JobNormalized.id)
        .where(EmployeeWorkQueue.report_status.isnot(None))
        .group_by(JobNormalized.source, EmployeeWorkQueue.report_status)
        .order_by(func.count().desc())
    ).all()
    reports_by_source = [
        {"source": row.source, "report_status": row.report_status, "count": row.cnt}
        for row in reported_rows
    ]

    # Top match scores by candidate
    top_matches = db.execute(
        select(Candidate.name, func.max(JobCandidateMatch.score).label("top_score"), func.count().label("match_count"))
        .join(JobCandidateMatch, JobCandidateMatch.candidate_id == Candidate.id)
        .group_by(Candidate.id, Candidate.name)
        .order_by(func.max(JobCandidateMatch.score).desc())
        .limit(10)
    ).all()
    candidate_stats = [
        {"name": row.name, "top_score": round(row.top_score, 1), "match_count": row.match_count}
        for row in top_matches
    ]

    # Source quality: jobs applied vs reported
    source_quality = db.execute(
        select(
            JobNormalized.source,
            func.count().label("total"),
            func.sum(
                func.cast(EmployeeWorkQueue.status == "applied", db.bind.dialect.name == "sqlite" and "INTEGER" or "INT")
            ).label("applied_count"),
        )
        .join(JobNormalized, EmployeeWorkQueue.job_id == JobNormalized.id)
        .group_by(JobNormalized.source)
        .order_by(func.count().desc())
    ).all()

    return {
        "jobs_by_source": jobs_by_source,
        "freshness": freshness,
        "funnel": {
            "total": total_queue,
            "pending": pending,
            "applied": applied,
            "skipped": skipped,
            "apply_rate_pct": round(applied / total_queue * 100, 1) if total_queue else 0,
        },
        "reports_by_source": reports_by_source,
        "top_candidates": candidate_stats,
    }


# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
# Candidate Self-Service Portal
# Routes prefixed /api/v1/portal/... Ã¢ÂÂ accessible only to role="candidate" users
# Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ

@router.post("/portal/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def candidate_register(payload: CandidateSelfRegister, db: Session = Depends(get_db)) -> TokenResponse:
    """Self-registration: creates a Candidate record + linked User (role=candidate) in one shot."""
    from app.services.auth import get_user_by_email

    if get_user_by_email(db, payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    # Create the Candidate profile
    candidate = Candidate(
        name=payload.name,
        email=payload.email.lower(),
        phone=payload.phone,
        location=payload.location,
        work_authorization=payload.work_authorization,
        years_experience=payload.years_experience,
        active=True,
    )
    db.add(candidate)
    db.flush()  # get candidate.id without committing

    # Create the User login linked to this candidate
    from app.services.auth import hash_password
    user = User(
        name=payload.name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role="candidate",
        is_active=True,
        candidate_id=candidate.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(user), user=user)


@router.get("/portal/me", response_model=CandidateRead)
def portal_get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_candidate_user),
) -> CandidateRead:
    """Return the authenticated candidate's own profile."""
    candidate = db.get(Candidate, current_user.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate profile not found")
    return candidate


@router.patch("/portal/me", response_model=CandidateRead)
def portal_update_profile(
    payload: CandidateProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_candidate_user),
) -> CandidateRead:
    """Candidate updates their own profile fields (not name or email Ã¢ÂÂ admin controls those)."""
    candidate = db.get(Candidate, current_user.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate profile not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(candidate, key, value)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("/portal/matches", response_model=JobCandidateMatchPage)
def portal_list_matches(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_candidate_user),
) -> JobCandidateMatchPage:
    """Return the candidate's own job matches sorted by score descending."""
    total, items = crud.list_job_candidate_matches(
        db,
        limit=limit,
        offset=offset,
        sort_by="score",
        sort_order="desc",
        candidate_id=current_user.candidate_id,
    )
    return JobCandidateMatchPage(items=items, meta=PageMeta(total=total, limit=limit, offset=offset))


@router.get("/portal/jobs/{job_id}", response_model=JobNormalizedRead)
def portal_get_job(
    job_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_candidate_user),
) -> JobNormalizedRead:
    """Fetch a single job for the candidate portal detail view."""
    job = db.get(JobNormalized, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("/portal/me/resume", response_model=CandidateRead)
async def portal_upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_candidate_user),
) -> CandidateRead:
    """Candidate uploads their own resume Ã¢ÂÂ same extraction logic as admin route."""
    candidate = db.get(Candidate, current_user.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate profile not found")

    allowed = {".pdf", ".doc", ".docx", ".txt"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}. Allowed: {allowed}")

    _RESUME_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"candidate_{candidate.id}{suffix}"
    dest = _RESUME_DIR / safe_name
    content = await file.read()
    dest.write_bytes(content)

    resume_text: str | None = None
    try:
        if suffix == ".pdf":
            import pypdf  # type: ignore
            import io as _io
            reader = pypdf.PdfReader(_io.BytesIO(content))
            resume_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif suffix in {".doc", ".docx"}:
            import mammoth  # type: ignore
            result = mammoth.extract_raw_text({"bytes": content})
            resume_text = result.value
        else:
            resume_text = content.decode("utf-8", errors="ignore")
    except Exception:
        resume_text = None

    candidate.resume_filename = safe_name
    candidate.resume_text = (resume_text or "").strip() or None
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("/portal/me/resume")
def portal_download_resume(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_candidate_user),
) -> Response:
    """Download the authenticated candidate's own resume file."""
    from fastapi.responses import FileResponse
    candidate = db.get(Candidate, current_user.candidate_id)
    if candidate is None or not candidate.resume_filename:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No resume on file")
    path = _RESUME_DIR / candidate.resume_filename
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume file not found on disk")
    return FileResponse(str(path), filename=candidate.resume_filename)


# Phase 1: Source / Feed Management

@router.get("/admin/source-types", response_model=AdapterTypeList)
def get_source_types(
    _current_user: User = Depends(require_super_admin),
):
    return AdapterTypeList(adapter_types=get_adapter_form_schemas())


@router.get("/admin/sources", response_model=list[SourceRead])
def list_sources_endpoint(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
):
    stats = svc_source_stats(db)
    sources = svc_list_sources(db)
    result = []
    for src in sources:
        s = SourceRead.model_validate(src)
        row = stats.get(src.name, {})
        s.jobs_total = row.get("total", 0)
        s.jobs_last_24h = row.get("last_24h", 0)
        s.jobs_last_7d = row.get("last_7d", 0)
        result.append(s)
    return result


@router.get("/admin/sources/{source_id}", response_model=SourceRead)
def get_source_endpoint(
    source_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
):
    src = svc_get_source(db, source_id)
    if src is None:
        raise HTTPException(status_code=404, detail="Source not found")
    stats = svc_source_stats(db)
    s = SourceRead.model_validate(src)
    row = stats.get(src.name, {})
    s.jobs_total = row.get("total", 0)
    s.jobs_last_24h = row.get("last_24h", 0)
    s.jobs_last_7d = row.get("last_7d", 0)
    return s


@router.post("/admin/sources", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source_endpoint(
    payload: SourceCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
):
    try:
        src = svc_create_source(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return SourceRead.model_validate(src)


@router.put("/admin/sources/{source_id}", response_model=SourceRead)
def update_source_endpoint(
    source_id: int,
    payload: SourceUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
):
    try:
        src = svc_update_source(db, source_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if src is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return SourceRead.model_validate(src)


@router.delete("/admin/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source_endpoint(
    source_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
):
    deleted = svc_delete_source(db, source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Source not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/admin/sources/test", response_model=SourceTestResult)
def test_source_config_endpoint(
    payload: SourceTestRequest,
    _current_user: User = Depends(require_super_admin),
):
    return svc_test_source_config(
        adapter_type=payload.adapter_type,
        config=payload.config,
        sample_size=payload.sample_size or 3,
    )


@router.post("/admin/sources/{source_id}/test", response_model=SourceTestResult)
def test_existing_source_endpoint(
    source_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
):
    src = svc_get_source(db, source_id)
    if src is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return svc_test_source_config(
        adapter_type=src.adapter_type,
        config=src.config or {},
        sample_size=3,
    )


@router.post("/admin/sources/{source_id}/run-now", response_model=SourceRunResult)
def run_source_now_endpoint(
    source_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
):
    try:
        return svc_run_source_now(db, source_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
