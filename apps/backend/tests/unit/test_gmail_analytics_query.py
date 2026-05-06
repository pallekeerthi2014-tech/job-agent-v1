from datetime import datetime, timezone

from app.services.gmail_analytics import _gmail_message_query


def test_gmail_message_query_searches_all_folders() -> None:
    query = _gmail_message_query(datetime(2026, 5, 6, tzinfo=timezone.utc))

    assert query == "in:anywhere after:2026/05/06"
