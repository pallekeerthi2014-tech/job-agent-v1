"""Phase 9: candidate Gmail analytics

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_mailboxes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("gmail_connected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("calendar_connected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_uri", sa.String(500), nullable=False, server_default="https://oauth2.googleapis.com/token"),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_email_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_calendar_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("candidate_id", name="uq_candidate_mailboxes_candidate_id"),
        sa.UniqueConstraint("email", name="uq_candidate_mailboxes_email"),
    )
    op.create_index("ix_candidate_mailboxes_status", "candidate_mailboxes", ["status"])

    op.create_table(
        "email_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mailbox_id", sa.Integer(), sa.ForeignKey("candidate_mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gmail_message_id", sa.String(255), nullable=False),
        sa.Column("gmail_thread_id", sa.String(255), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sender", sa.String(500), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("detected_company", sa.String(255), nullable=True),
        sa.Column("detected_role", sa.String(255), nullable=True),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("importance", sa.String(40), nullable=False, server_default="normal"),
        sa.Column("action_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("gmail_link", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("mailbox_id", "gmail_message_id", name="uq_email_events_mailbox_message"),
    )
    op.create_index("ix_email_events_candidate_received", "email_events", ["candidate_id", "received_at"])
    op.create_index("ix_email_events_category", "email_events", ["category"])

    op.create_table(
        "candidate_calendar_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mailbox_id", sa.Integer(), sa.ForeignKey("candidate_mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("google_event_id", sa.String(500), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organizer", sa.String(500), nullable=True),
        sa.Column("meeting_link", sa.Text(), nullable=True),
        sa.Column("calendar_source", sa.String(80), nullable=False, server_default="primary"),
        sa.Column("is_interview_like", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("mailbox_id", "google_event_id", name="uq_candidate_calendar_events_mailbox_event"),
    )
    op.create_index("ix_candidate_calendar_events_candidate_start", "candidate_calendar_events", ["candidate_id", "starts_at"])

    op.create_table(
        "daily_candidate_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("jobs_applied_detected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recruiter_replies", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interview_invites", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assessments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejections", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("followups_required", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_mailbox_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("candidate_id", "metric_date", name="uq_daily_candidate_metrics_candidate_date"),
    )
    op.create_index("ix_daily_candidate_metrics_date", "daily_candidate_metrics", ["metric_date"])


def downgrade() -> None:
    op.drop_index("ix_daily_candidate_metrics_date", table_name="daily_candidate_metrics")
    op.drop_table("daily_candidate_metrics")
    op.drop_index("ix_candidate_calendar_events_candidate_start", table_name="candidate_calendar_events")
    op.drop_table("candidate_calendar_events")
    op.drop_index("ix_email_events_category", table_name="email_events")
    op.drop_index("ix_email_events_candidate_received", table_name="email_events")
    op.drop_table("email_events")
    op.drop_index("ix_candidate_mailboxes_status", table_name="candidate_mailboxes")
    op.drop_table("candidate_mailboxes")
