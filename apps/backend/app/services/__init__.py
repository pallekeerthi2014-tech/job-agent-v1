from app.services.source_adapters import (
    ConfigurableSourceAdapterTemplate,
    GenericATSJsonFeedAdapter,
    GenericHTMLCareersPageAdapter,
    GreenhouseBoardAdapter,
    JobRecord,
    JobSourceAdapter,
    LeverPostingsAdapter,
    WorkdayJobsAdapter,
)
from app.services.ingestion import fetch_jobs_from_enabled_sources
from app.services.normalization import JobNormalizationService, normalize_jobs
from app.services.dedupe import JobDedupeService, mark_probable_duplicates
from app.services.matching import score_job_candidate_matches
from app.services.pipeline import PipelineRunSummary, run_daily_pipeline
from app.services.work_queue import create_employee_work_queues

__all__ = [
    "ConfigurableSourceAdapterTemplate",
    "GenericATSJsonFeedAdapter",
    "GenericHTMLCareersPageAdapter",
    "GreenhouseBoardAdapter",
    "JobDedupeService",
    "JobNormalizationService",
    "JobRecord",
    "JobSourceAdapter",
    "LeverPostingsAdapter",
    "WorkdayJobsAdapter",
    "PipelineRunSummary",
    "create_employee_work_queues",
    "fetch_jobs_from_enabled_sources",
    "mark_probable_duplicates",
    "normalize_jobs",
    "run_daily_pipeline",
    "score_job_candidate_matches",
]
