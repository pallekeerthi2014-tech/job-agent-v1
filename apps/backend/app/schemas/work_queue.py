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
    created_at: datetime
    updated_at: datetime


class EmployeeWorkQueuePage(BaseModel):
    items: list[EmployeeWorkQueueRead]
    meta: PageMeta
