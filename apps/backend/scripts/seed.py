from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.crud import (
    create_candidate,
    create_candidate_skill,
    create_employee,
    upsert_candidate_preference,
)
from app.db.session import SessionLocal
from app.models.candidate import Candidate
from app.models.employee import Employee
from app.models.source import JobSource
from app.schemas.candidate import CandidateCreate, CandidatePreferenceCreate, CandidateSkillCreate
from app.schemas.employee import EmployeeCreate

DEFAULT_SEED_DIR = Path("/app/seed-data")
BASE_DIR = Path(__file__).resolve().parents[1]
SEED_DIR = DEFAULT_SEED_DIR if DEFAULT_SEED_DIR.exists() else BASE_DIR.parent.parent / "seed-data"


def load_json(name: str) -> list[dict]:
    with (SEED_DIR / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def seed_employees() -> dict[str, int]:
    employee_records = load_json("employees.json")
    db = SessionLocal()
    employee_ids: dict[str, int] = {}

    try:
        existing = list(db.scalars(select(Employee).order_by(Employee.id.asc())))
        if existing:
            return {employee.name: employee.id for employee in existing}

        for payload in employee_records:
            employee = create_employee(db, EmployeeCreate(**payload))
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


def seed_candidates() -> None:
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
            assigned_employee_name = payload["assigned_employee_name"]
            candidate = create_candidate(
                db,
                CandidateCreate(
                    name=payload["name"],
                    assigned_employee=employee_ids.get(assigned_employee_name),
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


if __name__ == "__main__":
    seed_job_sources()
    seed_candidates()
    print("Seeded job sources and healthcare business analyst candidate profiles")
