from app.services.gmail_classifier import classify_email, is_interview_like_calendar_event


def test_classifies_application_confirmation() -> None:
    result = classify_email(
        sender="Jobs <jobs@examplecorp.com>",
        subject="Thank you for applying for Business Analyst",
        snippet="We received your application.",
    )

    assert result.category == "application_confirmation"
    assert result.detected_company == "Examplecorp"
    assert result.detected_role == "Business Analyst"
    assert result.action_required is False


def test_classifies_interview_as_high_priority_action() -> None:
    result = classify_email(
        sender="recruiter@acme.com",
        subject="Interview for Data Analyst",
        snippet="Please share your availability for a Zoom meeting.",
    )

    assert result.category == "interview_invite"
    assert result.importance == "high"
    assert result.action_required is True


def test_calendar_interview_detection() -> None:
    assert is_interview_like_calendar_event("Technical round with hiring team") is True
    assert is_interview_like_calendar_event("Personal reminder") is False
