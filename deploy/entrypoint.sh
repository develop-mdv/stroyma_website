#!/bin/sh
set -e

cd /app

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py build_image_variants

exec gunicorn stroyma.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-120}"
