"""phase 1 canonical tables

Revision ID: 0001_phase1_initial
Revises:
Create Date: 2026-04-22 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_phase1_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("adapter_type", sa.String(length=100), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
    )

    op.create_table(
        "candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("assigned_employee", sa.Integer(), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("work_authorization", sa.String(length=100), nullable=True),
        sa.Column("years_experience", sa.Integer(), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_unit", sa.String(length=50), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "candidate_preferences",
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("preferred_titles", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("employment_preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("location_preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("domain_expertise", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("must_have_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("exclude_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.create_index("ix_candidate_preferences_candidate_id", "candidate_preferences", ["candidate_id"])

    op.create_table(
        "candidate_skills",
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("skill_name", sa.String(length=255), primary_key=True),
        sa.Column("years_used", sa.Integer(), nullable=True),
    )
    op.create_index("ix_candidate_skills_candidate_id", "candidate_skills", ["candidate_id"])

    op.create_table(
        "jobs_raw",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("external_job_id", sa.String(length=255), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_jobs_raw_source", "jobs_raw", ["source"])

    op.create_table(
        "jobs_normalized",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("is_remote", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("employment_type", sa.String(length=100), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("posted_date", sa.Date(), nullable=True),
        sa.Column("posted_at_text", sa.String(length=255), nullable=True),
        sa.Column("freshness_status", sa.String(length=50), nullable=False, server_default=sa.text("'unverified'")),
        sa.Column("freshness_age_hours", sa.Integer(), nullable=True),
        sa.Column("apply_url", sa.String(length=500), nullable=True),
        sa.Column("canonical_apply_url", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("normalized_description_hash", sa.String(length=64), nullable=True),
        sa.Column("domain_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("visa_hints", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("keywords_extracted", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("dedupe_hash", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("probable_duplicate_of_job_id", sa.Integer(), nullable=True),
        sa.Column("duplicate_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.create_index("ix_jobs_normalized_source", "jobs_normalized", ["source"])
    op.create_index("ix_jobs_normalized_posted_date", "jobs_normalized", ["posted_date"])
    op.create_index("ix_jobs_normalized_dedupe_hash", "jobs_normalized", ["dedupe_hash"])
    op.create_index("ix_jobs_normalized_is_active", "jobs_normalized", ["is_active"])

    op.create_table(
        "job_candidate_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs_normalized.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("title_score", sa.Float(), nullable=True),
        sa.Column("domain_score", sa.Float(), nullable=True),
        sa.Column("skills_score", sa.Float(), nullable=True),
        sa.Column("experience_score", sa.Float(), nullable=True),
        sa.Column("employment_preference_score", sa.Float(), nullable=True),
        sa.Column("visa_score", sa.Float(), nullable=True),
        sa.Column("location_score", sa.Float(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate_match"),
    )
    op.create_index("ix_job_candidate_matches_job_id", "job_candidate_matches", ["job_id"])
    op.create_index("ix_job_candidate_matches_candidate_id", "job_candidate_matches", ["candidate_id"])
    op.create_index("ix_job_candidate_matches_score", "job_candidate_matches", ["score"])

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs_normalized.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_applications_candidate_id", "applications", ["candidate_id"])
    op.create_index("ix_applications_job_id", "applications", ["job_id"])

    op.create_table(
        "employee_work_queues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs_normalized.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("job_candidate_matches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("priority_bucket", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("employee_id", "candidate_id", "job_id", name="uq_employee_queue_assignment"),
    )


def downgrade() -> None:
    op.drop_table("employee_work_queues")
    op.drop_index("ix_applications_job_id", table_name="applications")
    op.drop_index("ix_applications_candidate_id", table_name="applications")
    op.drop_table("applications")
    op.drop_index("ix_job_candidate_matches_score", table_name="job_candidate_matches")
    op.drop_index("ix_job_candidate_matches_candidate_id", table_name="job_candidate_matches")
    op.drop_index("ix_job_candidate_matches_job_id", table_name="job_candidate_matches")
    op.drop_table("job_candidate_matches")
    op.drop_index("ix_jobs_normalized_is_active", table_name="jobs_normalized")
    op.drop_index("ix_jobs_normalized_dedupe_hash", table_name="jobs_normalized")
    op.drop_index("ix_jobs_normalized_posted_date", table_name="jobs_normalized")
    op.drop_index("ix_jobs_normalized_source", table_name="jobs_normalized")
    op.drop_table("jobs_normalized")
    op.drop_index("ix_jobs_raw_source", table_name="jobs_raw")
    op.drop_table("jobs_raw")
    op.drop_index("ix_candidate_skills_candidate_id", table_name="candidate_skills")
    op.drop_table("candidate_skills")
    op.drop_index("ix_candidate_preferences_candidate_id", table_name="candidate_preferences")
    op.drop_table("candidate_preferences")
    op.drop_table("candidates")
    op.drop_table("employees")
    op.drop_table("job_sources")
