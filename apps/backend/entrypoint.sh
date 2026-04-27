#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import os
import time

import psycopg

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    database_url = (
        "postgresql://"
        f"{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )

database_url = database_url.replace("+psycopg", "")

for attempt in range(30):
    try:
        with psycopg.connect(database_url):
            print("Database is ready")
            break
    except Exception as exc:
        print(f"Waiting for database: {exc}")
        time.sleep(2)
else:
    raise SystemExit("Database connection failed")
PY

alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"
