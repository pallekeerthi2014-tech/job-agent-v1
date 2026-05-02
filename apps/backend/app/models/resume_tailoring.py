from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSON_VARIANT


class ResumeTailoringDraft(Base):
    __tablename__ = "resume_tailoring_drafts"
    __table_args__ = (
        Index("ix_resume_tailoring_drafts_candidate_id", "candidate_id"),
        Index("ix_resume_tailoring_drafts_job_id", "job_id"),
        Index("ix_resume_tailoring_drafts_created_by_user_id", "created_by_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs_normalized.id", ondelete="CASCADE"), nullable=False)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("job_candidate_matches.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    recruiter_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    suggested_edits: Mapped[list[dict]] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    skill_gaps: Mapped[list[dict]] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    approved_edits: Mapped[list[dict]] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    confirmed_skills: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    generated_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
