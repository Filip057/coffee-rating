#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

# Create superuser if env vars are set (only creates if doesn't exist)
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser..."
    python manage.py createsuperuser --noinput --email "$DJANGO_SUPERUSER_EMAIL" 2>/dev/null || echo "Superuser already exists or could not be created"
fi

echo "Starting server..."
exec "$@"
