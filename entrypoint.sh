#!/bin/sh
# ============================================================================
# ENTRYPOINT SCRIPT - Docker and Render.com Initialization
# ============================================================================
# This script operates in two modes:
# 1. Local Docker (development): Waits for PostgreSQL, runs migrations, starts runserver
# 2. Render.com (production): Runs migrations, collectstatic, starts Gunicorn

set -e  # Exit if any command fails

# ============================================================================
# Detect Environment
# ============================================================================
IS_RENDER=false
if [ -n "$RENDER" ] || [ -n "$DATABASE_URL" ]; then
    IS_RENDER=true
    echo "=========================================="
    echo "🚀 Five a Day - Starting on Render.com..."
    echo "=========================================="
else
    echo "==================================="
    echo "🚀 Five a Day - Initializing..."
    echo "==================================="
fi

# ============================================================================
# Create necessary directories (Docker local only)
# ============================================================================
if [ "$IS_RENDER" = false ]; then
    mkdir -p /app/logs /app/staticfiles /app/mediafiles
fi

# ============================================================================
# Check critical environment variables on Render
# ============================================================================
if [ "$IS_RENDER" = true ]; then
    if [ -z "$DATABASE_URL" ] && [ -z "$POSTGRES_HOST" ]; then
        echo "❌ ERROR: No database configuration (DATABASE_URL or POSTGRES_HOST)"
        exit 1
    fi
    
    if [ "$DJANGO_DEBUG" = "True" ]; then
        echo "⚠️ WARNING: DEBUG is enabled in production"
    fi
fi

# ============================================================================
# Function: Wait for PostgreSQL to be available (Local Docker only)
# ============================================================================
wait_for_postgres() {
    echo "⏳ Waiting for PostgreSQL..."
    
    until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
        echo "   PostgreSQL is unavailable - waiting..."
        sleep 2
    done
    
    echo "✅ PostgreSQL is available!"
}

# ============================================================================
# Wait for the database to be ready (Local Docker only)
# ============================================================================
if [ "$IS_RENDER" = false ] && [ "$DATABASE" = "postgres" ]; then
    wait_for_postgres
fi

# ============================================================================
# Run Django Migrations
# ============================================================================
echo "📦 Applying database migrations..."
python project/manage.py migrate --noinput

# ============================================================================
# Collect Static Files
# ============================================================================
# On Render: Always (production with WhiteNoise)
# On Docker: Only if DJANGO_ENV=production or DJANGO_ENV=testing
if [ "$IS_RENDER" = true ] || [ "$DJANGO_ENV" = "production" ] || [ "$DJANGO_ENV" = "testing" ]; then
    echo "📁 Collecting static files..."
    python project/manage.py collectstatic --noinput --clear
fi

# ============================================================================
# Create Superuser if it doesn't exist
# ============================================================================
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "👤 Verifying superuser..."
    python project/manage.py createsuperuser --noinput 2>/dev/null || echo "✅ Superuser already exists."
else
    if [ "$IS_RENDER" = true ]; then
        echo "⚠️ Superuser variables not configured on Render"
    fi
fi

# ============================================================================
# Start Server
# ============================================================================
if [ "$IS_RENDER" = true ]; then
    # RENDER: Start Gunicorn
    echo "=========================================="
    echo "✨ Initialization complete!"
    echo "🚀 Starting Gunicorn server..."
    echo "=========================================="
    
    exec gunicorn \
        --chdir project \
        --bind 0.0.0.0:${PORT:-8000} \
        --workers ${WEB_CONCURRENCY:-4} \
        --timeout 120 \
        --access-logfile - \
        --error-logfile - \
        project.wsgi:application
else
    # LOCAL DOCKER: Execute passed command (runserver)
    echo "==================================="
    echo "✨ Initialization complete!"
    echo "==================================="
    
    exec "$@"
fi
