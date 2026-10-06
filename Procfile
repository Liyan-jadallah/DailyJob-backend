web: gunicorn backend.wsgi:application --workers 2 --threads 4 --worker-class gthread
worker: celery -A backend worker --loglevel=info --concurrency=2
beat: celery -A backend beat --loglevel=info