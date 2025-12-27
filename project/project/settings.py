from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================================
# SECURITY SETTINGS
# ============================================================================
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", os.getenv("DJANGO_SECRET", "dev-secret-key-change-in-production"))
EMAIL_SECRET = os.getenv("EMAIL_SECRET")

DEBUG = os.getenv("DJANGO_DEBUG", os.getenv("DEBUG_MODE", "False")).lower() in ('true', '1', 't')

# Parse ALLOWED_HOSTS from comma-separated string
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ============================================================================
# ENVIRONMENT
# ============================================================================
ENVIRONMENT = os.getenv("DJANGO_ENV", "development")

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
# STATIC AND MEDIA FILES
# ============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR.parent, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR.parent, 'mediafiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
