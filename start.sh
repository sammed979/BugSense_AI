#!/bin/bash
set -e
cd backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python manage.py migrate_locked --noinput
python manage.py database_diagnostics
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
