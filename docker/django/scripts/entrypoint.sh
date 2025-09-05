#!/bin/bash

# OneSquare Django Entrypoint Script

set -e

echo "=== OneSquare Django Container Starting ==="
echo "Time: $(date)"
echo "Environment: ${DEBUG:-production}"
echo "Python: $(python --version)"
echo "Django: $(python -c 'import django; print(django.get_version())')"

# Wait for services to be ready
echo "Waiting for dependencies..."
sleep 5

# Change to Django project directory
cd /var/www/html/${PROJECT_NAME}

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if secrets.json exists and has required keys
if [ ! -f "secrets.json" ]; then
    echo "Warning: secrets.json not found, using environment variables"
fi

# Run Django management commands
echo "Checking Django configuration..."
python manage.py check --deploy 2>/dev/null || python manage.py check

# Create database tables (for user sessions and admin)
echo "Running database migrations..."
python manage.py migrate --verbosity=1

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --verbosity=1

# Create superuser if in DEBUG mode and doesn't exist
if [ "${DEBUG}" = "1" ] || [ "${DEBUG}" = "true" ]; then
    echo "Development mode: Setting up admin user..."
    python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@localhost', 'admin123')
    print('Admin user created: admin/admin123')
else:
    print('Admin user already exists')
EOF
fi

# Check Notion API configuration
echo "Checking Notion API configuration..."
python manage.py shell << EOF
try:
    from django.conf import settings
    notion_token = getattr(settings, 'NOTION_TOKEN', None)
    notion_db_id = getattr(settings, 'NOTION_DATABASE_ID', None)
    
    if notion_token and notion_db_id:
        print('✅ Notion API configuration found')
    else:
        print('⚠️  Notion API not configured - please update secrets.json')
except Exception as e:
    print(f'❌ Configuration error: {e}')
EOF

# Start the Django development server or Gunicorn
if [ "${DEBUG}" = "1" ] || [ "${DEBUG}" = "true" ]; then
    echo "Starting Django development server..."
    echo "Access the application at:"
    echo "  HTTP:  http://localhost:${WEB_PORT:-8081}"
    echo "  HTTPS: https://localhost:${HTTPS_PORT:-8443}"
    echo "  Admin: https://localhost:${HTTPS_PORT:-8443}/admin (admin/admin123)"
    echo ""
    
    python manage.py runserver 0.0.0.0:8000
else
    echo "Starting Gunicorn production server..."
    gunicorn config.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers ${GUNICORN_WORKERS:-2} \
        --timeout ${GUNICORN_TIMEOUT:-300} \
        --access-logfile - \
        --error-logfile - \
        --log-level info
fi