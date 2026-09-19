#!/bin/sh
set -eu

if [ -n "${DB_HOST:-}" ]; then
  python - <<'PY'
import os
import socket
import sys
import time

host = os.environ["DB_HOST"]
port = int(os.environ.get("DB_PORT", "5432"))
deadline = time.monotonic() + int(os.environ.get("DB_CONNECT_TIMEOUT", "60"))

while True:
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError as exc:
        if time.monotonic() >= deadline:
            print(f"Database {host}:{port} did not become available: {exc}", file=sys.stderr)
            raise SystemExit(1)
        time.sleep(1)
PY
fi

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  python - <<'PY'
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.core.management import call_command
from django.db import connection

# ECS can start several replacement tasks at once. A PostgreSQL advisory lock
# serializes migrations so only one task changes the schema at a time.
if connection.vendor == "postgresql":
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_lock(%s)", [742_031_991])
        try:
            call_command("migrate", interactive=False)
        finally:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [742_031_991])
else:
    call_command("migrate", interactive=False)
PY
fi

if [ "${COLLECT_STATIC:-1}" = "1" ]; then
  python manage.py collectstatic --noinput --clear
fi

exec "$@"
