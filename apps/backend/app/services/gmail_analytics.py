from __future__ import annotations

import logging
import hmac
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import google.auth
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import Flow
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.candidate import Candidate
from app.models.gmail_analytics import CandidateCalendarEvent, CandidateMailbox, DailyCandidateMetric, EmailEvent
from app.services.gmail_classifier import classify_email, is_interview_like_calendar_event
from app.services.google_token_crypto import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]
SHEETS_SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]


@dataclass
class GmailAnalyticsSummary:
    mailboxes_scanned: int = 0
    email_events_created: int = 0
    calendar_events_upserted: int = 0
    sheets_published: bool = False
    failures: int = 0


def build_candidate_oauth_url(*, candidate_id: int, state_prefix: str = "candidate") -> str:
    flow = _candidate_oauth_flow()
    state = _signed_state(candidate_id, state_prefix)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return auth_url


def exchange_candidate_oauth_code(db: Session, *, code: str, state: str) -> CandidateMailbox:
    candidate_id = _candidate_id_from_state(state)
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise ValueError(f"Candidate {candidate_id} was not found")

    flow = _candidate_oauth_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    session = AuthorizedSession(creds)
    profile = session.get("https://gmail.googleapis.com/gmail/v1/users/me/profile", timeout=20).json()
    email = (profile.get("emailAddress") or candidate.email or "").lower()
    if not email:
        raise ValueError("Google did not return an email address for this mailbox")

    mailbox = db.scalar(select(CandidateMailbox).where(CandidateMailbox.candidate_id == candidate_id))
    if mailbox is None:
        mailbox = CandidateMailbox(candidate_id=candidate_id, email=email)
        db.add(mailbox)

    mailbox.email = email
    mailbox.status = "connected"
    mailbox.gmail_connected = True
    mailbox.calendar_connected = True
    mailbox.access_token_encrypted = encrypt_token(creds.token)
    mailbox.refresh_token_encrypted = encrypt_token(creds.refresh_token)
    mailbox.token_uri = creds.token_uri or "https://oauth2.googleapis.com/token"
    mailbox.scopes = ",".join(creds.scopes or GMAIL_SCOPES)
    mailbox.token_expiry = creds.expiry
    mailbox.last_error = None
    mailbox.updated_at = _now()
    db.commit()
    db.refresh(mailbox)
    return mailbox


def run_gmail_analytics_cycle(db: Session, *, publish_sheets: bool = True) -> GmailAnalyticsSummary:
    summary = GmailAnalyticsSummary()
    mailboxes = list(db.scalars(select(CandidateMailbox).where(CandidateMailbox.status.in_(["connected", "error"]))))
    for mailbox in mailboxes:
        try:
            creds = _credentials_for_mailbox(mailbox)
            session = AuthorizedSession(creds)
            summary.email_events_created += _scan_mailbox_messages(db, session, mailbox)
            summary.calendar_events_upserted += _scan_calendar_events(db, session, mailbox)
            mailbox.status = "connected"
            mailbox.gmail_connected = True
            mailbox.calendar_connected = True
            mailbox.last_successful_scan_at = _now()
            mailbox.last_error = None
            _persist_refreshed_tokens(mailbox, creds)
            summary.mailboxes_scanned += 1
            db.commit()
        except Exception as exc:
            db.rollback()
            summary.failures += 1
            mailbox = db.get(CandidateMailbox, mailbox.id)
            if mailbox is not None:
                mailbox.status = "error"
                mailbox.last_error = str(exc)[:2000]
                mailbox.updated_at = _now()
                db.commit()
            logger.exception("gmail_analytics.mailbox_failed mailbox_id=%s", getattr(mailbox, "id", None))

    rebuild_daily_metrics(db)
    if publish_sheets and settings.google_sheets_report_id:
        publish_google_sheet_report(db)
        summary.sheets_published = True
    return summary


def rebuild_daily_metrics(db: Session, *, days: int = 30) -> int:
    start = _date_floor(_now() - timedelta(days=days))
    rows = list(db.scalars(select(Candidate).where(Candidate.active.is_(True))))
    count = 0
    for candidate in rows:
        for offset in range(days + 1):
            metric_date = start + timedelta(days=offset)
            next_date = metric_date + timedelta(days=1)
            events = list(
                db.scalars(
                    select(EmailEvent).where(
                        EmailEvent.candidate_id == candidate.id,
                        EmailEvent.received_at >= metric_date,
                        EmailEvent.received_at < next_date,
                    )
                )
            )
            mailbox = db.scalar(select(CandidateMailbox).where(CandidateMailbox.candidate_id == candidate.id))
            metric = db.scalar(
                select(DailyCandidateMetric).where(
                    DailyCandidateMetric.candidate_id == candidate.id,
                    DailyCandidateMetric.metric_date == metric_date,
                )
            )
            if metric is None:
                metric = DailyCandidateMetric(candidate_id=candidate.id, metric_date=metric_date)
                db.add(metric)
            metric.jobs_applied_detected = _count(events, "application_confirmation")
            metric.recruiter_replies = _count(events, "recruiter_reply")
            metric.interview_invites = _count(events, "interview_invite")
            metric.assessments = _count(events, "assessment")
            metric.rejections = _count(events, "rejection")
            metric.followups_required = sum(1 for event in events if event.action_required)
            metric.last_mailbox_scan_at = mailbox.last_successful_scan_at if mailbox else None
            metric.updated_at = _now()
            count += 1
    db.commit()
    return count


def publish_google_sheet_report(db: Session) -> None:
    creds = _sheets_credentials()
    session = AuthorizedSession(creds)
    spreadsheet_id = settings.google_sheets_report_id

    _ensure_sheet_tabs(session, spreadsheet_id)
    values = {
        "Daily Summary!A1": _daily_summary_rows(db),
        "Candidate Detail!A1": _candidate_detail_rows(db),
        "Upcoming Interviews!A1": _upcoming_interview_rows(db),
        "Mailbox Health!A1": _mailbox_health_rows(db),
    }
    body = {
        "valueInputOption": "RAW",
        "data": [{"range": sheet_range, "values": rows} for sheet_range, rows in values.items()],
    }
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate"
    response = session.post(url, json=body, timeout=30)
    response.raise_for_status()


def _scan_mailbox_messages(db: Session, session: AuthorizedSession, mailbox: CandidateMailbox) -> int:
    after = mailbox.last_email_scan_at or (_now() - timedelta(days=settings.gmail_scan_lookback_days))
    query = f"after:{after.strftime('%Y/%m/%d')}"
    list_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    response = session.get(list_url, params={"q": query, "maxResults": 100}, timeout=30)
    response.raise_for_status()
    created = 0
    for item in response.json().get("messages", []):
        message_id = item["id"]
        existing = db.scalar(
            select(EmailEvent.id).where(
                EmailEvent.mailbox_id == mailbox.id,
                EmailEvent.gmail_message_id == message_id,
            )
        )
        if existing:
            continue
        message = session.get(
            f"{list_url}/{message_id}",
            params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
            timeout=30,
        )
        message.raise_for_status()
        payload = message.json()
        headers = _headers(payload)
        sender = headers.get("from")
        subject = headers.get("subject")
        snippet = payload.get("snippet")
        classification = classify_email(sender=sender, subject=subject, snippet=snippet)
        received_at = _from_gmail_internal_date(payload.get("internalDate"))
        event = EmailEvent(
            mailbox_id=mailbox.id,
            candidate_id=mailbox.candidate_id,
            gmail_message_id=message_id,
            gmail_thread_id=payload.get("threadId"),
            received_at=received_at,
            sender=sender,
            subject=subject,
            snippet=snippet,
            detected_company=classification.detected_company,
            detected_role=classification.detected_role,
            category=classification.category,
            importance=classification.importance,
            action_required=classification.action_required,
            gmail_link=f"https://mail.google.com/mail/u/{mailbox.email}/#inbox/{message_id}",
        )
        db.add(event)
        created += 1
    mailbox.last_email_scan_at = _now()
    mailbox.updated_at = _now()
    return created


def _scan_calendar_events(db: Session, session: AuthorizedSession, mailbox: CandidateMailbox) -> int:
    now = _now()
    time_max = now + timedelta(days=settings.gmail_calendar_lookahead_days)
    response = session.get(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        params={
            "timeMin": now.isoformat(),
            "timeMax": time_max.isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 100,
        },
        timeout=30,
    )
    response.raise_for_status()
    upserted = 0
    for item in response.json().get("items", []):
        starts_at = _parse_event_time(item.get("start", {}))
        if starts_at is None:
            continue
        event = db.scalar(
            select(CandidateCalendarEvent).where(
                CandidateCalendarEvent.mailbox_id == mailbox.id,
                CandidateCalendarEvent.google_event_id == item["id"],
            )
        )
        if event is None:
            event = CandidateCalendarEvent(
                mailbox_id=mailbox.id,
                candidate_id=mailbox.candidate_id,
                google_event_id=item["id"],
                starts_at=starts_at,
            )
            db.add(event)
        event.title = item.get("summary")
        event.starts_at = starts_at
        event.ends_at = _parse_event_time(item.get("end", {}))
        event.organizer = (item.get("organizer") or {}).get("email")
        event.meeting_link = item.get("hangoutLink") or _conference_link(item)
        event.calendar_source = "primary"
        event.is_interview_like = is_interview_like_calendar_event(item.get("summary"), item.get("description"))
        event.updated_at = _now()
        upserted += 1
    mailbox.last_calendar_scan_at = _now()
    mailbox.updated_at = _now()
    return upserted


def _candidate_oauth_flow() -> Flow:
    if not settings.google_client_id or not settings.google_client_secret:
        raise RuntimeError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required")
    config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_oauth_redirect_uri],
        }
    }
    return Flow.from_client_config(
        config,
        scopes=GMAIL_SCOPES,
        redirect_uri=settings.google_oauth_redirect_uri,
        autogenerate_code_verifier=False,
    )


def _credentials_for_mailbox(mailbox: CandidateMailbox) -> Credentials:
    creds = Credentials(
        token=decrypt_token(mailbox.access_token_encrypted),
        refresh_token=decrypt_token(mailbox.refresh_token_encrypted),
        token_uri=mailbox.token_uri,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=(mailbox.scopes or ",".join(GMAIL_SCOPES)).split(","),
    )
    creds.expiry = _google_credentials_expiry(mailbox.token_expiry)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def _sheets_credentials() -> Any:
    if settings.google_service_account_json:
        info = json.loads(settings.google_service_account_json)
        return service_account.Credentials.from_service_account_info(info, scopes=SHEETS_SCOPE)
    creds, _ = google.auth.default(scopes=SHEETS_SCOPE)
    return creds


def _persist_refreshed_tokens(mailbox: CandidateMailbox, creds: Credentials) -> None:
    if creds.token:
        mailbox.access_token_encrypted = encrypt_token(creds.token)
    if creds.refresh_token:
        mailbox.refresh_token_encrypted = encrypt_token(creds.refresh_token)
    mailbox.token_expiry = creds.expiry
    mailbox.updated_at = _now()


def _google_credentials_expiry(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _ensure_sheet_tabs(session: AuthorizedSession, spreadsheet_id: str) -> None:
    meta_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    response = session.get(meta_url, timeout=30)
    response.raise_for_status()
    existing = {sheet["properties"]["title"] for sheet in response.json().get("sheets", [])}
    wanted = ["Daily Summary", "Candidate Detail", "Upcoming Interviews", "Mailbox Health"]
    requests = [{"addSheet": {"properties": {"title": title}}} for title in wanted if title not in existing]
    if requests:
        batch_url = f"{meta_url}:batchUpdate"
        batch_response = session.post(batch_url, json={"requests": requests}, timeout=30)
        batch_response.raise_for_status()
    clear_ranges = ",".join(wanted)
    clear_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchClear"
    session.post(clear_url, json={"ranges": wanted}, timeout=30).raise_for_status()


def _daily_summary_rows(db: Session) -> list[list[Any]]:
    rows: list[list[Any]] = [[
        "date", "candidate name", "candidate email", "jobs applied detected", "recruiter replies",
        "interview invites", "assessments", "rejections", "follow-ups required", "last mailbox scan",
    ]]
    stmt = (
        select(DailyCandidateMetric, Candidate)
        .join(Candidate, Candidate.id == DailyCandidateMetric.candidate_id)
        .where(DailyCandidateMetric.metric_date >= _date_floor(_now() - timedelta(days=14)))
        .order_by(DailyCandidateMetric.metric_date.desc(), Candidate.name.asc())
    )
    for metric, candidate in db.execute(stmt).all():
        rows.append([
            metric.metric_date.date().isoformat(),
            candidate.name,
            candidate.email or "",
            metric.jobs_applied_detected,
            metric.recruiter_replies,
            metric.interview_invites,
            metric.assessments,
            metric.rejections,
            metric.followups_required,
            _fmt(metric.last_mailbox_scan_at),
        ])
    return rows


def _candidate_detail_rows(db: Session) -> list[list[Any]]:
    rows = [["candidate", "email timestamp", "sender", "subject", "detected company", "detected role", "category", "importance", "action required", "gmail message link"]]
    stmt = (
        select(EmailEvent, Candidate)
        .join(Candidate, Candidate.id == EmailEvent.candidate_id)
        .where(EmailEvent.received_at >= _now() - timedelta(days=30))
        .order_by(EmailEvent.received_at.desc())
        .limit(1000)
    )
    for event, candidate in db.execute(stmt).all():
        rows.append([
            candidate.name,
            _fmt(event.received_at),
            event.sender or "",
            event.subject or "",
            event.detected_company or "",
            event.detected_role or "",
            event.category,
            event.importance,
            "yes" if event.action_required else "no",
            event.gmail_link or "",
        ])
    return rows


def _upcoming_interview_rows(db: Session) -> list[list[Any]]:
    rows = [["candidate", "event title", "start time", "end time", "organizer", "meeting link", "calendar source"]]
    stmt = (
        select(CandidateCalendarEvent, Candidate)
        .join(Candidate, Candidate.id == CandidateCalendarEvent.candidate_id)
        .where(
            CandidateCalendarEvent.starts_at >= _now(),
            CandidateCalendarEvent.is_interview_like.is_(True),
        )
        .order_by(CandidateCalendarEvent.starts_at.asc())
    )
    for event, candidate in db.execute(stmt).all():
        rows.append([
            candidate.name,
            event.title or "",
            _fmt(event.starts_at),
            _fmt(event.ends_at),
            event.organizer or "",
            event.meeting_link or "",
            event.calendar_source,
        ])
    return rows


def _mailbox_health_rows(db: Session) -> list[list[Any]]:
    rows = [["candidate", "candidate email", "gmail connected", "calendar connected", "last successful scan", "authorization status", "error message"]]
    stmt = select(Candidate, CandidateMailbox).join(CandidateMailbox, CandidateMailbox.candidate_id == Candidate.id, isouter=True).order_by(Candidate.name.asc())
    for candidate, mailbox in db.execute(stmt).all():
        rows.append([
            candidate.name,
            (mailbox.email if mailbox else candidate.email) or "",
            "yes" if mailbox and mailbox.gmail_connected else "no",
            "yes" if mailbox and mailbox.calendar_connected else "no",
            _fmt(mailbox.last_successful_scan_at) if mailbox else "",
            mailbox.status if mailbox else "not_connected",
            mailbox.last_error or "" if mailbox else "",
        ])
    return rows


def _headers(message: dict[str, Any]) -> dict[str, str]:
    headers = {}
    for header in (message.get("payload") or {}).get("headers", []):
        headers[header.get("name", "").lower()] = header.get("value", "")
    return headers


def _candidate_id_from_state(state: str) -> int:
    try:
        prefix, raw_id, signature = state.split(":", 2)
        expected = _state_signature(prefix, raw_id)
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid OAuth state signature")
        return int(raw_id)
    except ValueError as exc:
        raise ValueError("Invalid OAuth state") from exc


def _signed_state(candidate_id: int, prefix: str) -> str:
    raw_id = str(candidate_id)
    return f"{prefix}:{raw_id}:{_state_signature(prefix, raw_id)}"


def _state_signature(prefix: str, raw_id: str) -> str:
    secret = settings.jwt_secret_key.encode("utf-8")
    payload = f"{prefix}:{raw_id}".encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def _from_gmail_internal_date(value: str | None) -> datetime:
    if not value:
        return _now()
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


def _parse_event_time(value: dict[str, str]) -> datetime | None:
    raw = value.get("dateTime") or value.get("date")
    if not raw:
        return None
    if "T" not in raw:
        raw = f"{raw}T00:00:00+00:00"
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _conference_link(item: dict[str, Any]) -> str | None:
    data = item.get("conferenceData") or {}
    for entry in data.get("entryPoints", []):
        if entry.get("uri"):
            return entry["uri"]
    return None


def _count(events: list[EmailEvent], category: str) -> int:
    return sum(1 for event in events if event.category == category)


def _date_floor(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def _fmt(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _now() -> datetime:
    return datetime.now(timezone.utc)
