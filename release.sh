#!/bin/bash
# Release script for Render - runs once after deployment
# This applies database migrations before the service starts

cd /opt/render/project/src/backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "=== Running database migrations ==="
python manage.py migrate --run-syncdb --noinput

echo "=== Migrations completed successfully ==="
