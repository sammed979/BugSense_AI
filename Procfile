web: cd backend && export PYTHONPATH="${PYTHONPATH}:$(pwd)" && python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
