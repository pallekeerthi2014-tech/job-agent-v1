from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.pagination import PageMeta


class ApplicationBase(BaseModel):
    candidate_id: int
    job_id: int
    employee_id: int | None = None
    status: str | None = None
    notes: str | None = None


class ApplicationCreate(ApplicationBase):
    applied_at: datetime | None = None


class ApplicationRead(ApplicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    applied_at: datetime


class ApplicationPage(BaseModel):
    items: list[ApplicationRead]
    meta: PageMeta
