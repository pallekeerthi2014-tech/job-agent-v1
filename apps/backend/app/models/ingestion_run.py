from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class IngestionRun(Base):
    """One row per source per pipeline cycle — tracks what happened for each fetch."""

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("job_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # "success" | "error"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="error")

    raw_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_stored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jobs_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship back to the source (optional, for ORM joins)
    source = relationship("JobSource", back_populates="ingestion_runs")
