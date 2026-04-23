from __future__ import annotations

from typing import Any

from app.services.source_adapters.ats_json import GenericATSJsonFeedAdapter
from app.services.source_adapters.base import JobSourceAdapter
from app.services.source_adapters.greenhouse import GreenhouseBoardAdapter
from app.services.source_adapters.html_careers import GenericHTMLCareersPageAdapter
from app.services.source_adapters.lever import LeverPostingsAdapter
from app.services.source_adapters.template import ConfigurableSourceAdapterTemplate
from app.services.source_adapters.workday import WorkdayJobsAdapter


ADAPTER_REGISTRY: dict[str, type[JobSourceAdapter]] = {
    "generic_ats_json": GenericATSJsonFeedAdapter,
    "generic_html_careers": GenericHTMLCareersPageAdapter,
    "configurable_template": ConfigurableSourceAdapterTemplate,
    "greenhouse_board": GreenhouseBoardAdapter,
    "lever_postings": LeverPostingsAdapter,
    "workday_jobs": WorkdayJobsAdapter,
}


def build_source_adapter(adapter_type: str, source_name: str, config: dict[str, Any] | None = None) -> JobSourceAdapter:
    try:
        adapter_cls = ADAPTER_REGISTRY[adapter_type]
    except KeyError as exc:
        supported = ", ".join(sorted(ADAPTER_REGISTRY))
        raise ValueError(f"Unsupported adapter '{adapter_type}'. Supported adapters: {supported}") from exc
    return adapter_cls(source_name=source_name, config=config)
