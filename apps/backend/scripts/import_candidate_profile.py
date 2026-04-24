from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.db.crud import create_candidate, create_candidate_skill, create_employee, upsert_candidate_preference
from app.db.session import SessionLocal
from app.models.candidate import Candidate, CandidateSkill
from app.models.employee import Employee
from app.schemas.candidate import CandidateCreate, CandidatePreferenceCreate, CandidateSkillCreate
from app.schemas.employee import EmployeeCreate

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_PATH = BASE_DIR.parent / "seed-data" / "shweta_dani_candidate.json"


def load_profile(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_employee(db, employee_name: str) -> int | None:
    employee = db.scalar(select(Employee).where(Employee.name == employee_name))
    if employee:
        return employee.id

    email = f"{employee_name.lower().replace(' ', '.')}@thinksuccessitconsulting.com"
    created = create_employee(db, EmployeeCreate(name=employee_name, email=email))
    return created.id


def import_candidate_profile(path: Path) -> int:
    payload = load_profile(path)
    db = SessionLocal()
    try:
        assigned_employee_id = None
        if payload.get("assigned_employee_name"):
            assigned_employee_id = ensure_employee(db, payload["assigned_employee_name"])

        existing_candidate = db.scalar(select(Candidate).where(Candidate.name == payload["name"]))
        candidate_values = {
            "name": payload["name"],
            "assigned_employee": assigned_employee_id,
            "work_authorization": payload.get("work_authorization"),
            "years_experience": payload.get("years_experience"),
            "salary_min": payload.get("salary_min"),
            "salary_unit": payload.get("salary_unit"),
            "active": payload.get("active", True),
        }

        if existing_candidate is None:
            candidate = create_candidate(db, CandidateCreate(**candidate_values))
        else:
            for key, value in candidate_values.items():
                setattr(existing_candidate, key, value)
            db.commit()
            db.refresh(existing_candidate)
            candidate = existing_candidate

        upsert_candidate_preference(
            db,
            CandidatePreferenceCreate(
                candidate_id=candidate.id,
                preferred_titles=payload.get("preferred_titles", []),
                employment_preferences=payload.get("employment_preferences", []),
                location_preferences=payload.get("location_preferences", []),
                domain_expertise=payload.get("healthcare_domain_expertise", []),
                must_have_keywords=payload.get("must_have_keywords", []),
                exclude_keywords=payload.get("exclude_keywords", []),
            ),
        )

        existing_skills = {
            skill.skill_name.lower(): skill
            for skill in db.scalars(select(CandidateSkill).where(CandidateSkill.candidate_id == candidate.id))
        }
        for skill_payload in payload.get("skills", []):
            key = skill_payload["skill_name"].lower()
            if key in existing_skills:
                existing_skills[key].years_used = skill_payload.get("years_used")
            else:
                create_candidate_skill(
                    db,
                    CandidateSkillCreate(
                        candidate_id=candidate.id,
                        skill_name=skill_payload["skill_name"],
                        years_used=skill_payload.get("years_used"),
                    ),
                )

        db.commit()
        return candidate.id
    finally:
        db.close()


if __name__ == "__main__":
    profile_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_PROFILE_PATH
    candidate_id = import_candidate_profile(profile_path)
    print(f"Imported candidate profile with id={candidate_id} from {profile_path}")
