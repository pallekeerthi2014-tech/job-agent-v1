"""
run_phase2_pipeline.py — Manually trigger the Phase 2 real-time pipeline (Phase 2)

Use this to test the pipeline immediately without waiting for the 15-minute
scheduler interval. Runs the full cycle: ingest → normalize → dedupe → score
→ dispatch WhatsApp + email alerts for new high-scoring matches.

Usage (inside Docker):
    docker-compose exec backend python scripts/run_phase2_pipeline.py

Usage (local):
    cd apps/backend
    python scripts/run_phase2_pipeline.py

Options:
    --dry-run   Run the pipeline but skip sending any alerts (safe for testing)
    --verbose   Print detailed output for each pipeline step
"""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Load .env if running locally (Docker already injects env vars so this is a no-op there)
try:
    from dotenv import load_dotenv
    _here = Path(__file__).resolve()
    for _parent in _here.parents:
        _candidate = _parent / ".env"
        if _candidate.exists():
            load_dotenv(_candidate)
            break
except Exception:
    pass

dry_run = "--dry-run" in sys.argv
verbose = "--verbose" in sys.argv

log_level = logging.DEBUG if verbose else logging.INFO
logging.basicConfig(level=log_level, format="%(asctime)s  %(levelname)-7s  %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    print("\n── ThinkSuccess Phase 2 Pipeline — Manual Run ──")
    if dry_run:
        print("   DRY RUN: alerts will be skipped\n")
    else:
        print()

    if dry_run:
        # Temporarily disable alert channels so nothing fires
        os.environ["WHATSAPP_ALERTS_ENABLED"] = "false"
        os.environ["EMAIL_ALERTS_ENABLED"]    = "false"

    from app.db.session import SessionLocal
    from app.services.dedupe import mark_probable_duplicates
    from app.services.ingestion import fetch_jobs_from_enabled_sources
    from app.services.matching import score_job_candidate_matches
    from app.services.normalization import normalize_jobs
    from app.services.work_queue import create_employee_work_queues
    from app.services.alert_service import dispatch_job_alerts
    from sqlalchemy import select
    from app.models.job import JobNormalized

    db = SessionLocal()
    try:
        # ── Step 1: Snapshot existing job IDs ────────────────────────────────
        existing_ids: set[int] = set(db.scalars(select(JobNormalized.id)))
        print(f"  Jobs already in DB:   {len(existing_ids)}")

        # ── Step 2: Ingest ────────────────────────────────────────────────────
        print("\n  [1/5] Fetching from live sources...")
        fetch_totals = fetch_jobs_from_enabled_sources(db)
        print(f"        Sources processed : {fetch_totals['sources_processed']}")
        print(f"        Raw jobs stored   : {fetch_totals['raw_jobs_stored']}")
        print(f"        Skipped irrelevant: {fetch_totals['jobs_skipped_irrelevant']}")
        if fetch_totals['source_failures']:
            print(f"        ⚠  Source failures : {fetch_totals['source_failures']}")

        # ── Step 3: Normalize ─────────────────────────────────────────────────
        print("\n  [2/5] Normalizing jobs...")
        normalized = normalize_jobs(db)
        print(f"        Normalized        : {normalized}")

        # ── Step 4: Deduplicate ───────────────────────────────────────────────
        print("\n  [3/5] Deduplicating...")
        dupes = mark_probable_duplicates(db)
        print(f"        Duplicate groups  : {len(dupes)}")

        # ── Step 5: Score ─────────────────────────────────────────────────────
        print("\n  [4/5] Scoring candidate × job matches...")
        scored = score_job_candidate_matches(db)
        print(f"        Match pairs scored: {scored}")

        # ── Step 6: Find new jobs ─────────────────────────────────────────────
        all_ids: set[int] = set(db.scalars(select(JobNormalized.id)))
        new_job_ids = list(all_ids - existing_ids)
        print(f"\n  New jobs this cycle   : {len(new_job_ids)}")

        # ── Step 7: Dispatch alerts ───────────────────────────────────────────
        print("\n  [5/5] Dispatching alerts...")
        if not new_job_ids:
            print("        No new jobs — nothing to alert on.")
        elif dry_run:
            print("        DRY RUN — alerts skipped.")
        else:
            alert_summary = dispatch_job_alerts(db, new_job_ids)
            print(f"        Matches evaluated : {alert_summary.matches_evaluated}")
            print(f"        WhatsApp sent     : {alert_summary.whatsapp_sent}")
            print(f"        Emails sent       : {alert_summary.email_sent}")
            if alert_summary.failed:
                print(f"        ⚠  Failed         : {alert_summary.failed}")

        # ── Step 8: Work queues ───────────────────────────────────────────────
        queue_items = create_employee_work_queues(db)
        print(f"\n  Work queue items      : {queue_items}")

        print("\n  ✓ Pipeline complete.\n")

    except Exception as exc:
        db.rollback()
        logger.exception("Pipeline failed: %s", exc)
        print(f"\n  ✗ Pipeline failed: {exc}\n")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
