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


def test_classifies_application_confirmation_from_body() -> None:
    result = classify_email(
        sender="no-reply@greenhouse.io",
        subject="Your submission is complete",
        snippet="Thanks",
        body="Your application was sent to Acme for the Senior Data Analyst role. The hiring team will review it.",
    )

    assert result.category == "application_confirmation"
    assert result.detected_role == "Senior Data Analyst"
    assert result.content_summary
    assert "application was sent" in result.content_summary


def test_classifies_assessment_from_body() -> None:
    result = classify_email(
        sender="talent@examplecorp.com",
        subject="Next step for your candidacy",
        snippet="Please continue when ready.",
        body="Please complete this case study and online test by Friday.",
    )

    assert result.category == "assessment"
    assert result.action_required is True


def test_classifies_rejection_language() -> None:
    result = classify_email(
        sender="careers@examplecorp.com",
        subject="Update on your application",
        snippet="After careful review, we decided not to move forward with your candidacy.",
    )

    assert result.category == "rejection"
    assert result.action_required is False


def test_email_summary_is_short_and_readable() -> None:
    result = classify_email(
        sender="jobs@examplecorp.com",
        subject="Application update",
        snippet=" ".join(["This is a long candidate application update."] * 20),
    )

    assert result.content_summary is not None
    assert len(result.content_summary) <= 240
