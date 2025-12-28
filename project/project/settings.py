from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================================
# SECURITY SETTINGS
# ============================================================================
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-in-production")
EMAIL_SECRET = os.getenv("EMAIL_SECRET")

DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ('true', '1', 't')

# Validar que SECRET_KEY no sea el valor por defecto en producción
if not DEBUG and SECRET_KEY == "dev-secret-key-change-in-production":
    raise ValueError("⚠️  DJANGO_SECRET_KEY debe ser cambiado en producción!")

# Parse ALLOWED_HOSTS from comma-separated string
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Security settings for production
if not DEBUG:
    # HTTPS/SSL
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() == 'true'
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "True").lower() == 'true'
    CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "True").lower() == 'true'
    
    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "True").lower() == 'true'
    SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "True").lower() == 'true'
    
    # Otros headers de seguridad
    SECURE_CONTENT_TYPE_NOSNIFF = os.getenv("SECURE_CONTENT_TYPE_NOSNIFF", "True").lower() == 'true'
    SECURE_BROWSER_XSS_FILTER = os.getenv("SECURE_BROWSER_XSS_FILTER", "True").lower() == 'true'
    X_FRAME_OPTIONS = os.getenv("X_FRAME_OPTIONS", "DENY")
    
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

# ============================================================================
# SESSION CONFIGURATION
# ============================================================================
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "86400"))  # 24 horas por defecto
SESSION_COOKIE_HTTPONLY = os.getenv("SESSION_COOKIE_HTTPONLY", "True").lower() == 'true'
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")  # 'Strict' en producción

# ============================================================================
# CSRF CONFIGURATION
# ============================================================================
CSRF_COOKIE_HTTPONLY = os.getenv("CSRF_COOKIE_HTTPONLY", "False").lower() == 'true'
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")  # 'Strict' en producción

# Installed packages: httpx celery gspread pytest pandas markdown dotenv
INSTALLED_APPS = [  # https://www.djangoproject.com/
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',  # https://www.django-rest-framework.org/
    "corsheaders",  # https://github.com/adamchainz/django-cors-headers
    'django_filters',  # https://django-filter.readthedocs.io/en/main/
    'django_extensions',  # https://django-extensions.readthedocs.io/en/latest/
      # https://django-storages.readthedocs.io/en/latest/
      # https://github.com/jazzband/django-redis
      # https://django-environ.readthedocs.io/en/latest/
    'gsheets',  # https://pypi.org/project/django-gsheets/
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.SimpleAuthMiddleware',  # Middleware de autenticación simple
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
# Usar PostgreSQL si DATABASE=postgres, sino SQLite (desarrollo local)
if os.getenv("DATABASE") == "postgres":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv("POSTGRES_DB", "fiveaday_db"),
            'USER': os.getenv("POSTGRES_USER", "fiveaday_user"),
            'PASSWORD': os.getenv("POSTGRES_PASSWORD", ""),
            'HOST': os.getenv("POSTGRES_HOST", "localhost"),
            'PORT': os.getenv("POSTGRES_PORT", "5432"),
            'CONN_MAX_AGE': 600,  # Reutilizar conexiones
            'OPTIONS': {
                'connect_timeout': 10,
            }
        }
    }
else:
    # SQLite para desarrollo local sin Docker
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'es-es'

TIME_ZONE = 'Europe/Madrid'

USE_I18N = True

USE_TZ = True

# ============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_SECRET", "")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'proyecto_noether@outlook.com'

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR.parent, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'] if DEBUG else ['console', 'file'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'] if DEBUG else ['console', 'file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', LOG_LEVEL),
            'propagate': False,
        },
        'core': {
            'handlers': ['console'] if DEBUG else ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}

# ============================================================================
# STATIC AND MEDIA FILES
# ============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR.parent, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR.parent, 'mediafiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_SECRET", "")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
