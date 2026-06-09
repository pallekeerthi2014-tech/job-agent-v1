from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr


class CandidateMailboxCreate(BaseModel):
    candidate_id: int
    email: EmailStr


class CandidateMailboxRead(BaseModel):
    id: int
    candidate_id: int
    email: str
    status: str
    gmail_connected: bool
    calendar_connected: bool
    last_email_scan_at: datetime | None
    last_calendar_scan_at: datetime | None
    last_successful_scan_at: datetime | None
    last_error: str | None

    model_config = {"from_attributes": True}


class ForwardingScanTarget(BaseModel):
    candidate_id: int
    candidate_name: str
    candidate_email: str


class ForwardedGmailEvent(BaseModel):
    candidate_email: EmailStr
    last_email_received_at: datetime | None = None
    message_id: str | None = None
    subject: str | None = None
    sender: str | None = None
    email_count_7_days: int = 0


class ForwardingScanPayload(BaseModel):
    events: list[ForwardedGmailEvent]


class ForwardingScanResponse(BaseModel):
    received: int
    updated: int
    missing: list[str]


class GmailOAuthUrlResponse(BaseModel):
    candidate_id: int
    authorization_url: str


class GmailAnalyticsRunResponse(BaseModel):
    mailboxes_scanned: int
    email_events_created: int
    calendar_events_upserted: int
    sheets_published: bool
    failures: int
