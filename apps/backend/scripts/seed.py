from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.db.crud import (
    create_candidate,
    create_candidate_skill,
    create_employee,
    create_user,
    upsert_candidate_preference,
)
from app.db.session import SessionLocal
from app.models.candidate import Candidate
from app.models.employee import Employee
from app.models.source import JobSource
from app.models.user import User
from app.schemas.candidate import CandidateCreate, CandidatePreferenceCreate, CandidateSkillCreate
from app.schemas.employee import EmployeeCreate
from app.schemas.user import UserCreate

DEFAULT_SEED_DIR = Path("/app/seed-data")
BASE_DIR = Path(__file__).resolve().parents[1]
SEED_DIR = DEFAULT_SEED_DIR if DEFAULT_SEED_DIR.exists() else BASE_DIR.parent.parent / "seed-data"

LEGACY_EMPLOYEE_EMAILS = {
    "olivia@example.com",
    "marcus@example.com",
    "olivia.chen@jobagent.example",
    "marcus.patel@jobagent.example",
    "sofia.ramirez@jobagent.example",
}
LEGACY_EMPLOYEE_NAMES = {"Olivia Chen", "Marcus Patel", "Sofia Ramirez"}
LEGACY_CANDIDATE_NAMES = {
    "Ariana Brooks",
    "Devika Nair",
    "Miguel Santos",
    "Priya Deshmukh",
    "Jonathan Reed",
    "Sarah Kim",
    "Nikhil Arora",
    "Lisa Tran",
    "Omar Haddad",
    "Emily Walker",
}


def load_json(name: str) -> list[dict]:
    with (SEED_DIR / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def cleanup_legacy_demo_data() -> None:
    db = SessionLocal()
    try:
        legacy_candidates = list(db.scalars(select(Candidate).where(Candidate.name.in_(LEGACY_CANDIDATE_NAMES))))
        for candidate in legacy_candidates:
            db.delete(candidate)
        db.flush()

        legacy_users = list(db.scalars(select(User).where(User.email.in_(LEGACY_EMPLOYEE_EMAILS))))
        for user in legacy_users:
            db.delete(user)
        db.flush()

        legacy_employees = list(db.scalars(select(Employee).where(Employee.name.in_(LEGACY_EMPLOYEE_NAMES))))
        for employee in legacy_employees:
            db.delete(employee)

        db.commit()
    finally:
        db.close()


def seed_employees() -> dict[str, int]:
    employee_records = load_json("employees.json")
    db = SessionLocal()
    employee_ids: dict[str, int] = {}

    try:
        existing_by_name = {employee.name: employee for employee in db.scalars(select(Employee).order_by(Employee.id.asc()))}

        for payload in employee_records:
            employee = existing_by_name.get(payload["name"])
            if employee is None:
                employee = create_employee(db, EmployeeCreate(**payload))
            else:
                employee.email = payload["email"]
                db.commit()
                db.refresh(employee)
            employee_ids[employee.name] = employee.id
    finally:
        db.close()

    return employee_ids


def seed_job_sources() -> None:
    source_records = load_json("job_sources.json")
    db = SessionLocal()
    try:
        existing_by_name = {source.name: source for source in db.scalars(select(JobSource).order_by(JobSource.id.asc()))}

        for payload in source_records:
            name = payload["name"]
            values = {
                "adapter_type": payload["adapter_type"],
                "config": payload.get("config", {}),
                "enabled": payload.get("enabled", True),
            }

            if name in existing_by_name:
                source = existing_by_name[name]
                for key, value in values.items():
                    setattr(source, key, value)
            else:
                db.add(JobSource(name=name, **values))

        db.commit()
    finally:
        db.close()


def seed_sample_candidates() -> None:
    if not settings.seed_sample_candidates:
        return

    db = SessionLocal()
    try:
        if db.scalar(select(Candidate.id).limit(1)):
            return
    finally:
        db.close()

    employee_ids = seed_employees()
    candidate_records = load_json("healthcare_business_analyst_candidates.json")

    db = SessionLocal()
    try:
        for payload in candidate_records:
            candidate = create_candidate(
                db,
                CandidateCreate(
                    name=payload["name"],
                    assigned_employee=employee_ids.get(payload["assigned_employee_name"]),
                    work_authorization=payload["work_authorization"],
                    years_experience=payload["years_experience"],
                    salary_min=payload["salary_min"],
                    salary_unit=payload["salary_unit"],
                    active=payload["active"],
                ),
            )

            upsert_candidate_preference(
                db,
                CandidatePreferenceCreate(
                    candidate_id=candidate.id,
                    preferred_titles=payload["preferred_titles"],
                    employment_preferences=payload["employment_preferences"],
                    location_preferences=payload["location_preferences"],
                    domain_expertise=payload["healthcare_domain_expertise"],
                    must_have_keywords=payload["must_have_keywords"],
                    exclude_keywords=payload["exclude_keywords"],
                ),
            )

            for skill in payload["skills"]:
                create_candidate_skill(
                    db,
                    CandidateSkillCreate(
                        candidate_id=candidate.id,
                        skill_name=skill["skill_name"],
                        years_used=skill.get("years_used"),
                    ),
                )
    finally:
        db.close()


def seed_users() -> None:
    db = SessionLocal()
    try:
        existing_users = {user.email: user for user in db.scalars(select(User).order_by(User.id.asc()))}

        if settings.super_admin_email not in existing_users:
            create_user(
                db,
                UserCreate(
                    name=settings.super_admin_name,
                    email=settings.super_admin_email,
                    password=settings.super_admin_password,
                    role="super_admin",
                    is_active=True,
                    employee_id=None,
                ),
            )

        employees = list(db.scalars(select(Employee).order_by(Employee.id.asc())))
        existing_emails = {user.email for user in db.scalars(select(User).order_by(User.id.asc()))}
        for employee in employees:
            normalized_email = employee.email.lower()
            if normalized_email in existing_emails:
                continue
            create_user(
                db,
                UserCreate(
                    name=employee.name,
                    email=employee.email,
                    password=settings.employee_default_password,
                    role="employee",
                    is_active=True,
                    employee_id=employee.id,
                ),
            )
            existing_emails.add(normalized_email)
    finally:
        db.close()


if __name__ == "__main__":
    # Seed admin user FIRST so login works even if other seed steps fail
    # (e.g. missing seed-data files in the container build context).
    _steps = [
        ("seed_users", seed_users),
        ("cleanup_legacy_demo_data", cleanup_legacy_demo_data),
        ("seed_job_sources", seed_job_sources),
        ("seed_employees", seed_employees),
        ("seed_sample_candidates", seed_sample_candidates),
    ]
    for _name, _fn in _steps:
        try:
            _fn()
            print(f"[seed] {_name}: ok")
        except Exception as _exc:
            print(f"[seed] {_name}: FAILED — {_exc}")
    print("Seed run complete (errors logged above if any)")
