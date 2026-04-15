import os
from pathlib import Path
from urllib.parse import urlparse

import dj_database_url
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env", override=True)

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================================
# APP VERSION
# ============================================================================
# NOTA: Usa `make version x.y.z` para actualizar ambos sitios a la vez:
#   - pyproject.toml (campo version)
#   - README.md (badge y tabla de versiones — gestionado por la skill update-readme)
APP_VERSION = os.getenv("APP_VERSION", "1.0.7")

# ============================================================================
# SECURITY SETTINGS
# ============================================================================
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-in-production")
EMAIL_SECRET = os.getenv("EMAIL_SECRET")

DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ("true", "1", "t")

# Validar que SECRET_KEY no sea el valor por defecto en producción
if not DEBUG and SECRET_KEY == "dev-secret-key-change-in-production":
    raise ValueError("⚠️  DJANGO_SECRET_KEY debe ser cambiado en producción!")

# Parse ALLOWED_HOSTS from comma-separated string
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Security settings for production
if not DEBUG:
    # HTTPS/SSL
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() == "true"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "True").lower() == "true"
    CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "True").lower() == "true"

    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "True").lower() == "true"
    SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "True").lower() == "true"

    # Otros headers de seguridad
    SECURE_CONTENT_TYPE_NOSNIFF = os.getenv("SECURE_CONTENT_TYPE_NOSNIFF", "True").lower() == "true"
    SECURE_BROWSER_XSS_FILTER = os.getenv("SECURE_BROWSER_XSS_FILTER", "True").lower() == "true"
    X_FRAME_OPTIONS = os.getenv("X_FRAME_OPTIONS", "DENY")

    # Trust the X-Forwarded-Proto header from reverse proxies (Nginx, Cloud Run LB)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    # CSRF Trusted Origins (para producción)
    csrf_origins = os.getenv("CSRF_TRUSTED_ORIGINS", "")
    if csrf_origins:
        CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins.split(",")]

# ============================================================================
# ENVIRONMENT
# ============================================================================
# DJANGO_ENV controla el comportamiento del entorno
# Valores permitidos:
#   - "development": Modo desarrollo (crea superuser automático, sin collectstatic)
#   - "production": Modo producción (ejecuta collectstatic, sin superuser auto)
#   - Cualquier otro valor se trata como "development"
#
# Uso en el código:
#   - entrypoint.sh: Verifica si debe crear superuser automático o collectstatic
#   - settings.py: Define configuraciones según el entorno (actualmente solo lo almacena)
ENVIRONMENT = os.getenv("DJANGO_ENV", "development")

# QA testing tools — only enabled when DJANGO_ENV=testing and a QA user is configured
IS_TESTING_ENV = ENVIRONMENT == "testing" and not DEBUG
QA_TESTING_USERNAME = os.getenv("QA_TESTING_USERNAME", "")

# ============================================================================
# SESSION CONFIGURATION
# ============================================================================
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "86400"))  # 24 horas por defecto
SESSION_COOKIE_HTTPONLY = os.getenv("SESSION_COOKIE_HTTPONLY", "True").lower() == "true"
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Strict" if not DEBUG else "Lax")

# ============================================================================
# SUPPORT / TICKETING
# ============================================================================
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", None)

# ============================================================================
# CSRF CONFIGURATION
# ============================================================================
CSRF_COOKIE_HTTPONLY = os.getenv("CSRF_COOKIE_HTTPONLY", "True" if not DEBUG else "False").lower() == "true"
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Strict" if not DEBUG else "Lax")

# Installed packages: httpx celery gspread pytest pandas markdown dotenv
INSTALLED_APPS = [  # https://www.djangoproject.com/
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",  # https://www.django-rest-framework.org/
    "corsheaders",  # https://github.com/adamchainz/django-cors-headers
    "django_filters",  # https://django-filter.readthedocs.io/en/main/
    "django_extensions",  # https://django-extensions.readthedocs.io/en/latest/
    # https://django-storages.readthedocs.io/en/latest/
    # https://github.com/jazzband/django-redis
    # https://django-environ.readthedocs.io/en/latest/
    "gsheets",  # https://pypi.org/project/django-gsheets/
    "core",
    "students",
    "billing",
    "comms",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Debe ir después de SecurityMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.QAErrorEmailMiddleware",  # QA: email errors to support
    "core.middleware.SimpleAuthMiddleware",  # Middleware de autenticación simple
]

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.today_notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "project.wsgi.application"

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
# Prioridad:
# 1. DATABASE_URL (Render, Heroku, etc.)
# 2. PostgreSQL con variables de entorno individuales
# 3. SQLite (desarrollo local)

database_url = os.getenv("DATABASE_URL", "").strip()
parsed_database_url = urlparse(database_url) if database_url else None
database_url_host = parsed_database_url.hostname if parsed_database_url else ""
database_url_has_valid_host = bool(
    database_url_host and ("." in database_url_host or database_url_host in ("localhost", "127.0.0.1"))
)

if database_url and not database_url_has_valid_host:
    database_url = ""

if database_url:
    # Render, Heroku u otro servicio que use DATABASE_URL
    DATABASES = {
        "default": dj_database_url.config(
            default=os.getenv("DATABASE_URL"),
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True if not DEBUG else False,
        )
    }
elif os.getenv("DATABASE") == "postgres" or os.getenv("POSTGRES_HOST"):
    # Docker o servidor PostgreSQL local
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "fiveaday_db"),
            "USER": os.getenv("POSTGRES_USER", "fiveaday_user"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 600,
            "OPTIONS": {
                "connect_timeout": 10,
            },
        }
    }
else:
    # SQLite para desarrollo local sin Docker
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "es-es"

TIME_ZONE = "Europe/Madrid"

USE_I18N = True

DATE_FORMAT = "d/m/Y"
SHORT_DATE_FORMAT = "d/m/Y"
DATE_INPUT_FORMATS = ["%d/%m/%Y", "%Y-%m-%d"]

USE_TZ = True

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", LOG_LEVEL),
            "propagate": False,
        },
        "core": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}

# ============================================================================
# STATIC AND MEDIA FILES
# ============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR.parent / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Configuración de WhiteNoise para producción
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR.parent / "mediafiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_SECRET", "")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ============================================================================
# CELERY CONFIGURATION
# ============================================================================
# Sin Redis (plan free de Render), usar eager mode (sincrónico)
# Las tareas se ejecutan inmediatamente en el mismo proceso
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", None)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", None)

# Serialización
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Timezone
CELERY_TIMEZONE = "Europe/Madrid"
CELERY_ENABLE_UTC = True

# Configuración de tareas
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos máximo por tarea

# Reintentos automáticos para tareas de email
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Configuración de colas
CELERY_TASK_ROUTES = {
    "comms.tasks.send_*": {"queue": "emails"},
}

# Modo eager cuando no hay broker (plan free)
if not CELERY_BROKER_URL:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
