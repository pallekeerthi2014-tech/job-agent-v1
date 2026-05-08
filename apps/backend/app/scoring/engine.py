from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, replace

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.core.config import settings
from app.models.candidate import Candidate
from app.models.job import JobNormalized

logger = logging.getLogger(__name__)

# ── Scoring weights (must sum to 100) ─────────────────────────────────────────
# Location raised 5→15: remote/hybrid fit is now a primary signal.
# Keywords added (10): dedicated JD keyword ↔ resume overlap, fully transparent.
# Title 25→20, Domain 20→15, Skills 20→15, Employment 10→5: rebalanced accordingly.
WEIGHTS = {
    "title":      20,   # preferred title alignment
    "domain":     15,   # domain/industry expertise overlap
    "skills":     15,   # structured skills vs job must-haves
    "experience": 10,   # years of experience vs role seniority
    "employment":  5,   # full-time / contract / part-time preference
    "visa":       10,   # work-auth / sponsorship fit
    "location":   15,   # remote ✓ hybrid-in-city ✓ on-site-in-city partial
    "keywords":   10,   # raw JD keyword ↔ resume keyword overlap count
}
# Sanity-check: sum == 100
assert sum(WEIGHTS.values()) == 100, f"Weights must sum to 100, got {sum(WEIGHTS.values())}"


@dataclass(slots=True)
class MatchScoreResult:
    total_score: float
    title_score: float
    domain_score: float
    skills_score: float
    experience_score: float
    employment_preference_score: float
    visa_score: float
    location_score: float
    keyword_score: float
    priority_bucket: str
    explanation: str
    # Keyword transparency — how many JD keywords appeared in the resume
    keyword_match_count: int = 0
    keyword_match_total: int = 0
    # Location mode that determined the location score
    location_match_mode: str = ""   # "remote" | "hybrid_city" | "onsite_city" | "none"
    # Smart-alert flag (set by alert_service, not the engine)
    is_smart_alert: bool = False
    ai_summary: str = ""
    ai_strengths: list = field(default_factory=list)
    ai_gaps: list = field(default_factory=list)
    apply_url: str = ""


# ── Public entry point ────────────────────────────────────────────────────────

def score_candidate_to_job(candidate: Candidate, job: JobNormalized) -> MatchScoreResult:
    title_score      = _score_title_match(candidate, job)
    domain_score     = _score_domain_match(candidate, job)
    skills_score     = _score_skills_match(candidate, job)
    experience_score = _score_experience_fit(candidate, job)
    employment_score = _score_employment_preference_fit(candidate, job)
    visa_score       = _score_visa_fit(candidate, job)
    location_score, location_mode = _score_remote_location_fit(candidate, job)
    keyword_score, kw_matched, kw_total = _score_keyword_match(candidate, job)

    total = round(
        title_score + domain_score + skills_score + experience_score
        + employment_score + visa_score + location_score + keyword_score, 2,
    )
    priority_bucket = _priority_bucket(total)
    explanation = _build_explanation(
        candidate=candidate, job=job, total=total, priority_bucket=priority_bucket,
        title_score=title_score, domain_score=domain_score, skills_score=skills_score,
        experience_score=experience_score, employment_score=employment_score,
        visa_score=visa_score, location_score=location_score, keyword_score=keyword_score,
        location_mode=location_mode, kw_matched=kw_matched, kw_total=kw_total,
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
        keyword_score=keyword_score,
        priority_bucket=priority_bucket,
        explanation=explanation,
        keyword_match_count=kw_matched,
        keyword_match_total=kw_total,
        location_match_mode=location_mode,
        apply_url=job.apply_url or job.canonical_apply_url or "",
    )


# ── Individual dimension scorers ──────────────────────────────────────────────

def _score_title_match(candidate: Candidate, job: JobNormalized) -> float:
    preferred_titles = {t.lower() for t in (candidate.preference.preferred_titles if candidate.preference else [])}
    if not preferred_titles:
        # No preferences set → neutral, give 0 (don't inflate with free credit)
        return 0.0
    job_title = job.title.lower()
    if job_title in preferred_titles:
        return float(WEIGHTS["title"])
    if any(p in job_title or job_title in p for p in preferred_titles):
        return round(WEIGHTS["title"] * 0.8, 2)
    if any(token in job_title for p in preferred_titles for token in p.split()):
        return round(WEIGHTS["title"] * 0.4, 2)
    return 0.0


def _score_domain_match(candidate: Candidate, job: JobNormalized) -> float:
    candidate_domains = {d.lower() for d in (candidate.preference.domain_expertise if candidate.preference else [])}
    job_domains = {d.lower() for d in job.domain_tags}
    if not candidate_domains or not job_domains:
        return 0.0
    overlap = candidate_domains & job_domains
    return round(WEIGHTS["domain"] * min(len(overlap) / max(len(job_domains), 1), 1.0), 2)


def _extract_resume_keywords(text: str | None) -> set[str]:
    """Extract meaningful skill-like tokens from free text (resume or JD).

    Tighter than the old version: requires ≥ 4 chars and uses a broader stop-list
    so generic English words don't inflate keyword-match scores.
    """
    if not text:
        return set()
    # Capture tech tokens including C++, .NET, Node.js, etc.
    tokens = re.findall(r'[A-Za-z][A-Za-z0-9\-\+\.\#]*', text)
    _STOP = {
        "the", "and", "for", "with", "that", "this", "are", "was", "has", "have",
        "been", "from", "will", "also", "not", "but", "can", "our", "all", "you",
        "your", "its", "use", "used", "work", "worked", "team", "role", "able",
        "help", "using", "inc", "llc", "ltd", "corp", "position", "experience",
        "must", "strong", "good", "knowledge", "skill", "skills", "year", "years",
        "job", "work", "company", "required", "preferred", "candidate", "candidates",
        "responsibilities", "qualifications", "requirements", "description", "about",
        "including", "such", "other", "well", "relevant", "related", "minimum",
        "plus", "both", "within", "across", "into", "over", "under", "between",
        "degree", "field", "fields", "working", "based", "location", "remote",
    }
    # Require ≥ 4 chars (was 3) to cut single-acronym noise
    return {t.lower() for t in tokens if len(t) >= 4 and t.lower() not in _STOP}


def _score_skills_match(candidate: Candidate, job: JobNormalized) -> float:
    """Score structured candidate skills against job must-haves.

    Intentionally narrower than _score_keyword_match — this only uses the
    curated CandidateSkill rows and the candidate's own must-have keywords,
    not raw resume text extraction (which lives in keyword score).
    """
    candidate_skills = {s.skill_name.lower() for s in candidate.skills}
    must_have = {kw.lower() for kw in (candidate.preference.must_have_keywords if candidate.preference else [])}
    job_keywords = {kw.lower() for kw in job.keywords_extracted}

    relevant = must_have | job_keywords
    if not relevant:
        return 0.0   # no data → no free credit
    matched = candidate_skills & relevant
    return round(WEIGHTS["skills"] * min(len(matched) / max(len(relevant), 1), 1.0), 2)


def _keyword_overlap(candidate: Candidate, job: JobNormalized) -> tuple[int, int]:
    """Return (matched_keyword_count, total_job_keyword_count).

    Pulls keywords from:
      - Candidate: resume text (extracted) + structured skills
      - Job: keywords_extracted metadata + description text (extracted)

    Capped at 30 unique job keywords to avoid score dilution on very long JDs.
    """
    # Candidate signals
    resume_kws   = _extract_resume_keywords(candidate.resume_text)
    skill_kws    = {s.skill_name.lower() for s in candidate.skills}
    all_candidate = resume_kws | skill_kws

    # Job signals — metadata keywords first (already curated), then JD text
    jd_kws: set[str] = {kw.lower() for kw in job.keywords_extracted}
    if job.description:
        jd_kws |= _extract_resume_keywords(job.description)

    # Cap to 30 to prevent very keyword-heavy JDs from artificially lowering the ratio
    if len(jd_kws) > 30:
        # Prefer the curated metadata keywords when trimming
        curated = {kw.lower() for kw in job.keywords_extracted}
        rest    = jd_kws - curated
        jd_kws  = curated | set(list(rest)[: max(0, 30 - len(curated))])

    if not jd_kws:
        return 0, 0

    matched = all_candidate & jd_kws
    return len(matched), len(jd_kws)


def _score_keyword_match(candidate: Candidate, job: JobNormalized) -> tuple[float, int, int]:
    """Dedicated JD keyword ↔ resume overlap score.

    Returns (score, matched_count, total_job_keywords) so the match record
    can surface exactly how many keywords were found in the resume.
    """
    matched, total = _keyword_overlap(candidate, job)
    if total == 0:
        return 0.0, 0, 0
    ratio = matched / total
    score = round(WEIGHTS["keywords"] * min(ratio, 1.0), 2)
    return score, matched, total


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
    preferences = {v.lower() for v in (candidate.preference.employment_preferences if candidate.preference else [])}
    if not preferences or not job.employment_type:
        return 0.0   # no data → no free credit
    return float(WEIGHTS["employment"]) if job.employment_type.lower() in preferences else 0.0


def _score_visa_fit(candidate: Candidate, job: JobNormalized) -> float:
    candidate_auth = (candidate.work_authorization or "").lower()
    visa_hints = {h.lower() for h in job.visa_hints}
    if not visa_hints:
        return round(WEIGHTS["visa"] * 0.7, 2)
    if "no sponsorship" in visa_hints and any(t in candidate_auth for t in ["h-1b", "opt", "tn", "visa"]):
        return 0.0
    if "visa sponsorship available" in visa_hints:
        return float(WEIGHTS["visa"])
    if "us work authorization required" in visa_hints and candidate_auth in {"us citizen", "green card", "ead", "opt ead"}:
        return float(WEIGHTS["visa"])
    if "citizenship preferred" in visa_hints and candidate_auth == "us citizen":
        return float(WEIGHTS["visa"])
    return round(WEIGHTS["visa"] * 0.5, 2)


def _candidate_city(candidate: Candidate) -> str:
    """Extract the city portion of a candidate's location string (before the first comma)."""
    loc = (candidate.location or "").lower().strip()
    return loc.split(",")[0].strip() if loc else ""


def _is_hybrid_job(job: JobNormalized) -> bool:
    """Detect hybrid jobs from employment_type or location string."""
    return (
        "hybrid" in (job.employment_type or "").lower()
        or "hybrid" in (job.location or "").lower()
    )


def _score_remote_location_fit(candidate: Candidate, job: JobNormalized) -> tuple[float, str]:
    """Score location fit and return (score, mode_label).

    Priority order:
      1. Remote job  → ideal for remote-preferring candidates (full score)
      2. Hybrid job in candidate's city → full score (great alternative to remote)
      3. Hybrid job outside candidate's city → low score
      4. On-site in candidate's preferred location → partial
      5. Everything else → 0

    Returns a tuple so the caller can record *why* the location scored as it did.
    """
    prefs = {v.lower() for v in (candidate.preference.location_preferences if candidate.preference else [])}
    job_location = (job.location or "").lower()
    candidate_city_str = _candidate_city(candidate)
    is_hybrid = _is_hybrid_job(job)

    # ── Remote job ────────────────────────────────────────────────────────────
    if job.is_remote:
        if "remote" in prefs or not prefs:
            # Perfect: candidate wants remote and this is remote
            return float(WEIGHTS["location"]), "remote"
        # Job is remote but candidate explicitly listed only on-site cities
        return round(WEIGHTS["location"] * 0.6, 2), "remote"

    # ── Hybrid job ────────────────────────────────────────────────────────────
    if is_hybrid:
        if candidate_city_str and candidate_city_str in job_location:
            # Hybrid in the candidate's own city — best non-remote outcome
            return float(WEIGHTS["location"]), "hybrid_city"
        if any(p in job_location for p in prefs if p not in ("remote",)):
            # Hybrid in a city the candidate listed as acceptable
            return round(WEIGHTS["location"] * 0.8, 2), "hybrid_city"
        # Hybrid but wrong city
        return round(WEIGHTS["location"] * 0.2, 2), "none"

    # ── On-site ───────────────────────────────────────────────────────────────
    if candidate_city_str and candidate_city_str in job_location:
        return round(WEIGHTS["location"] * 0.6, 2), "onsite_city"
    if any(p in job_location for p in prefs if p not in ("remote",)):
        return round(WEIGHTS["location"] * 0.5, 2), "onsite_city"

    return 0.0, "none"


def _priority_bucket(total_score: float) -> str:
    if total_score >= 75:
        return "High"
    if total_score >= 55:
        return "Medium"
    return "Low"


def _build_explanation(
    *, candidate, job, total, priority_bucket,
    title_score, domain_score, skills_score, experience_score,
    employment_score, visa_score, location_score, keyword_score,
    location_mode, kw_matched, kw_total,
) -> str:
    candidate_titles = ", ".join(candidate.preference.preferred_titles[:2]) if candidate.preference else "not specified"
    domain_terms = ", ".join(job.domain_tags[:3]) if job.domain_tags else "general healthcare"
    matched_skills = sorted({
        s.skill_name for s in candidate.skills
        if s.skill_name.lower() in {kw.lower() for kw in job.keywords_extracted}
    })
    skill_summary = ", ".join(matched_skills[:4]) if matched_skills else "none"

    location_mode_label = {
        "remote":      "Remote ✓",
        "hybrid_city": "Hybrid (same city) ✓",
        "onsite_city": "On-site (matching city)",
        "none":        "Location mismatch",
    }.get(location_mode, location_mode)

    kw_line = f"{kw_matched}/{kw_total} JD keywords in resume" if kw_total else "no JD keywords extracted"

    return (
        f"{candidate.name} scores {total:.2f}/100 for {job.title} ({priority_bucket} priority). "
        f"Title: {title_score:.2f}/20 | Domain: {domain_score:.2f}/15 | Skills: {skills_score:.2f}/15 | "
        f"Experience: {experience_score:.2f}/10 | Employment: {employment_score:.2f}/5 | "
        f"Visa: {visa_score:.2f}/10 | Location: {location_score:.2f}/15 [{location_mode_label}] | "
        f"Keywords: {keyword_score:.2f}/10 [{kw_line}]. "
        f"Preferred titles: {candidate_titles}. Domain: {domain_terms}. Matched skills: {skill_summary}."
    )


# ── Smart alert eligibility ───────────────────────────────────────────────────

def is_smart_alert_eligible(result: MatchScoreResult, candidate: Candidate, job: JobNormalized) -> bool:
    """Return True if this match qualifies for a smart alert.

    Smart alert fires when the candidate has smart_alerts_enabled=True AND:
      - The job is remote  OR  hybrid in the candidate's city
      - AND the candidate meets at least 60% of the experience requirement

    The overall score threshold is bypassed — the alert is about the opportunity
    type fitting the candidate's primary preference (remote/hybrid), not the
    total weighted score.
    """
    smart_enabled = getattr(candidate, "smart_alerts_enabled", True)
    if not smart_enabled:
        return False

    experience_ok = result.experience_score >= WEIGHTS["experience"] * 0.6
    location_ok   = result.location_match_mode in ("remote", "hybrid_city")

    return location_ok and experience_ok


# ── AI Enrichment ─────────────────────────────────────────────────────────────

def enrich_with_ai_explanation(
    result: MatchScoreResult,
    candidate: Candidate,
    job: JobNormalized,
) -> MatchScoreResult:
    """Add AI-generated summary/strengths/gaps. Fails silently — never crashes."""
    if not settings.ai_scoring_enabled:
        return result
    try:
        prompt = _build_ai_prompt(result, candidate, job)
        ai_response = _call_ai_with_retry(prompt)
        summary, strengths, gaps = _parse_ai_response(ai_response)
        return replace(result, ai_summary=summary, ai_strengths=strengths, ai_gaps=gaps)
    except Exception as exc:
        logger.warning("ai_enrichment.failed: %s", exc)
        return result


def _build_ai_prompt(result: MatchScoreResult, candidate: Candidate, job: JobNormalized) -> str:
    candidate_skills = ", ".join(s.skill_name for s in candidate.skills[:10]) or "not listed"
    preferred_titles = ", ".join(candidate.preference.preferred_titles[:3]) if candidate.preference else "not listed"
    domain_expertise = ", ".join(candidate.preference.domain_expertise[:3]) if candidate.preference else "not listed"
    job_keywords = ", ".join(job.keywords_extracted[:10]) or "not listed"
    job_desc = (job.description or "")[:400]
    resume_snippet = (candidate.resume_text or "")[:300]
    kw_line = (
        f"{result.keyword_match_count} of {result.keyword_match_total} JD keywords found in resume"
        if result.keyword_match_total else "keyword overlap not computed"
    )

    return f"""You are a healthcare IT staffing specialist. Assess how well this candidate matches this job.

CANDIDATE:
- Name: {candidate.name}
- Years of experience: {candidate.years_experience or "unknown"}
- Work authorisation: {candidate.work_authorization or "unknown"}
- Skills: {candidate_skills}
- Preferred titles: {preferred_titles}
- Domain expertise: {domain_expertise}
- Resume excerpt: {resume_snippet or "not provided"}

JOB:
- Title: {job.title}
- Company: {job.company}
- Location: {job.location or "Not specified"} | Remote: {job.is_remote}
- Employment type: {job.employment_type or "Not specified"}
- Key requirements: {job_keywords}
- Job description (first 400 chars): {job_desc}

COMPUTED SCORES (new weights — location and keyword overlap now heavily weighted):
- Overall: {result.total_score:.1f}/100 ({result.priority_bucket} priority)
- Title: {result.title_score:.1f}/20 | Domain: {result.domain_score:.1f}/15 | Skills: {result.skills_score:.1f}/15
- Experience: {result.experience_score:.1f}/10 | Employment: {result.employment_preference_score:.1f}/5
- Visa: {result.visa_score:.1f}/10 | Location: {result.location_score:.1f}/15 [{result.location_match_mode}]
- Keyword overlap: {result.keyword_score:.1f}/10 [{kw_line}]

Respond with exactly this JSON (no markdown, no extra text):
{{"summary": "<two sentences>", "strengths": ["<s1>", "<s2>", "<s3>"], "gaps": ["<g1>", "<g2>"]}}"""


def _call_ai_with_retry(prompt: str) -> str:
    """Call the configured AI provider with retry on rate-limit and transient errors."""
    provider = settings.ai_provider.lower()

    if provider == "anthropic":
        try:
            import anthropic  # type: ignore
        except ImportError:
            raise RuntimeError("anthropic package not installed")

        @retry(
            retry=retry_if_exception_type(Exception),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=2, min=5, max=60),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _call() -> str:
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            msg = client.messages.create(
                model=settings.ai_model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text

    else:  # openai (default)
        try:
            import openai  # type: ignore
        except ImportError:
            raise RuntimeError("openai package not installed")

        @retry(
            retry=retry_if_exception_type(Exception),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=2, min=5, max=60),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _call() -> str:
            client = openai.OpenAI(api_key=settings.openai_api_key)
            resp = client.chat.completions.create(
                model=settings.ai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3,
            )
            return resp.choices[0].message.content or ""

    return _call()


def _parse_ai_response(raw: str) -> tuple[str, list[str], list[str]]:
    try:
        data = json.loads(raw.strip())
        return (
            str(data.get("summary", "")),
            [str(s) for s in data.get("strengths", [])],
            [str(g) for g in data.get("gaps", [])],
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        logger.warning("ai_enrichment.parse_failed raw=%s", raw[:200])
        return "", [], []
