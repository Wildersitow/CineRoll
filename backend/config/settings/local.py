from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Mientras PostgreSQL no esté listo, se puede trabajar con SQLite poniendo
# USE_SQLITE=True en el .env. Por defecto se usa PostgreSQL (definido en base.py).
if config("USE_SQLITE", default=False, cast=bool):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Permitir que React se comunique con Django en desarrollo
CORS_ALLOW_ALL_ORIGINS = True