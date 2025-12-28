#!/bin/bash
# ============================================================================
# ENTRYPOINT SCRIPT - Inicialización del contenedor Django
# ============================================================================
# Este script se ejecuta cada vez que arranca el contenedor.
# Espera a que la base de datos esté disponible, ejecuta migraciones
# y recolecta archivos estáticos.

set -e  # Salir si algún comando falla

echo "==================================="
echo "🚀 Five a Day - Inicializando..."
echo "==================================="

# ============================================================================
# Crear directorios necesarios
# ============================================================================
mkdir -p /app/logs /app/staticfiles /app/mediafiles

# ============================================================================
# Función: Esperar a que PostgreSQL esté disponible
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
# Esperar a que la base de datos esté lista
# ============================================================================
if [ "$DATABASE" = "postgres" ]; then
    wait_for_postgres
fi

# ============================================================================
# Ejecutar migraciones de Django
# ============================================================================
echo "📦 Aplicando migraciones de base de datos..."
python project/manage.py migrate --noinput

# ============================================================================
# Recolectar archivos estáticos (solo en producción)
# ============================================================================
if [ "$DJANGO_ENV" = "production" ]; then
    echo "📁 Recolectando archivos estáticos..."
    python project/manage.py collectstatic --noinput --clear
fi

# ============================================================================
# Crear superusuario si no existe (opcional, solo desarrollo)
# ============================================================================
if [ "$DJANGO_ENV" = "development" ] && [ "$DJANGO_SUPERUSER_USERNAME" ]; then
    echo "👤 Verificando superusuario..."
    python project/manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser(
        username='$DJANGO_SUPERUSER_USERNAME',
        email='$DJANGO_SUPERUSER_EMAIL',
        password='$DJANGO_SUPERUSER_PASSWORD'
    )
    print('✅ Superusuario creado!')
else:
    print('✅ Superusuario ya existe.')
END
fi

echo "==================================="
echo "✨ Inicialización completada!"
echo "==================================="

# Ejecutar el comando pasado al contenedor (CMD en Dockerfile)
exec "$@"
