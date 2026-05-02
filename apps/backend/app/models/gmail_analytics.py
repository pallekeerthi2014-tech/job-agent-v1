from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CandidateMailbox(Base):
    __tablename__ = "candidate_mailboxes"
    __table_args__ = (
        UniqueConstraint("candidate_id", name="uq_candidate_mailboxes_candidate_id"),
        UniqueConstraint("email", name="uq_candidate_mailboxes_email"),
        Index("ix_candidate_mailboxes_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    gmail_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    calendar_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_uri: Mapped[str] = mapped_column(String(500), nullable=False, default="https://oauth2.googleapis.com/token")
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_email_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_calendar_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    candidate = relationship("Candidate")
    email_events = relationship("EmailEvent", back_populates="mailbox", cascade="all, delete-orphan")
    calendar_events = relationship("CandidateCalendarEvent", back_populates="mailbox", cascade="all, delete-orphan")


class EmailEvent(Base):
    __tablename__ = "email_events"
    __table_args__ = (
        UniqueConstraint("mailbox_id", "gmail_message_id", name="uq_email_events_mailbox_message"),
        Index("ix_email_events_candidate_received", "candidate_id", "received_at"),
        Index("ix_email_events_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mailbox_id: Mapped[int] = mapped_column(ForeignKey("candidate_mailboxes.id", ondelete="CASCADE"), nullable=False)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    gmail_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    gmail_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sender: Mapped[str | None] = mapped_column(String(500), nullable=True)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detected_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    importance: Mapped[str] = mapped_column(String(40), nullable=False, default="normal")
    action_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gmail_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    mailbox = relationship("CandidateMailbox", back_populates="email_events")
    candidate = relationship("Candidate")


class CandidateCalendarEvent(Base):
    __tablename__ = "candidate_calendar_events"
    __table_args__ = (
        UniqueConstraint("mailbox_id", "google_event_id", name="uq_candidate_calendar_events_mailbox_event"),
        Index("ix_candidate_calendar_events_candidate_start", "candidate_id", "starts_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mailbox_id: Mapped[int] = mapped_column(ForeignKey("candidate_mailboxes.id", ondelete="CASCADE"), nullable=False)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    google_event_id: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    organizer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meeting_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    calendar_source: Mapped[str] = mapped_column(String(80), nullable=False, default="primary")
    is_interview_like: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    mailbox = relationship("CandidateMailbox", back_populates="calendar_events")
    candidate = relationship("Candidate")


class DailyCandidateMetric(Base):
    __tablename__ = "daily_candidate_metrics"
    __table_args__ = (
        UniqueConstraint("candidate_id", "metric_date", name="uq_daily_candidate_metrics_candidate_date"),
        Index("ix_daily_candidate_metrics_date", "metric_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    metric_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    jobs_applied_detected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recruiter_replies: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    interview_invites: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assessments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejections: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    followups_required: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_mailbox_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    candidate = relationship("Candidate")
