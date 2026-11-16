web: cd backend && export PYTHONPATH="${PYTHONPATH}:$(pwd)" && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
release: bash release.sh
