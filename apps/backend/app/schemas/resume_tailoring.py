from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResumeTailoringDraftCreate(BaseModel):
    candidate_id: int
    job_id: int
    match_id: int | None = None
    recruiter_context: str | None = Field(default=None, max_length=6000)


class ResumeTailoringSuggestion(BaseModel):
    id: str
    section: str
    text: str
    skill_tags: list[str] = Field(default_factory=list)
    evidence: str | None = None
    status: str


class ResumeTailoringSkillGap(BaseModel):
    skill: str
    reason: str
    source: str


class ResumeTailoringDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    job_id: int
    match_id: int | None = None
    recruiter_context: str | None = None
    status: str
    suggested_edits: list[ResumeTailoringSuggestion] = Field(default_factory=list)
    skill_gaps: list[ResumeTailoringSkillGap] = Field(default_factory=list)
    approved_edits: list[ResumeTailoringSuggestion] = Field(default_factory=list)
    confirmed_skills: list[str] = Field(default_factory=list)
    generated_filename: str | None = None
    created_at: datetime
    updated_at: datetime


class ResumeTailoringDownloadRequest(BaseModel):
    approved_suggestion_ids: list[str] = Field(default_factory=list)
    confirmed_skills: list[str] = Field(default_factory=list)
