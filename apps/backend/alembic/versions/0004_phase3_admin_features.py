"""Phase 3 admin features: AlertRecipient table, resume + contact fields on Candidate, report fields on EmployeeWorkQueue

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003_password_reset_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── alert_recipients table ────────────────────────────────────────────────
    op.create_table(
        "alert_recipients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone_number", sa.String(30), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_number", name="uq_alert_recipients_phone_number"),
    )

    # ── Candidate: new contact + resume columns ───────────────────────────────
    op.add_column("candidates", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("candidates", sa.Column("phone", sa.String(30), nullable=True))
    op.add_column("candidates", sa.Column("location", sa.String(255), nullable=True))
    op.add_column("candidates", sa.Column("resume_filename", sa.String(500), nullable=True))
    op.add_column("candidates", sa.Column("resume_text", sa.Text(), nullable=True))

    try:
        op.create_unique_constraint("uq_candidates_email", "candidates", ["email"])
    except Exception:
        pass  # Column may already have unique index in some DB flavours

    # ── EmployeeWorkQueue: report fields ─────────────────────────────────────
    op.add_column("employee_work_queues", sa.Column("report_status", sa.String(50), nullable=True))
    op.add_column("employee_work_queues", sa.Column("report_reason", sa.String(500), nullable=True))
    op.add_column("employee_work_queues", sa.Column("reported_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("employee_work_queues", "reported_at")
    op.drop_column("employee_work_queues", "report_reason")
    op.drop_column("employee_work_queues", "report_status")

    op.drop_column("candidates", "resume_text")
    op.drop_column("candidates", "resume_filename")
    op.drop_column("candidates", "location")
    op.drop_column("candidates", "phone")
    op.drop_column("candidates", "email")

    op.drop_table("alert_recipients")
