# ============================================================================
# DOCKERFILE - Five a Day Django Application
# ============================================================================
# Este Dockerfile crea una imagen optimizada para Django usando multi-stage build
# para reducir el tamaño final de la imagen.

# ============================================================================
# STAGE 1: Builder - Instala dependencias y compila paquetes
# ============================================================================
FROM python:3.12-slim as builder

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema necesarias para compilar paquetes Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar Poetry
RUN pip install poetry==1.7.1

# Configurar Poetry para no crear virtual environments (ya estamos en un contenedor)
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY pyproject.toml poetry.lock ./

# Instalar dependencias (solo producción)
RUN poetry install --no-dev --no-root && rm -rf $POETRY_CACHE_DIR

# ============================================================================
# STAGE 2: Runtime - Imagen final ligera
# ============================================================================
FROM python:3.12-slim

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=project.settings

# Instalar solo las dependencias runtime necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para mayor seguridad
RUN useradd -m -u 1000 django && \
    mkdir -p /app /app/staticfiles /app/mediafiles && \
    chown -R django:django /app

# Establecer directorio de trabajo
WORKDIR /app

# Copiar dependencias instaladas desde el stage builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar código de la aplicación
COPY --chown=django:django . .

# Copiar y dar permisos al script de entrada
COPY --chown=django:django entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Cambiar a usuario no-root
USER django

# Exponer puerto 8000
EXPOSE 8000

# Script de entrada que maneja migraciones y collectstatic
ENTRYPOINT ["/app/entrypoint.sh"]

# Comando por defecto: servidor Gunicorn (producción)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "project.wsgi:application"]
