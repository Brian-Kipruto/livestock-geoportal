#!/bin/sh
set -e
case "$1" in
  web)
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput -v 0
    python manage.py ensure_buckets || echo "WARN: object storage not reachable yet"
    exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-3}" --timeout 60 --access-logfile -
    ;;
  worker) exec celery -A config worker -l info ;;
  beat)   exec celery -A config beat -l info ;;
  *)      exec "$@" ;;
esac
