from __future__ import annotations

import re
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TITLE_MAPS: dict[str, str] = {
    "sr healthcare business analyst": "Senior Healthcare Business Analyst",
    "senior healthcare ba": "Senior Healthcare Business Analyst",
    "healthcare ba": "Healthcare Business Analyst",
    "business systems analyst": "Business Systems Analyst",
    "payer analyst": "Payer Business Analyst",
    "claims analyst": "Claims Business Analyst",
    "interoperability analyst": "Healthcare Interoperability Analyst",
}

HEALTHCARE_DOMAIN_DICTIONARIES: dict[str, list[str]] = {
    "claims": ["claim", "claims", "adjudication", "remittance", "encounter"],
    "edi": ["edi", "834", "835", "837", "270", "271", "276", "277"],
    "interoperability": ["fhir", "hl7", "ccd", "ccda", "api", "integration"],
    "quality": ["hedis", "stars", "quality measures", "care gaps", "supplemental data"],
    "payer": ["payer", "health plan", "commercial", "medicare advantage", "medicaid"],
    "provider": ["provider", "ehr", "emr", "clinical workflow", "care management"],
    "population-health": ["population health", "risk adjustment", "stratification", "care coordination"],
}

TRANSACTION_KEYWORDS = ["834", "835", "837", "HL7", "FHIR", "EDI", "270", "271", "276", "277"]
WORK_AUTHORIZATION_PATTERNS = {
    "visa sponsorship available": r"(visa sponsorship|sponsor(?:ship)?)",
    "us work authorization required": r"(us work authorization|required to work in the us|authorized to work in the us)",
    "no sponsorship": r"(no sponsorship|unable to sponsor|cannot sponsor)",
    "citizenship preferred": r"(uscis|citizen(?:ship)? required|us citizen)",
}
REMOTE_PATTERNS = [
    r"\bremote\b",
    r"\bwork from home\b",
    r"\bwfh\b",
    r"\btelecommute\b",
    r"\banywhere in (?:the )?u?s?a?\b",
]
SALARY_PATTERNS = [
    re.compile(r"\$?\s*(\d{2,3}(?:,\d{3})+)\s*[-–to]{1,3}\s*\$?\s*(\d{2,3}(?:,\d{3})+)"),
    re.compile(r"\$?\s*(\d+(?:\.\d+)?)\s*k\s*[-–to]{1,3}\s*\$?\s*(\d+(?:\.\d+)?)\s*k", re.IGNORECASE),
]


def normalize_job_title(title: str) -> str:
    compact_title = re.sub(r"\s+", " ", title.strip())
    lookup = compact_title.lower()
    return TITLE_MAPS.get(lookup, compact_title.title() if compact_title.islower() else compact_title)


def detect_remote(text: str, location: str | None = None) -> bool:
    haystack = f"{text}\n{location or ''}".lower()
    return any(re.search(pattern, haystack, flags=re.IGNORECASE) for pattern in REMOTE_PATTERNS)


def extract_healthcare_domain_tags(text: str) -> list[str]:
    text_lower = text.lower()
    tags = [
        domain
        for domain, keywords in HEALTHCARE_DOMAIN_DICTIONARIES.items()
        if any(keyword in text_lower for keyword in keywords)
    ]
    return sorted(set(tags))


def extract_transaction_keywords(text: str) -> list[str]:
    text_upper = text.upper()
    found = [keyword for keyword in TRANSACTION_KEYWORDS if keyword in text_upper]
    return sorted(set(found))


def extract_work_authorization_hints(text: str) -> list[str]:
    text_lower = text.lower()
    hints = [
        label
        for label, pattern in WORK_AUTHORIZATION_PATTERNS.items()
        if re.search(pattern, text_lower, flags=re.IGNORECASE)
    ]
    return sorted(set(hints))


def extract_salary_ranges(text: str) -> tuple[int | None, int | None]:
    for pattern in SALARY_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue

        left, right = match.groups()
        if "k" in match.group(0).lower():
            return int(float(left) * 1000), int(float(right) * 1000)
        return int(left.replace(",", "")), int(right.replace(",", ""))
    return None, None


def build_dedupe_hash(source: str, title: str, company: str, location: str | None, apply_url: str | None) -> str:
    value = "|".join(
        [
            source.strip().lower(),
            title.strip().lower(),
            company.strip().lower(),
            (location or "").strip().lower(),
            (apply_url or "").strip().lower(),
        ]
    )
    return sha256(value.encode("utf-8")).hexdigest()


def canonicalize_apply_url(apply_url: str | None) -> str | None:
    if not apply_url:
        return None

    split = urlsplit(apply_url.strip())
    query_params = [(key, value) for key, value in parse_qsl(split.query, keep_blank_values=False) if not key.lower().startswith("utm_")]
    normalized_query = urlencode(sorted(query_params))
    normalized_path = split.path.rstrip("/") or "/"

    return urlunsplit(
        (
            split.scheme.lower(),
            split.netloc.lower(),
            normalized_path,
            normalized_query,
            "",
        )
    )


def normalized_description_content_hash(description: str | None) -> str | None:
    if not description:
        return None
    normalized = re.sub(r"\s+", " ", description).strip().lower()
    if not normalized:
        return None
    return sha256(normalized.encode("utf-8")).hexdigest()


def normalize_job_payload(
    *,
    source: str,
    title: str,
    company: str,
    description: str | None,
    location: str | None,
    employment_type: str | None,
    apply_url: str | None,
    salary_min: int | None = None,
    salary_max: int | None = None,
) -> dict:
    description_text = re.sub(r"\s+", " ", (description or "")).strip()
    combined_text = "\n".join(part for part in [title, company, location or "", description_text] if part)

    parsed_salary_min, parsed_salary_max = extract_salary_ranges(combined_text)
    normalized_title = normalize_job_title(title)
    domain_tags = extract_healthcare_domain_tags(combined_text)
    transaction_keywords = extract_transaction_keywords(combined_text)
    authorization_hints = extract_work_authorization_hints(combined_text)
    remote = detect_remote(combined_text, location)
    canonical_apply = canonicalize_apply_url(apply_url)
    description_hash = normalized_description_content_hash(description_text)

    return {
        "source": source,
        "title": normalized_title,
        "company": company.strip(),
        "location": location.strip() if location else None,
        "is_remote": remote,
        "employment_type": employment_type,
        "salary_min": salary_min if salary_min is not None else parsed_salary_min,
        "salary_max": salary_max if salary_max is not None else parsed_salary_max,
        "apply_url": apply_url,
        "canonical_apply_url": canonical_apply,
        "description": description_text or None,
        "normalized_description_hash": description_hash,
        "domain_tags": domain_tags,
        "visa_hints": authorization_hints,
        "keywords_extracted": transaction_keywords,
        "dedupe_hash": build_dedupe_hash(source, normalized_title, company, location, apply_url),
        "is_active": True,
        "probable_duplicate_of_job_id": None,
        "duplicate_reasons": [],
    }
