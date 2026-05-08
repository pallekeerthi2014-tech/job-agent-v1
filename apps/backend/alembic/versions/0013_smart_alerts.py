"""Phase 13: Smart alerts, keyword scoring, and alert deduplication.

Changes
-------
candidates
  • smart_alerts_enabled  BOOLEAN NOT NULL DEFAULT TRUE
      When true, alert fires on remote/hybrid-in-city + experience fit,
      bypassing the global score threshold entirely.
  • alert_threshold_override  FLOAT NULL
      Per-candidate score threshold used when smart_alerts_enabled=false.
      NULL means "use global ALERT_MIN_SCORE".

job_candidate_matches
  • keyword_score          FLOAT NULL
      Dedicated keyword-overlap dimension score (max 10 pts).
  • keyword_match_count    INTEGER NULL
      How many JD keywords were found in the candidate's resume.
  • keyword_match_total    INTEGER NULL
      Total unique JD keywords that were evaluated.
  • location_match_mode    VARCHAR(50) NULL
      One of: "remote" | "hybrid_city" | "onsite_city" | "none".
      Records which location logic drove the location score.
  • alerted_at             TIMESTAMPTZ NULL
      Stamped when an alert (WhatsApp or email) is sent for this match.
      NULL = not yet alerted. Prevents duplicate alerts across pipeline runs.

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── candidates ────────────────────────────────────────────────────────────
    op.add_column(
        "candidates",
        sa.Column(
            "smart_alerts_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "candidates",
        sa.Column("alert_threshold_override", sa.Float(), nullable=True),
    )

    # ── job_candidate_matches ─────────────────────────────────────────────────
    op.add_column(
        "job_candidate_matches",
        sa.Column("keyword_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "job_candidate_matches",
        sa.Column("keyword_match_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "job_candidate_matches",
        sa.Column("keyword_match_total", sa.Integer(), nullable=True),
    )
    op.add_column(
        "job_candidate_matches",
        sa.Column("location_match_mode", sa.String(50), nullable=True),
    )
    op.add_column(
        "job_candidate_matches",
        sa.Column(
            "alerted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    # Index for fast "find all unalerted matches" queries in dispatch_job_alerts
    op.create_index(
        "ix_job_candidate_matches_alerted_at",
        "job_candidate_matches",
        ["alerted_at"],
    )


def downgrade() -> None:
    # job_candidate_matches
    op.drop_index("ix_job_candidate_matches_alerted_at", table_name="job_candidate_matches")
    op.drop_column("job_candidate_matches", "alerted_at")
    op.drop_column("job_candidate_matches", "location_match_mode")
    op.drop_column("job_candidate_matches", "keyword_match_total")
    op.drop_column("job_candidate_matches", "keyword_match_count")
    op.drop_column("job_candidate_matches", "keyword_score")

    # candidates
    op.drop_column("candidates", "alert_threshold_override")
    op.drop_column("candidates", "smart_alerts_enabled")
