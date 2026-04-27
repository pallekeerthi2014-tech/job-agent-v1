from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EmployeeWorkQueue(Base):
    __tablename__ = "employee_work_queues"
    __table_args__ = (
        UniqueConstraint("employee_id", "candidate_id", "job_id", name="uq_employee_queue_assignment"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs_normalized.id", ondelete="CASCADE"), nullable=False)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("job_candidate_matches.id", ondelete="SET NULL"), nullable=True)
    priority_bucket: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    # Employee-reported quality signals fed back to analytics
    report_status: Mapped[str | None] = mapped_column(String(50), nullable=True)  # invalid|outdated|not_relevant
    report_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    employee = relationship("Employee")
    candidate = relationship("Candidate")
    job = relationship("JobNormalized")
    match = relationship("JobCandidateMatch")
