from __future__ import annotations

import json
from dataclasses import asdict

from app.db.session import SessionLocal
from app.services.pipeline import run_daily_pipeline


def main() -> None:
    db = SessionLocal()
    try:
        summary = run_daily_pipeline(db)
        print(json.dumps(asdict(summary), default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
