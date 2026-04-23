from __future__ import annotations

DEFAULT_ANALYST_INCLUDE_TITLES = [
    "business analyst",
    "data analyst",
    "business systems analyst",
    "systems analyst",
    "clinical analyst",
    "reporting analyst",
    "product analyst",
    "operations analyst",
    "quality analyst",
    "healthcare analyst",
    "interoperability analyst",
    "business technical analyst",
    "business intelligence analyst",
    "business process analyst",
    "process analyst",
    "research informatics",
    "informatics analyst",
    "epic business analyst",
    "health data analyst",
    "pharma analyst",
    "life sciences analyst",
]

DEFAULT_ANALYST_EXCLUDE_TITLES = [
    "financial analyst",
    "actuarial analyst",
    "security analyst",
    "cybersecurity analyst",
    "supply chain analyst",
    "warehouse analyst",
    "investment analyst",
    "intern",
    "director",
    "manager",
    "engineer",
    "developer",
    "architect",
]


def is_relevant_analyst_role(
    title: str | None,
    *,
    include_titles: list[str] | None = None,
    exclude_titles: list[str] | None = None,
) -> bool:
    if not title:
        return False

    normalized = title.strip().lower()
    include_terms = [term.strip().lower() for term in (include_titles or DEFAULT_ANALYST_INCLUDE_TITLES) if term.strip()]
    exclude_terms = [term.strip().lower() for term in (exclude_titles or DEFAULT_ANALYST_EXCLUDE_TITLES) if term.strip()]

    if not any(term in normalized for term in include_terms):
        return False
    if any(term in normalized for term in exclude_terms):
        return False
    return True
