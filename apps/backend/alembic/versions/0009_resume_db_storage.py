"""Phase 9: Store resume file bytes in DB so they survive container restarts/redeployments.

Adds resume_docx (BYTEA) to candidates table.
No Railway volume required after this migration.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Store the raw file bytes for any uploaded resume (all types: pdf, docx, txt).
    # This makes resumes durable across Railway redeployments without a volume.
    op.add_column(
        "candidates",
        sa.Column("resume_bytes", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "candidates",
        sa.Column("resume_content_type", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("candidates", "resume_content_type")
    op.drop_column("candidates", "resume_bytes")
