from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import JobNormalized
from app.parsers.normalizer import canonicalize_apply_url, normalized_description_content_hash


@dataclass(slots=True)
class DedupeResult:
    active_job_id: int
    duplicate_job_ids: list[int]
    reason: str


class JobDedupeService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def mark_probable_duplicates(self) -> list[DedupeResult]:
        jobs = list(self.db.scalars(select(JobNormalized).order_by(JobNormalized.posted_date.desc().nullslast(), JobNormalized.id.asc())))
        results: list[DedupeResult] = []

        self._reset_dedupe_state(jobs)

        comparison_groups = [
            ("canonical_apply_url", self._group_by_canonical_apply_url(jobs)),
            ("title_company_location", self._group_by_title_company_location(jobs)),
            ("normalized_description_hash", self._group_by_description_hash(jobs)),
        ]

        for reason, grouped_jobs in comparison_groups:
            for group in grouped_jobs:
                if len(group) < 2:
                    continue
                result = self._mark_group_duplicates(group, reason)
                if result:
                    results.append(result)

        self.db.commit()
        return results

    def _reset_dedupe_state(self, jobs: list[JobNormalized]) -> None:
        for job in jobs:
            job.is_active = True
            job.probable_duplicate_of_job_id = None
            job.duplicate_reasons = []

    def _group_by_canonical_apply_url(self, jobs: list[JobNormalized]) -> list[list[JobNormalized]]:
        grouped: dict[str, list[JobNormalized]] = defaultdict(list)
        for job in jobs:
            canonical_url = job.canonical_apply_url or canonicalize_apply_url(job.apply_url)
            if canonical_url:
                grouped[canonical_url].append(job)
        return list(grouped.values())

    def _group_by_title_company_location(self, jobs: list[JobNormalized]) -> list[list[JobNormalized]]:
        grouped: dict[str, list[JobNormalized]] = defaultdict(list)
        for job in jobs:
            key = "|".join(
                [
                    job.title.strip().lower(),
                    job.company.strip().lower(),
                    (job.location or "").strip().lower(),
                ]
            )
            grouped[key].append(job)
        return list(grouped.values())

    def _group_by_description_hash(self, jobs: list[JobNormalized]) -> list[list[JobNormalized]]:
        grouped: dict[str, list[JobNormalized]] = defaultdict(list)
        for job in jobs:
            content_hash = job.normalized_description_hash or normalized_description_content_hash(job.description)
            if content_hash:
                grouped[content_hash].append(job)
        return list(grouped.values())

    def _mark_group_duplicates(self, jobs: list[JobNormalized], reason: str) -> DedupeResult | None:
        active_job = self._select_primary_record(jobs)
        duplicate_ids: list[int] = []

        for job in jobs:
            if job.id == active_job.id:
                job.is_active = True
                continue

            if job.probable_duplicate_of_job_id is None:
                job.probable_duplicate_of_job_id = active_job.id
                job.is_active = False
            if reason not in job.duplicate_reasons:
                job.duplicate_reasons = sorted(set([*job.duplicate_reasons, reason]))

            duplicate_ids.append(job.id)

        if not duplicate_ids:
            return None

        return DedupeResult(
            active_job_id=active_job.id,
            duplicate_job_ids=duplicate_ids,
            reason=reason,
        )

    def _select_primary_record(self, jobs: list[JobNormalized]) -> JobNormalized:
        return min(
            jobs,
            key=lambda job: (
                0 if job.posted_date is not None else 1,
                -(job.posted_date.toordinal() if job.posted_date is not None else 0),
                0 if job.canonical_apply_url else 1,
                job.id,
            ),
        )


def mark_probable_duplicates(db: Session) -> list[DedupeResult]:
    return JobDedupeService(db).mark_probable_duplicates()
