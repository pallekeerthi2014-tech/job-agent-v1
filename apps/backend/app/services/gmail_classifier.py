from __future__ import annotations

import re
from dataclasses import dataclass
from email.utils import parseaddr


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
]
_ASSESSMENT_PATTERNS = ["assessment", "coding test", "take-home", "hackerrank", "codility", "testgorilla", "skill test"]
_REJECTION_PATTERNS = ["not selected", "not moving forward", "unfortunately", "we regret", "other candidates"]
_FOLLOWUP_PATTERNS = ["please respond", "next steps", "action required", "reply with", "confirm", "available times"]
_RECRUITER_PATTERNS = ["recruiter", "talent acquisition", "sourcer", "staffing", "hiring team"]


def classify_email(*, sender: str | None, subject: str | None, snippet: str | None) -> EmailClassification:
    haystack = " ".join(part for part in [subject, snippet, sender] if part).lower()
    company = _company_from_sender(sender)
    role = _role_from_subject(subject)

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
    return EmailClassification("other_important" if _looks_job_related(haystack) else "other", "normal", False, company, role)


def is_interview_like_calendar_event(title: str | None, description: str | None = None) -> bool:
    haystack = " ".join(part for part in [title, description] if part).lower()
    return _contains(haystack, _INTERVIEW_PATTERNS + ["screen", "recruiter call", "technical round", "manager round"])


def _contains(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _looks_job_related(text: str) -> bool:
    return any(word in text for word in ["job", "role", "position", "application", "interview", "recruiter", "hiring"])


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


def _role_from_subject(subject: str | None) -> str | None:
    if not subject:
        return None
    patterns = [
        r"application for (?P<role>.+)",
        r"your application(?: to| for)? (?P<role>.+)",
        r"interview for (?P<role>.+)",
        r"regarding (?P<role>.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, subject, flags=re.IGNORECASE)
        if match:
            role = re.sub(r"[\-|:|–].*$", "", match.group("role")).strip()
            return role[:255] or None
    return None
