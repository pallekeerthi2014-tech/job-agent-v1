from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import PageMeta


class CandidateBase(BaseModel):
    name: str
    assigned_employee: int | None = None
    work_authorization: str | None = None
    years_experience: int | None = None
    salary_min: int | None = None
    salary_unit: str | None = None
    active: bool = True


class CandidateCreate(CandidateBase):
    pass


class CandidateUpdate(BaseModel):
    name: str | None = None
    assigned_employee: int | None = None
    work_authorization: str | None = None
    years_experience: int | None = None
    salary_min: int | None = None
    salary_unit: str | None = None
    active: bool | None = None


class CandidateRead(CandidateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class CandidatePreferenceBase(BaseModel):
    preferred_titles: list[str] = Field(default_factory=list)
    employment_preferences: list[str] = Field(default_factory=list)
    location_preferences: list[str] = Field(default_factory=list)
    domain_expertise: list[str] = Field(default_factory=list)
    must_have_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)


class CandidatePreferenceCreate(CandidatePreferenceBase):
    candidate_id: int


class CandidatePreferenceUpsert(CandidatePreferenceBase):
    pass


class CandidatePreferenceRead(CandidatePreferenceBase):
    model_config = ConfigDict(from_attributes=True)

    candidate_id: int


class CandidateSkillBase(BaseModel):
    candidate_id: int
    skill_name: str
    years_used: int | None = None


class CandidateSkillCreate(CandidateSkillBase):
    pass


class CandidateSkillRead(CandidateSkillBase):
    model_config = ConfigDict(from_attributes=True)


class CandidatePage(BaseModel):
    items: list[CandidateRead]
    meta: PageMeta
