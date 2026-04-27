from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.candidate import Candidate
from app.models.job import JobNormalized
from app.models.match_score import JobCandidateMatch
from app.scoring.engine import enrich_with_ai_explanation, score_candidate_to_job

_AI_ENABLED = os.getenv("AI_SCORING_ENABLED", "false").lower() == "true"


def score_job_candidate_matches(db: Session) -> int:
    candidates = list(
        db.execute(
            select(Candidate)
            .options(joinedload(Candidate.preference), joinedload(Candidate.skills))
            .where(Candidate.active.is_(True))
        )
        .unique()
        .scalars()
    )
    jobs = list(
        db.scalars(
            select(JobNormalized).where(
                JobNormalized.is_active.is_(True),
                JobNormalized.freshness_status == "verified_recent",
            )
        )
    )
    scored = 0

    for candidate in candidates:
        for job in jobs:
            result = score_candidate_to_job(candidate, job)
            # Phase 2: AI enrichment — writes ai_summary into explanation field
            if _AI_ENABLED:
                result = enrich_with_ai_explanation(result, candidate, job)
                if result.ai_summary:
                    from dataclasses import replace as _replace
                    result = _replace(result, explanation=result.ai_summary)
            existing = db.scalar(
                select(JobCandidateMatch).where(
                    JobCandidateMatch.candidate_id == candidate.id,
                    JobCandidateMatch.job_id == job.id,
                )
            )

            values = {
                "score": result.total_score,
                "priority": _priority_rank(result.priority_bucket),
                "title_score": result.title_score,
                "domain_score": result.domain_score,
                "skills_score": result.skills_score,
                "experience_score": result.experience_score,
                "employment_preference_score": result.employment_preference_score,
                "visa_score": result.visa_score,
                "location_score": result.location_score,
                "explanation": result.explanation,
                "status": result.priority_bucket,
            }

            if existing:
                for key, value in values.items():
                    setattr(existing, key, value)
            else:
                db.add(
                    JobCandidateMatch(
                        job_id=job.id,
                        candidate_id=candidate.id,
                        **values,
                    )
                )
            scored += 1

    db.commit()
    return scored


def _priority_rank(priority_bucket: str) -> int:
    return {"High": 1, "Medium": 2, "Low": 3}[priority_bucket]
