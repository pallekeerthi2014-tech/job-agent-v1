from __future__ import annotations

from dataclasses import dataclass

from app.models.candidate import Candidate
from app.models.job import JobNormalized

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

