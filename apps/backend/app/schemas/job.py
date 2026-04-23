from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import PageMeta


class JobRawBase(BaseModel):
    source: str
    external_job_id: str
    raw_payload: dict


class JobRawCreate(JobRawBase):
    pass


class JobRawRead(JobRawBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fetched_at: datetime


class JobNormalizedBase(BaseModel):
    source: str
    title: str
    company: str
    location: str | None = None
    is_remote: bool = False
    employment_type: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    posted_date: date | None = None
    posted_at_text: str | None = None
    freshness_status: str = "unverified"
    freshness_age_hours: int | None = None
    apply_url: str | None = None
    canonical_apply_url: str | None = None
    description: str | None = None
    normalized_description_hash: str | None = None
    domain_tags: list[str] = Field(default_factory=list)
    visa_hints: list[str] = Field(default_factory=list)
    keywords_extracted: list[str] = Field(default_factory=list)
    dedupe_hash: str | None = None
    is_active: bool = True
    probable_duplicate_of_job_id: int | None = None
    duplicate_reasons: list[str] = Field(default_factory=list)


class JobNormalizedCreate(JobNormalizedBase):
    pass


class JobNormalizedRead(JobNormalizedBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class JobNormalizedPage(BaseModel):
    items: list[JobNormalizedRead]
    meta: PageMeta
