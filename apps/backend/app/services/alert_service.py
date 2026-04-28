"""
alert_service.py — WhatsApp (Twilio) + Email Job Alert Service
Production-hardened: reads all config from settings, retries Twilio sends,
enforces WhatsApp 1600-char limit, validates credentials before attempting.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

if TYPE_CHECKING:
    from app.scoring.engine import MatchScoreResult
    from app.models.candidate import Candidate
    from app.models.job import JobNormalized
    from app.models.employee import Employee

logger = logging.getLogger(__name__)

_WHATSAPP_MAX_CHARS = 1_600


# ──────────────────────────────────────────────────────────────────────────────
# Team number resolution — DB first, env fallback
# ──────────────────────────────────────────────────────────────────────────────

def _team_whatsapp_numbers(db: "Session | None" = None) -> list[str]:
    numbers: list[str] = []
    if db is not None:
        try:
            from app.models.alert_recipient import AlertRecipient
            rows = db.scalars(
                select(AlertRecipient).where(AlertRecipient.is_active == True)  # noqa: E712
            ).all()
            for row in rows:
                n = row.phone_number.strip()
                if n:
                    numbers.append(n if n.startswith("whatsapp:") else f"whatsapp:{n}")
        except Exception as exc:
            logger.warning("alert_service: DB number load failed: %s", exc)

    if not numbers:
        numbers = settings.whatsapp_team_numbers_list

    return numbers


def _dashboard_url(job_id: int | None = None) -> str:
    base = settings.public_app_url.rstrip("/")
    return f"{base}/queue?job={job_id}" if job_id else f"{base}/queue"


# ──────────────────────────────────────────────────────────────────────────────
# WhatsApp (Twilio) — with retry
# ──────────────────────────────────────────────────────────────────────────────

def send_whatsapp_alert(
    *,
    candidate_name: str,
    recruiter_name: str,
    result: "MatchScoreResult",
    job_title: str,
    job_company: str,
    job_location: str,
    job_id: int | None = None,
    db: "Session | None" = None,
) -> int:
    """Broadcast a WhatsApp alert to all active team numbers via Twilio.

    Returns the count of messages successfully sent (0 if disabled/unconfigured).
    Retries each individual send up to 2 extra times on transient errors.
    """
    if not settings.whatsapp_alerts_enabled:
        logger.debug("whatsapp_alert.skipped: WHATSAPP_ALERTS_ENABLED=false")
        return 0

    try:
        from twilio.rest import Client as TwilioClient  # type: ignore
        from twilio.base.exceptions import TwilioRestException  # type: ignore
    except ImportError:
        logger.warning("whatsapp_alert.skipped: twilio package not installed")
        return 0

    if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_whatsapp_from_formatted:
        logger.warning("whatsapp_alert.skipped: incomplete Twilio credentials in config")
        return 0

    team_numbers = _team_whatsapp_numbers(db)
    if not team_numbers:
        logger.warning("whatsapp_alert.skipped: no active recipient numbers")
        return 0

    # Build message body
    score_bar = _score_bar(result.total_score)
    strengths = "\n".join(f"  • {s}" for s in result.ai_strengths[:3]) if result.ai_strengths else f"  {result.explanation[:120]}..."
    ai_line = f"\n📝 {result.ai_summary}" if result.ai_summary else ""
    apply_line = f"\n🔗 Apply: {result.apply_url}" if result.apply_url else ""
    dashboard_line = f"\n📊 Dashboard: {_dashboard_url(job_id)}"

    message_body = (
        f"🎯 *New Job Match — {result.priority_bucket} Priority*\n"
        f"──────────────────\n"
        f"👤 Candidate: {candidate_name}\n"
        f"🏢 Role: {job_title}\n"
        f"🏛  Company: {job_company}\n"
        f"📍 Location: {job_location or 'Not specified'}\n"
        f"📊 Score: {score_bar} {result.total_score:.1f}/100\n"
        f"👔 Recruiter: {recruiter_name}"
        f"{ai_line}\n"
        f"\n✅ Key Strengths:\n{strengths}"
        f"{apply_line}"
        f"{dashboard_line}"
    )

    # Enforce Twilio's 1600-character limit
    if len(message_body) > _WHATSAPP_MAX_CHARS:
        message_body = message_body[: _WHATSAPP_MAX_CHARS - 4] + "…"

    client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _send_one(to_number: str) -> None:
        client.messages.create(
            body=message_body,
            from_=settings.twilio_whatsapp_from_formatted,
            to=to_number,
        )

    sent = 0
    for to_number in team_numbers:
        try:
            _send_one(to_number)
            sent += 1
            logger.info("whatsapp_alert.sent to=%s candidate=%s score=%.1f",
                        to_number, candidate_name, result.total_score)
        except Exception as exc:
            logger.warning("whatsapp_alert.failed to=%s error=%s", to_number, exc)

    return sent


# ──────────────────────────────────────────────────────────────────────────────
# Email alert
# ──────────────────────────────────────────────────────────────────────────────

def send_email_alert(
    *,
    recruiter_email: str,
    recruiter_name: str,
    candidate_name: str,
    result: "MatchScoreResult",
    job_title: str,
    job_company: str,
    job_location: str,
    job_id: int | None = None,
) -> bool:
    """Send an HTML email alert for a high-scoring job match.
    Returns True on success, False on failure. Never raises.
    """
    if not settings.email_alerts_enabled:
        logger.debug("email_alert.skipped: EMAIL_ALERTS_ENABLED=false")
        return False

    if not settings.smtp_host or not settings.smtp_from_email:
        logger.warning("email_alert.skipped: SMTP not configured")
        return False

    subject = (
        f"[{result.priority_bucket} Match] {candidate_name} → "
        f"{job_title} at {job_company} ({result.total_score:.0f}/100)"
    )

    gaps_html = (
        "<ul>" + "".join(f"<li>{g}</li>" for g in result.ai_gaps) + "</ul>"
        if result.ai_gaps else "<p>No significant gaps identified.</p>"
    )
    strengths_html = (
        "<ul>" + "".join(f"<li>{s}</li>" for s in result.ai_strengths) + "</ul>"
        if result.ai_strengths else f"<p>{result.explanation[:300]}</p>"
    )
    ai_summary_html = (
        f'<p style="font-style:italic;color:#555;">{result.ai_summary}</p>'
        if result.ai_summary else ""
    )
    apply_button = (
        f'<a href="{result.apply_url}" style="display:inline-block;padding:10px 20px;'
        f'background:#1B6EC2;color:#fff;text-decoration:none;border-radius:4px;font-weight:bold;">Apply Now →</a>'
        if result.apply_url else ""
    )

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;max-width:650px;margin:0 auto;padding:20px;color:#222;">
  <div style="background:#1B6EC2;padding:16px 20px;border-radius:6px 6px 0 0;">
    <h2 style="color:#fff;margin:0;">🎯 New Job Match — {result.priority_bucket} Priority</h2>
  </div>
  <div style="border:1px solid #ddd;border-top:none;padding:20px;border-radius:0 0 6px 6px;">
    <p>Hi {recruiter_name},</p>
    <p>A new job has been matched to one of your candidates:</p>
    {ai_summary_html}
    <table style="width:100%;border-collapse:collapse;margin:16px 0;">
      <tr style="background:#f0f4f8;"><td style="padding:8px 12px;font-weight:bold;border:1px solid #ddd;">Candidate</td><td style="padding:8px 12px;border:1px solid #ddd;">{candidate_name}</td></tr>
      <tr><td style="padding:8px 12px;font-weight:bold;border:1px solid #ddd;">Job Title</td><td style="padding:8px 12px;border:1px solid #ddd;">{job_title}</td></tr>
      <tr style="background:#f0f4f8;"><td style="padding:8px 12px;font-weight:bold;border:1px solid #ddd;">Company</td><td style="padding:8px 12px;border:1px solid #ddd;">{job_company}</td></tr>
      <tr><td style="padding:8px 12px;font-weight:bold;border:1px solid #ddd;">Location</td><td style="padding:8px 12px;border:1px solid #ddd;">{job_location or 'Not specified'}</td></tr>
      <tr style="background:#f0f4f8;"><td style="padding:8px 12px;font-weight:bold;border:1px solid #ddd;">Match Score</td>
        <td style="padding:8px 12px;border:1px solid #ddd;"><strong style="color:#1B6EC2;">{result.total_score:.1f}/100</strong> ({result.priority_bucket} priority)</td></tr>
    </table>
    <h3 style="color:#1B6EC2;">Score Breakdown</h3>
    <table style="width:100%;border-collapse:collapse;margin-bottom:16px;">
      <tr style="background:#1B6EC2;color:#fff;">
        <th style="padding:8px 12px;text-align:left;">Dimension</th>
        <th style="padding:8px 12px;text-align:center;">Score</th>
        <th style="padding:8px 12px;text-align:center;">Max</th>
      </tr>
      {_score_table_rows(result)}
    </table>
    <h3 style="color:#1B6EC2;">Key Strengths</h3>{strengths_html}
    <h3 style="color:#1B6EC2;">Gaps to Review</h3>{gaps_html}
    <div style="margin-top:24px;">
      {apply_button}
      &nbsp;&nbsp;
      <a href="{_dashboard_url(job_id)}" style="display:inline-block;padding:10px 20px;
        background:#f0f4f8;color:#1B6EC2;text-decoration:none;border-radius:4px;
        border:1px solid #1B6EC2;font-weight:bold;">View in Dashboard</a>
    </div>
    <p style="margin-top:24px;font-size:12px;color:#888;">
      Generated automatically by the ThinkSuccess Job Alert Platform.
    </p>
  </div>
</body>
</html>"""

    try:
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from_email
        msg["To"] = recruiter_email
        msg.set_content(
            f"New {result.priority_bucket} match: {candidate_name} → {job_title} ({result.total_score:.0f}/100)"
        )
        msg.add_alternative(html, subtype="html")

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            if settings.smtp_use_tls:
                server.starttls(context=ssl.create_default_context())
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)

        logger.info("email_alert.sent to=%s candidate=%s score=%.1f",
                    recruiter_email, candidate_name, result.total_score)
        return True

    except Exception as exc:
        logger.warning("email_alert.failed to=%s error=%s", recruiter_email, exc)
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class AlertDispatchSummary:
    matches_evaluated: int = 0
    whatsapp_sent: int = 0
    email_sent: int = 0
    skipped_below_threshold: int = 0
    failed: int = 0


def dispatch_job_alerts(db: Session, new_job_ids: list[int]) -> AlertDispatchSummary:
    """Called by the scheduler after each pipeline cycle."""
    from app.models.match_score import JobCandidateMatch
    from app.models.candidate import Candidate
    from app.models.job import JobNormalized
    from app.models.employee import Employee

    summary = AlertDispatchSummary()
    threshold = settings.alert_min_score

    if not new_job_ids:
        return summary

    if not settings.whatsapp_alerts_enabled and not settings.email_alerts_enabled:
        logger.debug("dispatch_job_alerts.skipped: no alert channels enabled")
        return summary

    matches = list(
        db.execute(
            select(JobCandidateMatch)
            .options(
                joinedload(JobCandidateMatch.candidate).joinedload(Candidate.preference),
                joinedload(JobCandidateMatch.candidate).joinedload(Candidate.skills),
                joinedload(JobCandidateMatch.candidate).joinedload(Candidate.employee),
                joinedload(JobCandidateMatch.job),
            )
            .where(
                JobCandidateMatch.job_id.in_(new_job_ids),
                JobCandidateMatch.score >= threshold,
            )
            .order_by(JobCandidateMatch.score.desc())
        )
        .unique()
        .scalars()
    )

    summary.matches_evaluated = len(matches)

    for match in matches:
        candidate: Candidate = match.candidate
        job: JobNormalized = match.job
        employee: Employee | None = candidate.employee

        recruiter_name = employee.name if employee else "Team"
        recruiter_email = employee.email if employee else None

        from app.scoring.engine import MatchScoreResult, enrich_with_ai_explanation
        score_result = MatchScoreResult(
            total_score=match.score,
            title_score=match.title_score or 0.0,
            domain_score=match.domain_score or 0.0,
            skills_score=match.skills_score or 0.0,
            experience_score=match.experience_score or 0.0,
            employment_preference_score=match.employment_preference_score or 0.0,
            visa_score=match.visa_score or 0.0,
            location_score=match.location_score or 0.0,
            priority_bucket=match.status or "Medium",
            explanation=match.explanation or "",
            apply_url=job.apply_url or job.canonical_apply_url or "",
        )
        score_result = enrich_with_ai_explanation(score_result, candidate, job)

        alert_kwargs = dict(
            candidate_name=candidate.name,
            recruiter_name=recruiter_name,
            result=score_result,
            job_title=job.title,
            job_company=job.company,
            job_location=job.location or ("Remote" if job.is_remote else "Not specified"),
            job_id=job.id,
        )

        wa_sent = send_whatsapp_alert(**alert_kwargs, db=db)
        summary.whatsapp_sent += wa_sent

        email_ok = send_email_alert(**alert_kwargs, recruiter_email=recruiter_email) if recruiter_email else False
        if email_ok:
            summary.email_sent += 1

        if wa_sent == 0 and not email_ok:
            summary.failed += 1

    logger.info(
        "dispatch_job_alerts.complete evaluated=%d whatsapp=%d email=%d failed=%d",
        summary.matches_evaluated, summary.whatsapp_sent, summary.email_sent, summary.failed,
    )
    return summary


# ── Helpers ───────────────────────────────────────────────────────────────────

def _score_bar(score: float, width: int = 10) -> str:
    filled = round((score / 100) * width)
    return "█" * filled + "░" * (width - filled)


def _score_table_rows(result: "MatchScoreResult") -> str:
    rows = [
        ("Title Match", result.title_score, 25),
        ("Domain Match", result.domain_score, 20),
        ("Skills Match", result.skills_score, 20),
        ("Experience Fit", result.experience_score, 10),
        ("Employment Preference", result.employment_preference_score, 10),
        ("Visa Fit", result.visa_score, 10),
        ("Location / Remote", result.location_score, 5),
    ]
    html_rows = ""
    for i, (label, score, max_score) in enumerate(rows):
        bg = "#f0f4f8" if i % 2 == 0 else "#ffffff"
        pct = (score / max_score * 100) if max_score else 0
        bar = (
            f'<div style="background:#e0e7ef;border-radius:3px;height:8px;width:80px;display:inline-block;vertical-align:middle;">'
            f'<div style="background:#1B6EC2;width:{pct:.0f}%;height:100%;border-radius:3px;"></div></div>'
        )
        html_rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:6px 12px;border:1px solid #ddd;">{label}</td>'
            f'<td style="padding:6px 12px;text-align:center;border:1px solid #ddd;">{score:.1f}</td>'
            f'<td style="padding:6px 12px;text-align:center;border:1px solid #ddd;">{max_score} &nbsp;{bar}</td>'
            f"</tr>"
        )
    return html_rows
