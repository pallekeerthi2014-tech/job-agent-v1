from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSON_VARIANT


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_employee: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    work_authorization: Mapped[str | None] = mapped_column(String(100), nullable=True)
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employee = relationship("Employee", back_populates="assigned_candidates")
    preference = relationship("CandidatePreference", back_populates="candidate", uselist=False, cascade="all, delete-orphan")
    skills = relationship("CandidateSkill", back_populates="candidate", cascade="all, delete-orphan")
    matches = relationship("JobCandidateMatch", back_populates="candidate", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")


class CandidatePreference(Base):
    __tablename__ = "candidate_preferences"

    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True)
    preferred_titles: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    employment_preferences: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    location_preferences: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    domain_expertise: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    must_have_keywords: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list, nullable=False)
    exclude_keywords: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list, nullable=False)

    candidate = relationship("Candidate", back_populates="preference")


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    __table_args__ = (Index("ix_candidate_skills_candidate_id", "candidate_id"),)

    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True)
    skill_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    years_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    candidate = relationship("Candidate", back_populates="skills")
