from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.pagination import PageMeta


class JobCandidateMatchBase(BaseModel):
    job_id: int
    candidate_id: int
    score: float
    priority: int | None = None
    title_score: float | None = None
    domain_score: float | None = None
    skills_score: float | None = None
    experience_score: float | None = None
    employment_preference_score: float | None = None
    visa_score: float | None = None
    location_score: float | None = None
    explanation: str | None = None
    status: str | None = None


class JobCandidateMatchCreate(JobCandidateMatchBase):
    pass


class JobCandidateMatchRead(JobCandidateMatchBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class JobCandidateMatchPage(BaseModel):
    items: list[JobCandidateMatchRead]
    meta: PageMeta
