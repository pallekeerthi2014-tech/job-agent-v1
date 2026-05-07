"""Store tailored resume artifacts and copy-paste suggestions

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tailored_resumes", sa.Column("file_bytes", sa.LargeBinary(), nullable=True))
    op.add_column("tailored_resumes", sa.Column("content_type", sa.String(100), nullable=True))
    op.add_column("tailored_resumes", sa.Column("suggested_lines", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tailored_resumes", "suggested_lines")
    op.drop_column("tailored_resumes", "content_type")
    op.drop_column("tailored_resumes", "file_bytes")
