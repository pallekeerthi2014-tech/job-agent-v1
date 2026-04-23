from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSON_VARIANT


class JobRaw(Base):
    __tablename__ = "jobs_raw"
    __table_args__ = (Index("ix_jobs_raw_source", "source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    external_job_id: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class JobNormalized(Base):
    __tablename__ = "jobs_normalized"
    __table_args__ = (
        Index("ix_jobs_normalized_source", "source"),
        Index("ix_jobs_normalized_posted_date", "posted_date"),
        Index("ix_jobs_normalized_dedupe_hash", "dedupe_hash"),
        Index("ix_jobs_normalized_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    employment_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    posted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    posted_at_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    freshness_status: Mapped[str] = mapped_column(String(50), nullable=False, default="unverified")
    freshness_age_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    apply_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    canonical_apply_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_description_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    domain_tags: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    visa_hints: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    keywords_extracted: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    dedupe_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    probable_duplicate_of_job_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    duplicate_reasons: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list, nullable=False)

    matches = relationship("JobCandidateMatch", back_populates="job", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
