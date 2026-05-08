from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class JobCandidateMatch(Base):
    __tablename__ = "job_candidate_matches"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate_match"),
        Index("ix_job_candidate_matches_job_id", "job_id"),
        Index("ix_job_candidate_matches_candidate_id", "candidate_id"),
        Index("ix_job_candidate_matches_score", "score"),
        # Fast lookup for deduplication: find unalerted matches above threshold
        Index("ix_job_candidate_matches_alerted_at", "alerted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs_normalized.id", ondelete="CASCADE"), nullable=False)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    domain_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    skills_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    employment_preference_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    visa_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # New: dedicated keyword overlap dimension
    keyword_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Transparency: how many JD keywords appeared in the candidate's resume
    keyword_match_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    keyword_match_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Location mode that drove the location score ("remote" | "hybrid_city" | "onsite_city" | "none")
    location_match_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Alert deduplication — NULL means this match has not yet triggered an alert.
    # Stamped by alert_service after a WhatsApp/email is sent so the same
    # candidate+job pair never fires twice across pipeline runs.
    alerted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job = relationship("JobNormalized", back_populates="matches")
    candidate = relationship("Candidate", back_populates="matches")
