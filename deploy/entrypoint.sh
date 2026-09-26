#!/bin/sh
set -e

cd /app

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn stroyma.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-120}"
