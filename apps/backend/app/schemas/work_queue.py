from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.pagination import PageMeta


class EmployeeWorkQueueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    candidate_id: int
    job_id: int
    match_id: int | None = None
    priority_bucket: str
    score: float
    explanation: str | None = None
    status: str
    report_status: str | None = None
    report_reason: str | None = None
    reported_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class EmployeeWorkQueuePage(BaseModel):
    items: list[EmployeeWorkQueueRead]
    meta: PageMeta


class WorkQueueReportPayload(BaseModel):
    report_status: str   # "invalid" | "outdated" | "not_relevant"
    report_reason: str | None = None
