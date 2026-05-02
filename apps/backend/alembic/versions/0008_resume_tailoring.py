"""Phase 8: tailored_resumes table for AI resume tailoring workflow

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tailored_resumes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Integer(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("jobs_normalized.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "match_id",
            sa.Integer(),
            sa.ForeignKey("job_candidate_matches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by_employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_tailored_resumes_candidate_id", "tailored_resumes", ["candidate_id"])
    op.create_index("ix_tailored_resumes_job_id", "tailored_resumes", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_tailored_resumes_job_id", "tailored_resumes")
    op.drop_index("ix_tailored_resumes_candidate_id", "tailored_resumes")
    op.drop_table("tailored_resumes")
