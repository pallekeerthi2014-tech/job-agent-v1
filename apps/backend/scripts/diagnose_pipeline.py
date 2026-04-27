"""
diagnose_pipeline.py — Step-by-step pipeline health check

Prints a table showing exactly how many records exist at each stage
without modifying any data. Run this when the dashboard shows 0 jobs.

Usage (inside Docker):
    docker compose exec backend python scripts/diagnose_pipeline.py

Usage (local):
    cd apps/backend
    python scripts/diagnose_pipeline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from dotenv import load_dotenv
    _here = Path(__file__).resolve()
    for _parent in _here.parents:
        if (_parent / ".env").exists():
            load_dotenv(_parent / ".env")
            break
except Exception:
    pass


def main() -> None:
    from sqlalchemy import func, select, text
    from app.db.session import SessionLocal
    from app.models.job import JobRaw, JobNormalized
    from app.models.candidate import Candidate
    from app.models.match_score import JobCandidateMatch
    from app.models.work_queue import EmployeeWorkQueue
    from app.models.source import JobSource
    from app.models.employee import Employee

    db = SessionLocal()
    print("\n══════════════════════════════════════════════")
    print("  ThinkSuccess Pipeline Diagnostics")
    print("══════════════════════════════════════════════\n")

    try:
        # ── Sources ───────────────────────────────────────
        sources = list(db.scalars(select(JobSource)))
        enabled = [s for s in sources if s.enabled]
        print(f"  Job Sources      : {len(sources)} total, {len(enabled)} enabled")
        for s in sources:
            status = "✓ enabled" if s.enabled else "  disabled"
            last_run = str(s.last_run_at)[:19] if s.last_run_at else "never"
            err = f"  ⚠ {s.last_error[:60]}" if s.last_error else ""
            print(f"    {status}  {s.name}  (last run: {last_run}){err}")

        # ── Raw jobs ──────────────────────────────────────
        raw_count = db.scalar(select(func.count()).select_from(JobRaw))
        print(f"\n  Raw jobs stored  : {raw_count}")

        # By source
        raw_by_source = db.execute(
            select(JobRaw.source, func.count().label("n"))
            .group_by(JobRaw.source)
            .order_by(func.count().desc())
        ).all()
        for src, n in raw_by_source:
            print(f"    {n:4d}  {src}")

        # ── Normalized jobs ───────────────────────────────
        norm_count  = db.scalar(select(func.count()).select_from(JobNormalized))
        recent      = db.scalar(select(func.count()).select_from(JobNormalized).where(JobNormalized.freshness_status == "verified_recent"))
        stale       = db.scalar(select(func.count()).select_from(JobNormalized).where(JobNormalized.freshness_status == "verified_stale"))
        unverified  = db.scalar(select(func.count()).select_from(JobNormalized).where(JobNormalized.freshness_status == "unverified"))
        active      = db.scalar(select(func.count()).select_from(JobNormalized).where(JobNormalized.is_active.is_(True)))
        print(f"\n  Normalized jobs  : {norm_count} total, {active} active")
        print(f"    verified_recent : {recent}   ← these are scored against candidates")
        print(f"    verified_stale  : {stale}   ← too old (>{_max_age()} hours)")
        print(f"    unverified      : {unverified}  ← no parseable date found")

        # By source
        norm_by_source = db.execute(
            select(JobNormalized.source, func.count().label("n"))
            .group_by(JobNormalized.source)
            .order_by(func.count().desc())
        ).all()
        for src, n in norm_by_source:
            print(f"    {n:4d}  {src}")

        # Sample recent jobs
        sample = list(db.scalars(
            select(JobNormalized)
            .where(JobNormalized.freshness_status == "verified_recent")
            .order_by(JobNormalized.id.desc())
            .limit(5)
        ))
        if sample:
            print(f"\n  Sample recent jobs:")
            for j in sample:
                print(f"    [{j.posted_date}] {j.title[:50]} @ {j.company[:30]}  src={j.source}")

        # ── Candidates ────────────────────────────────────
        cand_count = db.scalar(select(func.count()).select_from(Candidate))
        active_cands = db.scalar(select(func.count()).select_from(Candidate).where(Candidate.active.is_(True)))
        print(f"\n  Candidates       : {cand_count} total, {active_cands} active")
        if cand_count == 0:
            print("    ⚠  No candidates! Set SEED_SAMPLE_CANDIDATES=true and restart.")

        # ── Employees ─────────────────────────────────────
        emp_count = db.scalar(select(func.count()).select_from(Employee))
        print(f"  Employees        : {emp_count}")

        # ── Matches ───────────────────────────────────────
        match_count = db.scalar(select(func.count()).select_from(JobCandidateMatch))
        high = db.scalar(select(func.count()).select_from(JobCandidateMatch).where(JobCandidateMatch.status == "High"))
        med  = db.scalar(select(func.count()).select_from(JobCandidateMatch).where(JobCandidateMatch.status == "Medium"))
        print(f"\n  Match pairs      : {match_count} (High: {high}, Medium: {med})")
        if match_count == 0 and cand_count > 0 and recent > 0:
            print("    ⚠  Jobs and candidates exist but no matches — run the pipeline.")

        # ── Work queue ────────────────────────────────────
        queue_count = db.scalar(select(func.count()).select_from(EmployeeWorkQueue))
        pending     = db.scalar(select(func.count()).select_from(EmployeeWorkQueue).where(EmployeeWorkQueue.status == "pending"))
        print(f"  Work queue items : {queue_count} total, {pending} pending")

        # ── Verdict ───────────────────────────────────────
        print("\n  ── Verdict ─────────────────────────────────")
        ok = True
        if len(enabled) == 0:
            print("  ✗  No sources enabled — nothing will be ingested.")
            ok = False
        if raw_count == 0:
            print("  ✗  No raw jobs — pipeline has never run or all sources failed.")
            ok = False
        if norm_count == 0:
            print("  ✗  Normalization has not run yet.")
            ok = False
        if recent == 0 and norm_count > 0:
            print(f"  ✗  All {norm_count} normalized jobs are stale or unverified — check posted dates.")
            ok = False
        if cand_count == 0:
            print("  ✗  No candidates seeded — SEED_SAMPLE_CANDIDATES must be true.")
            ok = False
        if match_count == 0 and recent > 0 and cand_count > 0:
            print("  ✗  No matches scored — run: docker compose exec backend python scripts/run_phase2_pipeline.py")
            ok = False
        if queue_count == 0 and match_count > 0:
            print("  ✗  No work queue items — run_phase2_pipeline.py should create them.")
            ok = False
        if ok:
            print("  ✓  Pipeline looks healthy. Dashboard should show jobs.")
        print()

    finally:
        db.close()


def _max_age() -> int:
    try:
        from app.core.config import settings
        return settings.fresh_job_max_age_hours
    except Exception:
        return 168


if __name__ == "__main__":
    main()
