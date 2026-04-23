from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class JobRecord:
    source: str
    title: str
    company: str
    location: str | None = None
    is_remote: bool = False
    employment_type: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    posted_date: str | None = None
    apply_url: str | None = None
    description: str | None = None
    domain_tags: list[str] = field(default_factory=list)
    visa_hints: list[str] = field(default_factory=list)
    keywords_extracted: list[str] = field(default_factory=list)
    external_job_id: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


class JobSourceAdapter(ABC):
    def __init__(self, source_name: str, config: dict[str, Any] | None = None) -> None:
        self.source_name = source_name
        self.config = config or {}

    @abstractmethod
    def fetch_jobs(self) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def normalize_job(self, raw_job: dict[str, Any]) -> JobRecord:
        pass

    @abstractmethod
    def dedupe_key(self, raw_job: dict[str, Any]) -> str:
        pass

