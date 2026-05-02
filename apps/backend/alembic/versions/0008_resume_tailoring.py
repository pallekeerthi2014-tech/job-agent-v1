"""Phase 8: resume tailoring drafts

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import JSON_VARIANT

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_tailoring_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs_normalized.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("job_candidate_matches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recruiter_context", sa.Text(), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("suggested_edits", JSON_VARIANT, nullable=False, server_default="[]"),
        sa.Column("skill_gaps", JSON_VARIANT, nullable=False, server_default="[]"),
        sa.Column("approved_edits", JSON_VARIANT, nullable=False, server_default="[]"),
        sa.Column("confirmed_skills", JSON_VARIANT, nullable=False, server_default="[]"),
        sa.Column("generated_filename", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_resume_tailoring_drafts_candidate_id", "resume_tailoring_drafts", ["candidate_id"])
    op.create_index("ix_resume_tailoring_drafts_job_id", "resume_tailoring_drafts", ["job_id"])
    op.create_index("ix_resume_tailoring_drafts_created_by_user_id", "resume_tailoring_drafts", ["created_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_resume_tailoring_drafts_created_by_user_id", "resume_tailoring_drafts")
    op.drop_index("ix_resume_tailoring_drafts_job_id", "resume_tailoring_drafts")
    op.drop_index("ix_resume_tailoring_drafts_candidate_id", "resume_tailoring_drafts")
    op.drop_table("resume_tailoring_drafts")
