from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from email.utils import parseaddr

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailClassification:
    category: str
    importance: str
    action_required: bool
    detected_company: str | None = None
    detected_role: str | None = None


_APPLICATION_PATTERNS = [
    "application received",
    "thanks for applying",
    "thank you for applying",
    "we received your application",
    "your application has been submitted",
    "application submitted",
    "successfully applied",
    "your application was sent",
    "we have your application",
    "we got your application",
    "application is complete",
    "your profile has been submitted",
    "we will review your application",
    "submitted for the role",
    "applied to",
]
_INTERVIEW_PATTERNS = [
    "interview",
    "schedule a call",
    "schedule an interview",
    "availability",
    "calendar invitation",
    "google meet",
    "teams meeting",
    "zoom meeting",
    "phone screen",
    "screening call",
    "recruiter screen",
    "technical round",
    "manager round",
    "onsite",
    "final round",
    "meet with",
    "discussion with",
]
_ASSESSMENT_PATTERNS = [
    "assessment",
    "coding test",
    "take-home",
    "take home",
    "hackerrank",
    "codility",
    "testgorilla",
    "skill test",
    "case study",
    "work sample",
    "online test",
    "complete the challenge",
]
_REJECTION_PATTERNS = [
    "not selected",
    "not moving forward",
    "unfortunately",
    "we regret",
    "other candidates",
    "will not be proceeding",
    "will not proceed",
    "decided not to move forward",
    "no longer under consideration",
    "not continue with your candidacy",
    "not a match",
    "unable to offer",
]
_FOLLOWUP_PATTERNS = [
    "please respond",
    "next steps",
    "action required",
    "reply with",
    "confirm",
    "available times",
    "provide your availability",
    "send your availability",
    "complete this form",
    "fill out",
    "please complete",
    "please submit",
    "respond by",
]
_RECRUITER_PATTERNS = [
    "recruiter",
    "talent acquisition",
    "sourcer",
    "staffing",
    "hiring team",
    "we found your profile",
    "came across your profile",
    "opportunity",
    "would like to connect",
    "are you interested",
]
_JOB_BOARD_DOMAINS = {
    "greenhouse.io",
    "lever.co",
    "workday.com",
    "myworkdayjobs.com",
    "ashbyhq.com",
    "smartrecruiters.com",
    "icims.com",
    "bamboohr.com",
    "jobvite.com",
    "indeed.com",
    "linkedin.com",
    "naukri.com",
    "wellfound.com",
}
_CATEGORIES = {
    "application_confirmation",
    "recruiter_reply",
    "interview_invite",
    "assessment",
    "rejection",
    "follow_up_required",
    "other_important",
    "other",
}


def classify_email(
    *,
    sender: str | None,
    subject: str | None,
    snippet: str | None,
    body: str | None = None,
    use_ai: bool = True,
) -> EmailClassification:
    haystack = _normalize(" ".join(part for part in [subject, snippet, body, sender] if part))
    company = _company_from_sender(sender)
    role = _role_from_text(subject, body or snippet)

    if _contains(haystack, _INTERVIEW_PATTERNS):
        return EmailClassification("interview_invite", "high", True, company, role)
    if _contains(haystack, _ASSESSMENT_PATTERNS):
        return EmailClassification("assessment", "high", True, company, role)
    if _contains(haystack, _FOLLOWUP_PATTERNS):
        return EmailClassification("follow_up_required", "high", True, company, role)
    if _contains(haystack, _REJECTION_PATTERNS):
        return EmailClassification("rejection", "normal", False, company, role)
    if _contains(haystack, _APPLICATION_PATTERNS):
        return EmailClassification("application_confirmation", "normal", False, company, role)
    if _contains(haystack, _RECRUITER_PATTERNS):
        return EmailClassification("recruiter_reply", "high", True, company, role)

    if use_ai and _should_use_ai(haystack, sender):
        ai_result = _classify_with_ai(sender=sender, subject=subject, snippet=snippet, body=body, company=company, role=role)
        if ai_result:
            return ai_result

    return EmailClassification("other_important" if _looks_job_related(haystack) else "other", "normal", False, company, role)


def is_interview_like_calendar_event(title: str | None, description: str | None = None) -> bool:
    haystack = _normalize(" ".join(part for part in [title, description] if part))
    return _contains(haystack, _INTERVIEW_PATTERNS + ["screen", "recruiter call", "technical round", "manager round"])


def _contains(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _looks_job_related(text: str) -> bool:
    return any(
        word in text
        for word in [
            "job",
            "role",
            "position",
            "application",
            "interview",
            "recruiter",
            "hiring",
            "candidate",
            "candidacy",
            "careers",
            "talent",
            "resume",
            "cv",
        ]
    )


def _should_use_ai(text: str, sender: str | None) -> bool:
    if not settings.gmail_ai_classification_enabled or not settings.openai_api_key:
        return False
    _, addr = parseaddr(sender or "")
    domain = addr.split("@")[-1].lower() if "@" in addr else ""
    return _looks_job_related(text) or any(domain.endswith(job_domain) for job_domain in _JOB_BOARD_DOMAINS)


def _classify_with_ai(
    *,
    sender: str | None,
    subject: str | None,
    snippet: str | None,
    body: str | None,
    company: str | None,
    role: str | None,
) -> EmailClassification | None:
    try:
        from openai import OpenAI
    except ImportError:
        return None

    body_excerpt = (body or "")[:3500]
    prompt = f"""
Classify this candidate job-search email into exactly one category:
- application_confirmation: confirms the candidate applied or an application/profile was submitted
- recruiter_reply: recruiter/employer reply or outreach that is job-related but not clearly one of the other categories
- interview_invite: interview, phone screen, scheduling interview/call, or meeting invite
- assessment: assessment, test, case study, work sample, coding challenge, or required evaluation
- rejection: rejection or no longer under consideration
- follow_up_required: candidate must reply, confirm, send availability/documents, complete a form, or take action
- other_important: job-search related but not one of the above
- other: not related to job search

Prioritize the candidate's required action and funnel stage. Return only compact JSON with:
{{"category":"...", "importance":"high|normal", "action_required":true|false, "detected_company":"...", "detected_role":"..."}}

Sender: {sender or ""}
Subject: {subject or ""}
Snippet: {snippet or ""}
Body excerpt: {body_excerpt}
""".strip()

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.ai_model,
            temperature=0,
            max_tokens=160,
            messages=[
                {"role": "system", "content": "You classify recruiting emails for analytics. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
        )
        data = json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:  # pragma: no cover - external AI failures should not break scans
        logger.warning("gmail_classifier.ai_failed error=%s", exc)
        return None

    category = data.get("category")
    if category not in _CATEGORIES:
        return None
    importance = "high" if data.get("importance") == "high" or category in {"interview_invite", "assessment", "follow_up_required", "recruiter_reply"} else "normal"
    return EmailClassification(
        category=category,
        importance=importance,
        action_required=bool(data.get("action_required")) or category in {"interview_invite", "assessment", "follow_up_required", "recruiter_reply"},
        detected_company=(data.get("detected_company") or company) or None,
        detected_role=(data.get("detected_role") or role) or None,
    )


def _company_from_sender(sender: str | None) -> str | None:
    if not sender:
        return None
    _, addr = parseaddr(sender)
    domain = addr.split("@")[-1].lower() if "@" in addr else ""
    if not domain:
        return None
    domain = re.sub(r"^(mail|email|notifications|jobs|careers|talent)\.", "", domain)
    if domain in {"gmail.com", "googlemail.com", "outlook.com", "yahoo.com", "icloud.com"}:
        return None
    return domain.split(".")[0].replace("-", " ").title()


def _role_from_text(subject: str | None, body: str | None = None) -> str | None:
    subject_patterns = [
        r"applying for (?P<role>.+)",
        r"application for (?P<role>.+)",
        r"your application(?: to| for) (?P<role>.+)",
        r"interview for (?P<role>.+)",
        r"regarding (?P<role>.+)",
    ]
    body_patterns = [
        r"for the (?P<role>[\w\s,/&+-]{3,80}?) role",
        r"(?P<role>[\w\s,/&+-]{3,80}?) position",
    ]
    for text, patterns in [(subject or "", subject_patterns), (body or "", body_patterns)]:
        if not text:
            continue
        match = None
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                break
        if match:
            role = re.sub(r"[\-|:|–|\n|\.].*$", "", match.group("role")).strip(" .,:;")
            return role[:255] or None
    return None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()
