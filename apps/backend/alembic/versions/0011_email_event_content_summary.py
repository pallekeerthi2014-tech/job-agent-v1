"""Add Gmail email content summary

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("email_events", sa.Column("content_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("email_events", "content_summary")
