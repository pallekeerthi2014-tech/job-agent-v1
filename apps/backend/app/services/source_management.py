"""
Source management service — CRUD + Test-Connection + Run-Now for JobSource rows.

This is the backend behind the admin "Sources" / "Feed Management" page.

Responsibilities:
  * list_sources / get_source / create_source / update_source / delete_source
  * test_source: run an adapter once with a given config, return sample jobs,
    NEVER write to the DB. Used by the wizard's "Test Connection" button.
  * run_source_now: run ingestion for one source (writes to DB) so admins can
    pull jobs immediately after editing instead of waiting for the scheduler.
  * source_stats: per-source jobs count rollups (total / 24h / 7d) for the
    Sources table.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.job import JobRaw
from app.models.source import JobSource
from app.schemas.source import (
    SourceCreate,
    SourceJobSample,
    SourceRunResult,
    SourceTestResult,
    SourceUpdate,
)
from app.services.logging_utils import log_event
from app.services.role_filtering import (
    DEFAULT_ANALYST_EXCLUDE_TITLES,
    DEFAULT_ANALYST_INCLUDE_TITLES,
    is_relevant_analyst_role,
)
from app.services.source_adapters.registry import build_source_adapter, ADAPTER_REGISTRY


logger = logging.getLogger(__name__)


# ── CRUD ─────────────────────────────────────────────────────────────────────

def list_sources(db: Session) -> list[JobSource]:
    return list(db.scalars(select(JobSource).order_by(JobSource.id.asc())))


def get_source(db: Session, source_id: int) -> JobSource | None:
    return db.scalar(select(JobSource).where(JobSource.id == source_id))


def get_source_by_name(db: Session, name: str) -> JobSource | None:
    return db.scalar(select(JobSource).where(JobSource.name == name))


def create_source(db: Session, payload: SourceCreate) -> JobSource:
    if payload.adapter_type not in ADAPTER_REGISTRY:
        raise ValueError(
            f"Unknown adapter_type '{payload.adapter_type}'. "
            f"Supported: {sorted(ADAPTER_REGISTRY)}"
        )
    if get_source_by_name(db, payload.name) is not None:
        raise ValueError(f"A source named '{payload.name}' already exists")

    source = JobSource(
        name=payload.name,
        adapter_type=payload.adapter_type,
        config=payload.config or {},
        enabled=payload.enabled,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    log_event(logging.INFO, "admin.source.created", source_id=source.id, name=source.name, adapter_type=source.adapter_type)
    return source


def update_source(db: Session, source_id: int, payload: SourceUpdate) -> JobSource | None:
    source = get_source(db, source_id)
    if source is None:
        return None

    if payload.name is not None and payload.name != source.name:
        clash = get_source_by_name(db, payload.name)
        if clash is not None and clash.id != source.id:
            raise ValueError(f"A source named '{payload.name}' already exists")
        source.name = payload.name

    if payload.adapter_type is not None:
        if payload.adapter_type not in ADAPTER_REGISTRY:
            raise ValueError(
                f"Unknown adapter_type '{payload.adapter_type}'. "
                f"Supported: {sorted(ADAPTER_REGISTRY)}"
            )
        source.adapter_type = payload.adapter_type

    if payload.config is not None:
        source.config = payload.config

    if payload.enabled is not None:
        source.enabled = payload.enabled

    db.commit()
    db.refresh(source)
    log_event(logging.INFO, "admin.source.updated", source_id=source.id, name=source.name)
    return source


def delete_source(db: Session, source_id: int) -> bool:
    source = get_source(db, source_id)
    if source is None:
        return False
    db.delete(source)
    db.commit()
    log_event(logging.INFO, "admin.source.deleted", source_id=source_id)
    return True


# ── Test connection (no DB writes) ───────────────────────────────────────────

def test_source_config(
    *,
    adapter_type: str,
    config: dict[str, Any],
    source_name: str = "test-source",
    sample_size: int = 3,
) -> SourceTestResult:
    """
    Run the adapter once with the supplied config but DO NOT write anything to
    the DB. Returns a sample of returned jobs so the admin can sanity-check
    before saving. This is what powers the wizard's "Test Connection" button.
    """
    started = time.perf_counter()
    try:
        adapter = build_source_adapter(adapter_type, source_name, config)
        raw_jobs = adapter.fetch_jobs()
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        log_event(logging.WARNING, "admin.source.test.failed", adapter_type=adapter_type, error=str(exc), duration_ms=duration_ms)
        return SourceTestResult(
            success=False,
            adapter_type=adapter_type,
            raw_jobs_returned=0,
            error=str(exc),
            duration_ms=duration_ms,
        )

    samples: list[SourceJobSample] = []
    for raw in raw_jobs[:sample_size]:
        try:
            normalized = adapter.normalize_job(raw)
            samples.append(
                SourceJobSample(
                    title=normalized.title,
                    company=normalized.company,
                    location=normalized.location,
                    apply_url=normalized.apply_url,
                    posted_date=normalized.posted_date,
                    external_job_id=normalized.external_job_id,
                )
            )
        except Exception as exc:  # pragma: no cover — defensive
            log_event(logging.WARNING, "admin.source.test.normalize_failed", adapter_type=adapter_type, error=str(exc))

    duration_ms = int((time.perf_counter() - started) * 1000)
    log_event(
        logging.INFO,
        "admin.source.test.ok",
        adapter_type=adapter_type,
        raw_jobs_returned=len(raw_jobs),
        duration_ms=duration_ms,
    )
    return SourceTestResult(
        success=True,
        adapter_type=adapter_type,
        raw_jobs_returned=len(raw_jobs),
        sample_jobs=samples,
        duration_ms=duration_ms,
    )


# ── Run a single source now (DB writes) ──────────────────────────────────────

def run_source_now(db: Session, source_id: int) -> SourceRunResult | None:
    """
    Pull jobs from one source synchronously and persist new raw rows.

    Mirrors the per-source loop body in services.ingestion.fetch_jobs_from_enabled_sources
    but scoped to a single source_id and returns its result. Does NOT run
    normalization / scoring / queue creation — those happen on the next full
    pipeline run (POST /admin/run-daily-pipeline) so this stays fast.
    """
    source = get_source(db, source_id)
    if source is None:
        return None

    started = time.perf_counter()
    stored = 0
    skipped_irrelevant = 0
    error: str | None = None

    try:
        adapter = build_source_adapter(source.adapter_type, source.name, source.config)
        raw_jobs = adapter.fetch_jobs()

        include_titles = source.config.get("include_titles", DEFAULT_ANALYST_INCLUDE_TITLES)
        exclude_titles = source.config.get("exclude_titles", DEFAULT_ANALYST_EXCLUDE_TITLES)

        existing_external_ids: set[str] = set(
            db.scalars(select(JobRaw.external_job_id).where(JobRaw.source == source.name))
        )

        for raw_job in raw_jobs:
            normalized = adapter.normalize_job(raw_job)
            if not is_relevant_analyst_role(
                normalized.title,
                include_titles=include_titles,
                exclude_titles=exclude_titles,
            ):
                skipped_irrelevant += 1
                continue

            external_id = normalized.external_job_id or adapter.dedupe_key(raw_job)
            if external_id in existing_external_ids:
                continue

            db.add(JobRaw(source=source.name, external_job_id=external_id, raw_payload=raw_job))
            existing_external_ids.add(external_id)
            stored += 1

        source.last_run_at = datetime.now(timezone.utc)
        source.last_error = None
        db.commit()
        db.refresh(source)
    except Exception as exc:
        error = str(exc)
        source.last_run_at = datetime.now(timezone.utc)
        source.last_error = error
        db.commit()
        db.refresh(source)
        log_event(logging.WARNING, "admin.source.run.failed", source_id=source_id, error=error)

    duration_ms = int((time.perf_counter() - started) * 1000)
    log_event(
        logging.INFO,
        "admin.source.run.completed",
        source_id=source_id,
        source_name=source.name,
        stored=stored,
        skipped_irrelevant=skipped_irrelevant,
        duration_ms=duration_ms,
        error=error,
    )
    return SourceRunResult(
        source_id=source.id,
        source_name=source.name,
        success=error is None,
        raw_jobs_stored=stored,
        jobs_skipped_irrelevant=skipped_irrelevant,
        error=error,
        duration_ms=duration_ms,
    )


# ── Per-source roll-up stats ─────────────────────────────────────────────────

def source_stats(db: Session) -> dict[str, dict[str, int]]:
    """
    Return {source_name: {total, last_24h, last_7d}} for every source name
    that has ever produced a JobRaw row. The Sources list endpoint merges
    these counts with the JobSource rows.
    """
    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)

    totals = {
        row.source: row.cnt
        for row in db.execute(
            select(JobRaw.source, func.count(JobRaw.id).label("cnt")).group_by(JobRaw.source)
        ).all()
    }
    last_24h = {
        row.source: row.cnt
        for row in db.execute(
            select(JobRaw.source, func.count(JobRaw.id).label("cnt"))
            .where(JobRaw.fetched_at >= cutoff_24h)
            .group_by(JobRaw.source)
        ).all()
    }
    last_7d = {
        row.source: row.cnt
        for row in db.execute(
            select(JobRaw.source, func.count(JobRaw.id).label("cnt"))
            .where(JobRaw.fetched_at >= cutoff_7d)
            .group_by(JobRaw.source)
        ).all()
    }

    out: dict[str, dict[str, int]] = {}
    for name, total in totals.items():
        out[name] = {
            "total": int(total),
            "last_24h": int(last_24h.get(name, 0)),
            "last_7d": int(last_7d.get(name, 0)),
        }
    return out
