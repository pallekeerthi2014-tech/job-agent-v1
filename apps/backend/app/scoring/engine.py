from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from app.models.candidate import Candidate
from app.models.job import JobNormalized

logger = logging.getLogger(__name__)

WEIGHTS = {
    "title": 25,
    "domain": 20,
    "skills": 20,
    "experience": 10,
    "employment": 10,
    "visa": 10,
    "location": 5,
}


@dataclass(slots=True)
class MatchScoreResult:
    # ── Core rule-based scores (Phase 1 — preserved character-for-character) ──
    total_score: float
    title_score: float
    domain_score: float
    skills_score: float
    experience_score: float
    employment_preference_score: float
    visa_score: float
    location_score: float
    priority_bucket: str
    explanation: str
    # ── Phase 2 additions — AI enrichment + direct apply link ────────────────
    # All fields are optional with safe defaults so Phase 1 callers are unaffected.
    ai_summary: str = ""
    ai_strengths: list = field(default_factory=list)
    ai_gaps: list = field(default_factory=list)
    apply_url: str = ""


def score_candidate_to_job(candidate: Candidate, job: JobNormalized) -> MatchScoreResult:
    title_score = _score_title_match(candidate, job)
    domain_score = _score_domain_match(candidate, job)
    skills_score = _score_skills_match(candidate, job)
    experience_score = _score_experience_fit(candidate, job)
    employment_score = _score_employment_preference_fit(candidate, job)
    visa_score = _score_visa_fit(candidate, job)
    location_score = _score_remote_location_fit(candidate, job)

    total = round(
        title_score
        + domain_score
        + skills_score
        + experience_score
        + employment_score
        + visa_score
        + location_score,
        2,
    )
    priority_bucket = _priority_bucket(total)
    explanation = _build_explanation(
        candidate=candidate,
        job=job,
        total=total,
        priority_bucket=priority_bucket,
        title_score=title_score,
        domain_score=domain_score,
        skills_score=skills_score,
        experience_score=experience_score,
        employment_score=employment_score,
        visa_score=visa_score,
        location_score=location_score,
    )

    return MatchScoreResult(
        total_score=total,
        title_score=title_score,
        domain_score=domain_score,
        skills_score=skills_score,
        experience_score=experience_score,
        employment_preference_score=employment_score,
        visa_score=visa_score,
        location_score=location_score,
        priority_bucket=priority_bucket,
        explanation=explanation,
        apply_url=job.apply_url or job.canonical_apply_url or "",
    )


def _score_title_match(candidate: Candidate, job: JobNormalized) -> float:
    preferred_titles = {title.lower() for title in (candidate.preference.preferred_titles if candidate.preference else [])}
    if not preferred_titles:
        return round(WEIGHTS["title"] * 0.5, 2)

    job_title = job.title.lower()
    if job_title in preferred_titles:
        return float(WEIGHTS["title"])
    if any(preferred in job_title or job_title in preferred for preferred in preferred_titles):
        return round(WEIGHTS["title"] * 0.8, 2)
    if any(token in job_title for preferred in preferred_titles for token in preferred.split()):
        return round(WEIGHTS["title"] * 0.4, 2)
    return 0.0


def _score_domain_match(candidate: Candidate, job: JobNormalized) -> float:
    candidate_domains = {domain.lower() for domain in (candidate.preference.domain_expertise if candidate.preference else [])}
    job_domains = {domain.lower() for domain in job.domain_tags}
    if not candidate_domains or not job_domains:
        return 0.0
    overlap = candidate_domains & job_domains
    ratio = len(overlap) / max(len(job_domains), 1)
    return round(WEIGHTS["domain"] * min(ratio, 1.0), 2)


def _score_skills_match(candidate: Candidate, job: JobNormalized) -> float:
    candidate_skills = {skill.skill_name.lower() for skill in candidate.skills}
    must_have_keywords = {keyword.lower() for keyword in (candidate.preference.must_have_keywords if candidate.preference else [])}
    job_keywords = {keyword.lower() for keyword in job.keywords_extracted}
    relevant_keywords = must_have_keywords | job_keywords

    if not relevant_keywords:
        return round(WEIGHTS["skills"] * 0.5, 2)

    matched = candidate_skills & relevant_keywords
    ratio = len(matched) / max(len(relevant_keywords), 1)
    return round(WEIGHTS["skills"] * min(ratio, 1.0), 2)


def _score_experience_fit(candidate: Candidate, job: JobNormalized) -> float:
    years = candidate.years_experience or 0
    title = job.title.lower()

    if "lead" in title or "principal" in title:
        target_min = 8
    elif "manager" in title:
        target_min = 7
    elif "senior" in title:
        target_min = 6
    else:
        target_min = 3

    if years >= target_min:
        return float(WEIGHTS["experience"])
    if years >= max(target_min - 2, 0):
        return round(WEIGHTS["experience"] * 0.6, 2)
    return round(WEIGHTS["experience"] * 0.2, 2)


def _score_employment_preference_fit(candidate: Candidate, job: JobNormalized) -> float:
    preferences = {value.lower() for value in (candidate.preference.employment_preferences if candidate.preference else [])}
    if not preferences or not job.employment_type:
        return round(WEIGHTS["employment"] * 0.5, 2)
    if job.employment_type.lower() in preferences:
        return float(WEIGHTS["employment"])
    return 0.0


def _score_visa_fit(candidate: Candidate, job: JobNormalized) -> float:
    candidate_auth = (candidate.work_authorization or "").lower()
    visa_hints = {hint.lower() for hint in job.visa_hints}

    if not visa_hints:
        return round(WEIGHTS["visa"] * 0.7, 2)
    if "no sponsorship" in visa_hints and any(token in candidate_auth for token in ["h-1b", "opt", "tn", "visa"]):
        return 0.0
    if "visa sponsorship available" in visa_hints:
        return float(WEIGHTS["visa"])
    if "us work authorization required" in visa_hints and candidate_auth in {"us citizen", "green card", "ead", "opt ead"}:
        return float(WEIGHTS["visa"])
    if "citizenship preferred" in visa_hints and candidate_auth == "us citizen":
        return float(WEIGHTS["visa"])
    return round(WEIGHTS["visa"] * 0.5, 2)


def _score_remote_location_fit(candidate: Candidate, job: JobNormalized) -> float:
    preferences = {value.lower() for value in (candidate.preference.location_preferences if candidate.preference else [])}
    job_location = (job.location or "").lower()

    if job.is_remote and ("remote" in preferences or not preferences):
        return float(WEIGHTS["location"])
    if any(preference in job_location for preference in preferences if preference != "remote"):
        return float(WEIGHTS["location"])
    if job.is_remote:
        return round(WEIGHTS["location"] * 0.8, 2)
    return 0.0


def _priority_bucket(total_score: float) -> str:
    if total_score >= 75:
        return "High"
    if total_score >= 50:
        return "Medium"
    return "Low"


def _build_explanation(
    *,
    candidate: Candidate,
    job: JobNormalized,
    total: float,
    priority_bucket: str,
    title_score: float,
    domain_score: float,
    skills_score: float,
    experience_score: float,
    employment_score: float,
    visa_score: float,
    location_score: float,
) -> str:
    candidate_titles = ", ".join(candidate.preference.preferred_titles[:2]) if candidate.preference else "their preferred roles"
    domain_terms = ", ".join(job.domain_tags[:3]) if job.domain_tags else "general healthcare"
    matched_skills = sorted(
        {skill.skill_name for skill in candidate.skills if skill.skill_name.lower() in {keyword.lower() for keyword in job.keywords_extracted}}
    )
    skill_summary = ", ".join(matched_skills[:4]) if matched_skills else "limited direct keyword overlap"

    return (
        f"{candidate.name} scores {total:.2f}/100 for {job.title} ({priority_bucket} priority). "
        f"Title fit contributed {title_score:.2f}/25, domain alignment contributed {domain_score:.2f}/20, "
        f"and skills relevance contributed {skills_score:.2f}/20. "
        f"The role aligns with preferred titles such as {candidate_titles}, maps to healthcare domains like {domain_terms}, "
        f"and matched skills/keywords include {skill_summary}. "
        f"Experience fit contributed {experience_score:.2f}/10, employment preference fit contributed {employment_score:.2f}/10, "
        f"visa fit contributed {visa_score:.2f}/10, and remote/location fit contributed {location_score:.2f}/5."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2 — AI Enrichment Layer
# ──────────────────────────────────────────────────────────────────────────────

def enrich_with_ai_explanation(
    result: MatchScoreResult,
    candidate: Candidate,
    job: JobNormalized,
) -> MatchScoreResult:
    """
    Augment a MatchScoreResult with an AI-generated plain-English summary.

    Called AFTER rule-based scoring when AI_SCORING_ENABLED=true.
    If the AI call fails for any reason, returns the original result unchanged —
    no crash, no data loss.

    Supported providers (via env vars):
        AI_PROVIDER=openai    →  uses OPENAI_API_KEY  (default: gpt-4o-mini)
        AI_PROVIDER=anthropic →  uses ANTHROPIC_API_KEY  (default: claude-haiku-4-5-20251001)
    """
    if not _ai_enabled():
        return result

    try:
        prompt = _build_ai_prompt(result, candidate, job)
        ai_response = _call_ai(prompt)
        summary, strengths, gaps = _parse_ai_response(ai_response)
        # Return a new dataclass with AI fields populated — all other fields unchanged
        from dataclasses import replace
        return replace(result, ai_summary=summary, ai_strengths=strengths, ai_gaps=gaps)
    except Exception as exc:
        logger.warning("ai_enrichment.failed: %s", exc)
        return result


def _ai_enabled() -> bool:
    return os.getenv("AI_SCORING_ENABLED", "false").lower() in {"true", "1", "yes"}


def _build_ai_prompt(result: MatchScoreResult, candidate: Candidate, job: JobNormalized) -> str:
    candidate_skills = ", ".join(skill.skill_name for skill in candidate.skills[:10]) or "not listed"
    preferred_titles = ", ".join(candidate.preference.preferred_titles[:3]) if candidate.preference else "not listed"
    domain_expertise = ", ".join(candidate.preference.domain_expertise[:3]) if candidate.preference else "not listed"
    job_keywords = ", ".join(job.keywords_extracted[:10]) or "not listed"

    return f"""You are a healthcare IT staffing specialist. Assess how well this candidate matches this job.

CANDIDATE:
- Name: {candidate.name}
- Years of experience: {candidate.years_experience or "unknown"}
- Work authorisation: {candidate.work_authorization or "unknown"}
- Skills: {candidate_skills}
- Preferred titles: {preferred_titles}
- Domain expertise: {domain_expertise}

JOB:
- Title: {job.title}
- Company: {job.company}
- Location: {job.location or "Not specified"} | Remote: {job.is_remote}
- Employment type: {job.employment_type or "Not specified"}
- Key requirements: {job_keywords}
- Job description (first 400 chars): {(job.description or "")[:400]}

COMPUTED SCORES:
- Overall: {result.total_score:.1f}/100 ({result.priority_bucket} priority)
- Title: {result.title_score:.1f}/25 | Domain: {result.domain_score:.1f}/20 | Skills: {result.skills_score:.1f}/20
- Experience: {result.experience_score:.1f}/10 | Employment: {result.employment_preference_score:.1f}/10
- Visa: {result.visa_score:.1f}/10 | Location: {result.location_score:.1f}/5

Respond with exactly this JSON (no markdown, no extra text):
{{
  "summary": "<two sentences: why this is/isn't a strong match>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "gaps": ["<gap 1>", "<gap 2>"]
}}"""


def _call_ai(prompt: str) -> str:
    provider = os.getenv("AI_PROVIDER", "openai").lower()

    if provider == "anthropic":
        import anthropic  # type: ignore
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        model = os.getenv("AI_MODEL", "claude-haiku-4-5-20251001")
        message = client.messages.create(
            model=model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    else:  # default: openai
        import openai  # type: ignore
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        model = os.getenv("AI_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""


def _parse_ai_response(raw: str) -> tuple[str, list[str], list[str]]:
    """Parse the JSON response from the AI. Falls back to empty values on failure."""
    import json

    try:
        data = json.loads(raw.strip())
        summary = str(data.get("summary", ""))
        strengths = [str(s) for s in data.get("strengths", [])]
        gaps = [str(g) for g in data.get("gaps", [])]
        return summary, strengths, gaps
    except (json.JSONDecodeError, KeyError, TypeError):
        logger.warning("ai_enrichment.parse_failed: raw=%s", raw[:200])
        return "", [], []

