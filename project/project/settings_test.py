"""
Test settings — imports everything from main settings, overrides for test environment.

Uses PostgreSQL (same as production) to ensure realistic behavior.
Requires the Docker PostgreSQL container to be running: `make up`

If PostgreSQL is not available, falls back to SQLite for CI or quick local runs.
"""

import os

from project.settings import *  # noqa: F401, F403

# Try to use PostgreSQL (matches production). Fall back to SQLite if unavailable.
_test_db_engine = os.getenv("TEST_DB_ENGINE", "postgresql")

if _test_db_engine == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test_db.sqlite3",  # noqa: F405
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "fiveaday_db"),
            "USER": os.getenv("POSTGRES_USER", "fiveaday_user"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("TEST_DB_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }

# Use simple static file storage (no manifest needed)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Disable password validators for faster tests
AUTH_PASSWORD_VALIDATORS = []

# Use faster password hasher
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable Celery in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use in-memory email backend (enables django.core.mail.outbox for assertions)
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
