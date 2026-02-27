#!/bin/sh
# ============================================================================
# ENTRYPOINT SCRIPT - Inicialización para Docker y Render.com
# ============================================================================
# Este script funciona en dos modos:
# 1. Docker local (desarrollo): Espera PostgreSQL, ejecuta migraciones, lanza runserver
# 2. Render.com (producción): Ejecuta migraciones, collectstatic, lanza Gunicorn

set -e  # Salir si algún comando falla

# ============================================================================
# Detectar entorno
# ============================================================================
IS_RENDER=false
if [ -n "$RENDER" ] || [ -n "$DATABASE_URL" ]; then
    IS_RENDER=true
    echo "=========================================="
    echo "🚀 Five a Day - Iniciando en Render.com..."
    echo "=========================================="
else
    echo "==================================="
    echo "🚀 Five a Day - Inicializando..."
    echo "==================================="
fi

# ============================================================================
# Crear directorios necesarios (solo en Docker local)
# ============================================================================
if [ "$IS_RENDER" = false ]; then
    mkdir -p /app/logs /app/staticfiles /app/mediafiles
fi

# ============================================================================
# Verificar variables de entorno críticas en Render
# ============================================================================
if [ "$IS_RENDER" = true ]; then
    if [ -z "$DATABASE_URL" ] && [ -z "$POSTGRES_HOST" ]; then
        echo "❌ ERROR: No hay configuración de base de datos (DATABASE_URL o POSTGRES_HOST)"
        exit 1
    fi
    
    if [ "$DJANGO_DEBUG" = "True" ]; then
        echo "⚠️  ADVERTENCIA: DEBUG está activado en producción"
    fi
fi

# ============================================================================
# Función: Esperar a que PostgreSQL esté disponible (solo Docker local)
# ============================================================================
wait_for_postgres() {
    echo "⏳ Esperando a PostgreSQL..."
    
    until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
        echo "   PostgreSQL no está disponible - esperando..."
        sleep 2
    done
    
    echo "✅ PostgreSQL está disponible!"
}

# ============================================================================
# Esperar a que la base de datos esté lista (solo Docker local)
# ============================================================================
if [ "$IS_RENDER" = false ] && [ "$DATABASE" = "postgres" ]; then
    wait_for_postgres
fi

# ============================================================================
# Ejecutar migraciones de Django
# ============================================================================
echo "📦 Aplicando migraciones de base de datos..."
python project/manage.py migrate --noinput

# ============================================================================
# Recolectar archivos estáticos
# ============================================================================
# En Render: Siempre (producción con WhiteNoise)
# En Docker: Solo si DJANGO_ENV=production
if [ "$IS_RENDER" = true ] || [ "$DJANGO_ENV" = "production" ]; then
    echo "📁 Recolectando archivos estáticos..."
    python project/manage.py collectstatic --noinput --clear
fi

# ============================================================================
# Crear superusuario si no existe
# ============================================================================
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "👤 Verificando superusuario..."
    python project/manage.py createsuperuser --noinput 2>/dev/null || echo "✅ Superusuario ya existe."
else
    if [ "$IS_RENDER" = true ]; then
        echo "⚠️  Variables de superusuario no configuradas en Render"
    fi
fi

# ============================================================================
# Iniciar servidor
# ============================================================================
if [ "$IS_RENDER" = true ]; then
    # RENDER: Iniciar Gunicorn
    echo "=========================================="
    echo "✨ Inicialización completada!"
    echo "🌐 Iniciando servidor Gunicorn..."
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
    # DOCKER LOCAL: Ejecutar el comando pasado (runserver)
    echo "==================================="
    echo "✨ Inicialización completada!"
    echo "==================================="
    
    exec "$@"
fi
