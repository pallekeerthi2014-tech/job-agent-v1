from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Source CRUD schemas ──────────────────────────────────────────────────────

class SourceBase(BaseModel):
    """Fields shared by create/update/read for a JobSource."""

    name: str = Field(min_length=1, max_length=255)
    adapter_type: str = Field(min_length=1, max_length=100)
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    """All fields optional — partial update."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    adapter_type: str | None = Field(default=None, min_length=1, max_length=100)
    config: dict[str, Any] | None = None
    enabled: bool | None = None


class SourceRead(SourceBase):
    """Source as returned to admins. Excludes raw config secrets in future phases."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    last_run_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime

    # Roll-up stats — populated by the service layer (NOT a DB column).
    jobs_total: int | None = None
    jobs_last_24h: int | None = None
    jobs_last_7d: int | None = None


# ── Test connection / Run now ────────────────────────────────────────────────

class SourceJobSample(BaseModel):
    """A trimmed-down preview of a single job returned by Test Connection."""

    title: str
    company: str | None = None
    location: str | None = None
    apply_url: str | None = None
    posted_date: str | None = None
    external_job_id: str | None = None


class SourceTestResult(BaseModel):
    """Result of running an adapter once with a given config (no DB writes)."""

    success: bool
    adapter_type: str
    raw_jobs_returned: int = 0
    sample_jobs: list[SourceJobSample] = Field(default_factory=list)
    error: str | None = None
    duration_ms: int


class SourceRunResult(BaseModel):
    """Result of running ingestion for a single source (with DB writes)."""

    source_id: int
    source_name: str
    success: bool
    raw_jobs_stored: int = 0
    jobs_skipped_irrelevant: int = 0
    error: str | None = None
    duration_ms: int


# ── Adapter form-schema metadata ─────────────────────────────────────────────

FieldType = Literal[
    "string",
    "url",
    "secret",
    "number",
    "boolean",
    "string_list",
    "object",
]


class AdapterFieldSchema(BaseModel):
    """One configurable field on an adapter's `config` dict."""

    name: str
    label: str
    type: FieldType = "string"
    required: bool = False
    description: str | None = None
    placeholder: str | None = None
    default: Any | None = None
    options: list[str] | None = None  # for select-style fields


class AdapterTypeMeta(BaseModel):
    """Describes one entry in ADAPTER_REGISTRY so the frontend can render a form."""

    adapter_type: str
    label: str
    category: str  # "API" | "ATS" | "Career Page" | "RSS" | "File"
    description: str
    fields: list[AdapterFieldSchema]


class AdapterTypeList(BaseModel):
    types: list[AdapterTypeMeta]


# ── Misc request bodies ──────────────────────────────────────────────────────

class SourceTestRequest(BaseModel):
    """Body for POST /admin/sources/test — dry-run an adapter config."""

    adapter_type: str
    config: dict[str, Any] = Field(default_factory=dict)
