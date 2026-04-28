#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import os
import time

import psycopg

database_url = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("DATABASE_PRIVATE_URL")
)
if not database_url:
    user = os.environ.get("POSTGRES_USER") or os.environ.get("PGUSER", "job_ops")
    password = os.environ.get("POSTGRES_PASSWORD") or os.environ.get("PGPASSWORD", "job_ops")
    host = os.environ.get("POSTGRES_HOST") or os.environ.get("PGHOST", "localhost")
    port = os.environ.get("POSTGRES_PORT") or os.environ.get("PGPORT", "5432")
    db = os.environ.get("POSTGRES_DB") or os.environ.get("PGDATABASE", "job_ops")
    database_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"

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
