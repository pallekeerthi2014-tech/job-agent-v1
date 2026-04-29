"""
Form-schema metadata for each adapter type.

The frontend admin "Add Source" wizard renders type-specific forms by reading
this metadata. To make a new adapter type configurable in the UI:
  1. Add its class + entry in ADAPTER_REGISTRY.
  2. Add its form schema here.

Each schema describes the keys that go into JobSource.config for that adapter.
The frontend should send config values that match this schema.
"""
from __future__ import annotations

from app.schemas.source import AdapterFieldSchema, AdapterTypeMeta


# ── Reusable filter field group ──────────────────────────────────────────────
# include_titles / exclude_titles are the standard filtering pattern shared by
# most adapters. Define once, reuse.

_INCLUDE_TITLES = AdapterFieldSchema(
    name="include_titles",
    label="Include titles (any match)",
    type="string_list",
    required=False,
    description="A job title must contain at least one of these substrings (case-insensitive). Leave empty to use the platform defaults for analyst roles.",
    placeholder="business analyst, healthcare analyst, ...",
)
_EXCLUDE_TITLES = AdapterFieldSchema(
    name="exclude_titles",
    label="Exclude titles (any match drops the job)",
    type="string_list",
    required=False,
    description="If a title contains any of these substrings the job is skipped. Defaults exclude software engineer, devops, marketing analyst, etc.",
    placeholder="software engineer, devops, ...",
)


# ── Per-adapter schemas ──────────────────────────────────────────────────────

GREENHOUSE_BOARD = AdapterTypeMeta(
    adapter_type="greenhouse_board",
    label="Greenhouse job board",
    category="ATS",
    description="Pulls public jobs from a company's Greenhouse board JSON API. Fast, reliable, no auth.",
    fields=[
        AdapterFieldSchema(
            name="board_token",
            label="Greenhouse board token",
            type="string",
            required=True,
            description="The slug Greenhouse uses to identify the company. Example: greenhouse.io/cloverhealth → board_token = cloverhealth.",
            placeholder="cloverhealth",
        ),
        AdapterFieldSchema(
            name="company_name",
            label="Company name (display)",
            type="string",
            required=True,
            placeholder="Clover Health",
        ),
        _INCLUDE_TITLES,
        _EXCLUDE_TITLES,
    ],
)

LEVER_POSTINGS = AdapterTypeMeta(
    adapter_type="lever_postings",
    label="Lever postings",
    category="ATS",
    description="Pulls public jobs from a company's Lever postings JSON API. Format: api.lever.co/v0/postings/{handle}.",
    fields=[
        AdapterFieldSchema(
            name="company_handle",
            label="Lever company handle",
            type="string",
            required=True,
            description="The handle in api.lever.co/v0/postings/{handle}. Example: 'netflix'.",
            placeholder="example-company",
        ),
        AdapterFieldSchema(
            name="company_name",
            label="Company name (display)",
            type="string",
            required=True,
            placeholder="Example Company",
        ),
        _INCLUDE_TITLES,
        _EXCLUDE_TITLES,
    ],
)

WORKDAY_JOBS = AdapterTypeMeta(
    adapter_type="workday_jobs",
    label="Workday jobs feed",
    category="ATS",
    description="Pulls jobs from a Workday-hosted careers site via its CXS JSON endpoint.",
    fields=[
        AdapterFieldSchema(
            name="url",
            label="Workday CXS endpoint",
            type="url",
            required=True,
            description="The internal jobs endpoint, usually ends in /wday/cxs/{tenant}/{site}/jobs.",
            placeholder="https://example.myworkdayjobs.com/wday/cxs/example/careers/jobs",
        ),
        AdapterFieldSchema(
            name="job_url_prefix",
            label="Job URL prefix",
            type="url",
            required=True,
            description="Prefix used to build apply URLs from each job's external path.",
            placeholder="https://example.myworkdayjobs.com/en-US/careers",
        ),
        AdapterFieldSchema(
            name="company_name",
            label="Company name (display)",
            type="string",
            required=True,
            placeholder="Example Company",
        ),
        _INCLUDE_TITLES,
        _EXCLUDE_TITLES,
    ],
)

GENERIC_ATS_JSON = AdapterTypeMeta(
    adapter_type="generic_ats_json",
    label="Generic JSON file feed",
    category="File",
    description="Reads jobs from a static JSON file already on the server (under /app/seed-data/). Useful for static testing or curated lists.",
    fields=[
        AdapterFieldSchema(
            name="path",
            label="JSON file path on server",
            type="string",
            required=True,
            description="Absolute path inside the container. Example: /app/seed-data/job_feed.json.",
            placeholder="/app/seed-data/recent_healthcare_analyst_jobs.json",
        ),
        _INCLUDE_TITLES,
        _EXCLUDE_TITLES,
    ],
)

GENERIC_HTML_CAREERS = AdapterTypeMeta(
    adapter_type="generic_html_careers",
    label="HTML careers page (CSS selectors)",
    category="Career Page",
    description="Scrapes a static HTML careers page using CSS selectors. Best for sites without an API.",
    fields=[
        AdapterFieldSchema(name="url", label="Careers page URL", type="url", required=True, placeholder="https://careers.example.com/"),
        AdapterFieldSchema(name="company_name", label="Company name (display)", type="string", required=True, placeholder="Example Company"),
        AdapterFieldSchema(name="job_selector", label="Job-row CSS selector", type="string", required=True, placeholder="job-list-item"),
        AdapterFieldSchema(name="title_selector", label="Title CSS selector", type="string", required=True, placeholder="job-title"),
        AdapterFieldSchema(name="location_selector", label="Location CSS selector", type="string", required=False, placeholder="job-location"),
        AdapterFieldSchema(name="link_selector", label="Apply-link CSS selector", type="string", required=False, placeholder="job-link"),
        AdapterFieldSchema(name="posted_selector", label="Posted-date CSS selector", type="string", required=False, placeholder="date-posted"),
        AdapterFieldSchema(
            name="default_employment_type",
            label="Default employment type",
            type="string",
            required=False,
            default="full-time",
            options=["full-time", "part-time", "contract", "temporary", "internship"],
        ),
        _INCLUDE_TITLES,
        _EXCLUDE_TITLES,
    ],
)

LIVE_FEED = AdapterTypeMeta(
    adapter_type="live_feed",
    label="Aggregated live feed (TheMuse + Arbeitnow + RemoteOK + USAJobs)",
    category="API",
    description="Polls multiple public job APIs in one source. Toggle each provider on/off. Best single-source for getting jobs flowing.",
    fields=[
        AdapterFieldSchema(name="enable_themuse", label="Enable TheMuse", type="boolean", required=False, default=True),
        AdapterFieldSchema(name="themuse_query", label="TheMuse search query", type="string", required=False, placeholder="Business Analyst"),
        AdapterFieldSchema(name="themuse_category", label="TheMuse category", type="string", required=False, placeholder="Data and Analytics"),
        AdapterFieldSchema(name="enable_arbeitnow", label="Enable Arbeitnow", type="boolean", required=False, default=True),
        AdapterFieldSchema(name="arbeitnow_query", label="Arbeitnow query", type="string", required=False, placeholder="healthcare business analyst"),
        AdapterFieldSchema(name="enable_remoteok", label="Enable RemoteOK", type="boolean", required=False, default=True),
        AdapterFieldSchema(name="remoteok_tag", label="RemoteOK tag", type="string", required=False, placeholder="healthcare"),
        AdapterFieldSchema(
            name="enable_usajobs",
            label="Enable USAJobs",
            type="boolean",
            required=False,
            default=False,
            description="Requires USAJOBS_API_KEY env var on the server. Leave off if not configured.",
        ),
        _INCLUDE_TITLES,
        _EXCLUDE_TITLES,
    ],
)

CONFIGURABLE_TEMPLATE = AdapterTypeMeta(
    adapter_type="configurable_template",
    label="Configurable template (advanced)",
    category="API",
    description="A power-user adapter that maps generic API responses into job records. Use when the source has a custom JSON schema you can describe with field paths.",
    fields=[
        AdapterFieldSchema(name="url", label="API URL", type="url", required=True),
        AdapterFieldSchema(name="company_name", label="Company name (display)", type="string", required=False),
        AdapterFieldSchema(
            name="response_path",
            label="JSON path to job array",
            type="string",
            required=False,
            description="Dotted path inside the response that holds the job list. Empty means the response IS a list.",
            placeholder="data.jobs",
        ),
        AdapterFieldSchema(name="title_field", label="Title field path", type="string", required=False, placeholder="title"),
        AdapterFieldSchema(name="location_field", label="Location field path", type="string", required=False, placeholder="location.name"),
        AdapterFieldSchema(name="url_field", label="Apply URL field path", type="string", required=False, placeholder="absolute_url"),
        AdapterFieldSchema(name="external_id_field", label="External ID field path", type="string", required=False, placeholder="id"),
        _INCLUDE_TITLES,
        _EXCLUDE_TITLES,
    ],
)


# ── Public registry ──────────────────────────────────────────────────────────

ADAPTER_FORM_SCHEMAS: dict[str, AdapterTypeMeta] = {
    GREENHOUSE_BOARD.adapter_type: GREENHOUSE_BOARD,
    LEVER_POSTINGS.adapter_type: LEVER_POSTINGS,
    WORKDAY_JOBS.adapter_type: WORKDAY_JOBS,
    LIVE_FEED.adapter_type: LIVE_FEED,
    GENERIC_HTML_CAREERS.adapter_type: GENERIC_HTML_CAREERS,
    GENERIC_ATS_JSON.adapter_type: GENERIC_ATS_JSON,
    CONFIGURABLE_TEMPLATE.adapter_type: CONFIGURABLE_TEMPLATE,
}


def get_adapter_form_schemas() -> list[AdapterTypeMeta]:
    """Return the form-schema metadata for every adapter the UI can configure."""
    return list(ADAPTER_FORM_SCHEMAS.values())


def get_adapter_form_schema(adapter_type: str) -> AdapterTypeMeta | None:
    return ADAPTER_FORM_SCHEMAS.get(adapter_type)
