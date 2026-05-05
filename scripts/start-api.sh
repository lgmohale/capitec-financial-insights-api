#!/bin/sh
set -e

python - <<'PY'
import os
import time

import psycopg

database_url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

for attempt in range(30):
    try:
        with psycopg.connect(database_url):
            print("PostgreSQL is ready.")
            break
    except psycopg.OperationalError:
        print(f"Waiting for PostgreSQL... attempt {attempt + 1}/30")
        time.sleep(1)
else:
    raise SystemExit("PostgreSQL did not become ready in time.")
PY

alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
