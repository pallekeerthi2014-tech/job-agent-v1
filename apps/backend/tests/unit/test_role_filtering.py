from app.services.role_filtering import is_relevant_analyst_role


def test_role_filtering_accepts_analyst_family_titles() -> None:
    assert is_relevant_analyst_role("Healthcare Business Analyst") is True
    assert is_relevant_analyst_role("Senior Data Analyst") is True
    assert is_relevant_analyst_role("Business Systems Analyst") is True


def test_role_filtering_rejects_irrelevant_or_excluded_titles() -> None:
    assert is_relevant_analyst_role("Software Engineer") is False
    assert is_relevant_analyst_role("Financial Analyst") is False
    assert is_relevant_analyst_role("Business Analyst Intern") is False
