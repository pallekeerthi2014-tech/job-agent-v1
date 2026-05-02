from __future__ import annotations

from app.db.session import SessionLocal
from app.services.gmail_analytics import run_gmail_analytics_cycle


if __name__ == "__main__":
    with SessionLocal() as db:
        summary = run_gmail_analytics_cycle(db, publish_sheets=True)
        print(
            "Gmail analytics complete: "
            f"mailboxes={summary.mailboxes_scanned}, "
            f"emails={summary.email_events_created}, "
            f"calendar_events={summary.calendar_events_upserted}, "
            f"sheets_published={summary.sheets_published}, "
            f"failures={summary.failures}"
        )
