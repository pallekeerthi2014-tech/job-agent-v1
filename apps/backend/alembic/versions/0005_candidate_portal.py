"""Candidate portal: add candidate_id FK to users table

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-28
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add candidate_id column to users — links a "candidate" role login to a Candidate record
    op.add_column(
        "users",
        sa.Column("candidate_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_candidate_id",
        "users",
        "candidates",
        ["candidate_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint("uq_users_candidate_id", "users", ["candidate_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_candidate_id", "users", type_="unique")
    op.drop_constraint("fk_users_candidate_id", "users", type_="foreignkey")
    op.drop_column("users", "candidate_id")
