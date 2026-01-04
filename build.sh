#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit  # Exit on error

echo "Installing dependencies..."
pip install -r requirements-render.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate

# Create superuser from environment variables (if set)
if [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "Creating superuser..."
    python manage.py createsuperuser --noinput --email "$DJANGO_SUPERUSER_EMAIL" || echo "Superuser already exists"
fi

echo "Build complete!"
