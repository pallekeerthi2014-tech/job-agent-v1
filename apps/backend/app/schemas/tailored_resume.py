from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TailoredResumeRead(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    status: str
    filename: str | None
    notes: str | None
    created_at: datetime
    error_message: str | None

    model_config = {"from_attributes": True}


class TailoredResumeReadWithFlags(TailoredResumeRead):
    """Returned by POST /jobs/{job_id}/tailor-resume — may include flagged skills."""
    flagged_skills: list[str] = []


class TailorResumeRequest(BaseModel):
    candidate_id: int
    notes: str | None = None
    confirm_flagged_skills: list[str] | None = None  # employee confirms these skills are OK to add
