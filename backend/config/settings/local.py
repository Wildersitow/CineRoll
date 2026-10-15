from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

USE_SQLITE = config("USE_SQLITE", default=True, cast=bool)
if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Permitir que React se comunique con Django en desarrollo
CORS_ALLOW_ALL_ORIGINS = True