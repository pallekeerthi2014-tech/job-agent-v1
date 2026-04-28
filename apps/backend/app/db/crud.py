from __future__ import annotations

from datetime import date

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.candidate import Candidate, CandidatePreference, CandidateSkill
from app.models.employee import Employee
from app.models.job import JobNormalized, JobRaw
from app.models.match_score import JobCandidateMatch
from app.models.user import User
from app.models.work_queue import EmployeeWorkQueue
from app.schemas.application import ApplicationCreate
from app.schemas.candidate import CandidateCreate, CandidatePreferenceCreate, CandidateSkillCreate, CandidateUpdate
from app.schemas.employee import EmployeeCreate
from app.schemas.job import JobNormalizedCreate, JobRawCreate
from app.schemas.match import JobCandidateMatchCreate
from app.schemas.user import UserCreate, UserUpdate
from app.services.auth import hash_password


def create_candidate(db: Session, payload: CandidateCreate) -> Candidate:
    candidate = Candidate(**payload.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def get_candidate(db: Session, candidate_id: int) -> Candidate | None:
    return db.get(Candidate, candidate_id)


def update_candidate(db: Session, candidate_id: int, payload: CandidateUpdate) -> Candidate | None:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        return None

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(candidate, key, value)

    db.commit()
    db.refresh(candidate)
    return candidate


def delete_candidate(db: Session, candidate_id: int) -> bool:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        return False

    db.delete(candidate)
    db.commit()
    return True


def list_candidates(
    db: Session,
    *,
    limit: int,
    offset: int,
    sort_by: str,
    sort_order: str,
    candidate_id: int | None = None,
    employee_id: int | None = None,
) -> tuple[int, list[Candidate]]:
    stmt: Select = select(Candidate)
    if candidate_id is not None:
        stmt = stmt.where(Candidate.id == candidate_id)
    if employee_id is not None:
        stmt = stmt.where(Candidate.assigned_employee == employee_id)

    total = _count_rows(db, stmt)
    stmt = stmt.order_by(_sort_column(Candidate, sort_by, sort_order, default="id")).offset(offset).limit(limit)
    return total, list(db.scalars(stmt))


def upsert_candidate_preference(db: Session, payload: CandidatePreferenceCreate) -> CandidatePreference:
    preference = db.get(CandidatePreference, payload.candidate_id)
    values = payload.model_dump(exclude={"candidate_id"})

    if preference is None:
        preference = CandidatePreference(candidate_id=payload.candidate_id, **values)
        db.add(preference)
    else:
        for key, value in values.items():
            setattr(preference, key, value)

    db.commit()
    db.refresh(preference)
    return preference


def list_candidate_preferences(db: Session) -> list[CandidatePreference]:
    return list(db.scalars(select(CandidatePreference).order_by(CandidatePreference.candidate_id)))


def create_candidate_skill(db: Session, payload: CandidateSkillCreate) -> CandidateSkill:
    skill = CandidateSkill(**payload.model_dump())
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def list_candidate_skills(db: Session, candidate_id: int | None = None) -> list[CandidateSkill]:
    stmt = select(CandidateSkill).order_by(CandidateSkill.candidate_id, CandidateSkill.skill_name)
    if candidate_id is not None:
        stmt = stmt.where(CandidateSkill.candidate_id == candidate_id)
    return list(db.scalars(stmt))


def create_employee(db: Session, payload: EmployeeCreate) -> Employee:
    employee = Employee(**payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def list_employees(db: Session) -> list[Employee]:
    return list(db.scalars(select(Employee).order_by(Employee.id.desc())))


def get_employee(db: Session, employee_id: int) -> Employee | None:
    return db.get(Employee, employee_id)


def create_user(db: Session, payload: UserCreate) -> User:
    user = User(
        name=payload.name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
        employee_id=payload.employee_id,
        candidate_id=getattr(payload, "candidate_id", None),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.role.asc(), User.name.asc(), User.id.asc())))


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def update_user(db: Session, user_id: int, payload: UserUpdate) -> User | None:
    user = db.get(User, user_id)
    if user is None:
        return None

    values = payload.model_dump(exclude_unset=True)
    password = values.pop("password", None)
    for key, value in values.items():
        setattr(user, key, value)
    if password:
        user.password_hash = hash_password(password)

    db.commit()
    db.refresh(user)
    return user


def create_job_raw(db: Session, payload: JobRawCreate) -> JobRaw:
    job = JobRaw(**payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_jobs_raw(db: Session) -> list[JobRaw]:
    return list(db.scalars(select(JobRaw).order_by(JobRaw.fetched_at.desc())))


def create_job_normalized(db: Session, payload: JobNormalizedCreate) -> JobNormalized:
    job = JobNormalized(**payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_jobs_normalized(
    db: Session,
    *,
    limit: int,
    offset: int,
    sort_by: str,
    sort_order: str,
    source: str | None = None,
    posted_date: date | None = None,
    freshness_status: str | None = None,
) -> tuple[int, list[JobNormalized]]:
    stmt: Select = select(JobNormalized)
    if source is not None:
        stmt = stmt.where(JobNormalized.source == source)
    if posted_date is not None:
        stmt = stmt.where(JobNormalized.posted_date == posted_date)
    if freshness_status is not None:
        stmt = stmt.where(JobNormalized.freshness_status == freshness_status)

    total = _count_rows(db, stmt)
    stmt = stmt.order_by(
        _sort_column(JobNormalized, sort_by, sort_order, default="posted_date", nullslast=True),
        _sort_column(JobNormalized, "id", "desc", default="id"),
    ).offset(offset).limit(limit)
    return total, list(db.scalars(stmt))


def create_job_candidate_match(db: Session, payload: JobCandidateMatchCreate) -> JobCandidateMatch:
    match = JobCandidateMatch(**payload.model_dump())
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


def list_job_candidate_matches(
    db: Session,
    *,
    limit: int,
    offset: int,
    sort_by: str,
    sort_order: str,
    candidate_id: int | None = None,
    employee_id: int | None = None,
    min_score: float | None = None,
    priority: int | None = None,
) -> tuple[int, list[JobCandidateMatch]]:
    stmt: Select = select(JobCandidateMatch)
    if candidate_id is not None:
        stmt = stmt.where(JobCandidateMatch.candidate_id == candidate_id)
    if min_score is not None:
        stmt = stmt.where(JobCandidateMatch.score >= min_score)
    if priority is not None:
        stmt = stmt.where(JobCandidateMatch.priority == priority)
    if employee_id is not None:
        stmt = stmt.join(Candidate, Candidate.id == JobCandidateMatch.candidate_id).where(Candidate.assigned_employee == employee_id)

    total = _count_rows(db, stmt)
    stmt = stmt.order_by(_sort_column(JobCandidateMatch, sort_by, sort_order, default="score")).offset(offset).limit(limit)
    return total, list(db.scalars(stmt))


def create_application(db: Session, payload: ApplicationCreate) -> Application:
    application = Application(**payload.model_dump(exclude_none=True))
    db.add(application)
    queue_stmt: Select = select(EmployeeWorkQueue).where(
        EmployeeWorkQueue.candidate_id == payload.candidate_id,
        EmployeeWorkQueue.job_id == payload.job_id,
    )
    if payload.employee_id is not None:
        queue_stmt = queue_stmt.where(EmployeeWorkQueue.employee_id == payload.employee_id)

    queue_items = list(db.scalars(queue_stmt))
    queue_status = payload.status or "applied"
    for queue_item in queue_items:
        queue_item.status = queue_status

    db.commit()
    db.refresh(application)
    return application


def list_applications(
    db: Session,
    *,
    limit: int,
    offset: int,
    sort_by: str,
    sort_order: str,
    candidate_id: int | None = None,
    employee_id: int | None = None,
) -> tuple[int, list[Application]]:
    stmt: Select = select(Application)
    if candidate_id is not None:
        stmt = stmt.where(Application.candidate_id == candidate_id)
    if employee_id is not None:
        stmt = stmt.where(Application.employee_id == employee_id)

    total = _count_rows(db, stmt)
    stmt = stmt.order_by(_sort_column(Application, sort_by, sort_order, default="applied_at")).offset(offset).limit(limit)
    return total, list(db.scalars(stmt))


def list_employee_work_queues(
    db: Session,
    *,
    limit: int,
    offset: int,
    sort_by: str,
    sort_order: str,
    candidate_id: int | None = None,
    employee_id: int | None = None,
    priority_bucket: str | None = None,
    status: str | None = None,
) -> tuple[int, list[EmployeeWorkQueue]]:
    stmt: Select = select(EmployeeWorkQueue)
    if candidate_id is not None:
        stmt = stmt.where(EmployeeWorkQueue.candidate_id == candidate_id)
    if employee_id is not None:
        stmt = stmt.where(EmployeeWorkQueue.employee_id == employee_id)
    if priority_bucket is not None:
        stmt = stmt.where(EmployeeWorkQueue.priority_bucket == priority_bucket)
    if status is not None:
        stmt = stmt.where(EmployeeWorkQueue.status == status)

    total = _count_rows(db, stmt)
    stmt = stmt.order_by(_sort_column(EmployeeWorkQueue, sort_by, sort_order, default="score")).offset(offset).limit(limit)
    return total, list(db.scalars(stmt))


def _count_rows(db: Session, stmt: Select) -> int:
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    return int(db.scalar(count_stmt) or 0)


def _sort_column(model: type, sort_by: str, sort_order: str, *, default: str, nullslast: bool = False):
    column_name = sort_by if hasattr(model, sort_by) else default
    column = getattr(model, column_name)
    ordered = asc(column) if sort_order == "asc" else desc(column)
    return ordered.nullslast() if nullslast else ordered
