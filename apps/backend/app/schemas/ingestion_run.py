from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IngestionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    source_name: str
    started_at: datetime
    completed_at: datetime | None = None
    status: str  # "success" | "error"
    raw_fetched: int
    raw_stored: int
    jobs_skipped: int
    error_message: str | None = None


class IngestionRunPage(BaseModel):
    items: list[IngestionRunRead]
    total: int


class SourceHealthRead(BaseModel):
    """Aggregated health snapshot for a single source."""
    source_id: int
    source_name: str
    enabled: bool
    last_run_at: datetime | None = None
    last_successful_run_at: datetime | None = None
    last_error: str | None = None
    # "healthy" | "warning" | "critical" | "paused"
    health_status: str
    recent_error_rate: float  # fraction 0.0–1.0 based on last 5 runs
    runs_last_24h: int
