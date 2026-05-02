"""Phase 7: ingestion_runs table + last_successful_run_at on job_sources

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add last_successful_run_at to job_sources
    op.add_column(
        "job_sources",
        sa.Column("last_successful_run_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 2. Create ingestion_runs table
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("job_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="error"),
        sa.Column("raw_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_stored", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_ingestion_runs_source_id", "ingestion_runs", ["source_id"])
    op.create_index("ix_ingestion_runs_started_at", "ingestion_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_ingestion_runs_started_at", "ingestion_runs")
    op.drop_index("ix_ingestion_runs_source_id", "ingestion_runs")
    op.drop_table("ingestion_runs")
    op.drop_column("job_sources", "last_successful_run_at")
