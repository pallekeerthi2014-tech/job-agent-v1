from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.candidate import Candidate
from app.models.employee import Employee
from app.models.match_score import JobCandidateMatch
from app.models.work_queue import EmployeeWorkQueue


def create_employee_work_queues(db: Session) -> int:
    matches = list(
        db.scalars(
            select(JobCandidateMatch)
            .options(joinedload(JobCandidateMatch.candidate))
            .order_by(JobCandidateMatch.score.desc(), JobCandidateMatch.id.asc())
        )
    )
    employees = list(db.scalars(select(Employee).order_by(Employee.id.asc())))
    if not employees:
        return 0

    queue_count = 0
    fallback_employee = employees[0]

    for match in matches:
        candidate = match.candidate
        employee_id = candidate.assigned_employee or fallback_employee.id
        queue_item = db.scalar(
            select(EmployeeWorkQueue).where(
                EmployeeWorkQueue.employee_id == employee_id,
                EmployeeWorkQueue.candidate_id == match.candidate_id,
                EmployeeWorkQueue.job_id == match.job_id,
            )
        )

        values = {
            "match_id": match.id,
            "priority_bucket": match.status or _bucket_from_priority(match.priority),
            "score": match.score,
            "explanation": match.explanation,
            "status": "pending",
        }

        if queue_item:
            for key, value in values.items():
                setattr(queue_item, key, value)
        else:
            db.add(
                EmployeeWorkQueue(
                    employee_id=employee_id,
                    candidate_id=match.candidate_id,
                    job_id=match.job_id,
                    **values,
                )
            )
        queue_count += 1

    db.commit()
    return queue_count


def _bucket_from_priority(priority: int | None) -> str:
    if priority == 1:
        return "High"
    if priority == 2:
        return "Medium"
    return "Low"
