import sys
from datetime import timedelta
from pathlib import Path
from decouple import Csv, config

# True cuando se corre `python manage.py test`: las pruebas usan una caché en memoria
# (no necesitan Redis) y límites altos, salvo las que prueban el throttling a propósito.
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    # Apps del proyecto
    "media",
    "cines",
    "social",
    "usuarios",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # siempre antes de CommonMiddleware
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

AUTH_USER_MODEL = "usuarios.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Caché compartida entre procesos (la usa el throttling). Con la caché en memoria
# cada worker de gunicorn contaría por separado. Usa la base 1 de Redis; Celery usa la 0.
if TESTING:
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": config("CACHE_URL", default="redis://localhost:6379/1"),
            "KEY_PREFIX": "cineroll",
            # Si Redis no responde, que falle rápido en vez de colgar la petición.
            "OPTIONS": {"socket_connect_timeout": 2, "socket_timeout": 2},
        }
    }

# Con TESTING los límites son altísimos para no estorbar a las demás pruebas.
_ALTO = "100000/min"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "config.exceptions.manejador_errores",
    "DEFAULT_THROTTLE_CLASSES": ["config.throttling.LimitePorAmbito"],
    "DEFAULT_THROTTLE_RATES": {
        "acceso": _ALTO if TESTING else config("THROTTLE_ACCESO", default="10/min"),
        "escritura_social": _ALTO if TESTING else config("THROTTLE_ESCRITURA_SOCIAL", default="30/min"),
        "general": _ALTO if TESTING else config("THROTTLE_GENERAL", default="120/min"),
    },
    # Cuántos proxies hay delante de Django. En producción es 1 (Caddy): sin esto,
    # todos los visitantes parecerían tener la IP de Caddy y compartirían el límite.
    "NUM_PROXIES": config("NUM_PROXIES", default=0, cast=int),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "usuarios.serializers.CustomTokenObtainPairSerializer",
}

# Orígenes del frontend (React u otro) que pueden consumir la API
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

# --- Programación de la cartelera (Celery Beat) ---
# Pares cine:ciudad que se scrapean automáticamente. Se puede cambiar desde el
# .env sin tocar el código, por ejemplo para apagar un cine que está fallando.
# Cinemark no está aquí: no devuelve funciones en Valledupar.
from config.beat import construir_beat_schedule, parsear_pares  # noqa: E402

CARTELERA_ACTIVA = parsear_pares(
    config(
        "CARTELERA_ACTIVA",
        default="cinepolis:valledupar,royal_films:valledupar,cineland:valledupar",
        cast=Csv(),
    )
)

# Dos franjas al día (6:00 a. m. y 6:00 p. m., hora de Bogotá porque
# CELERY_TIMEZONE = America/Bogota), con 10 minutos entre un cine y el siguiente.
CELERY_BEAT_SCHEDULE = construir_beat_schedule(
    CARTELERA_ACTIVA,
    horas=(6, 18),
    espaciado_minutos=10,
)

# Celery 5.3+ avisa si no se declara esto: reintenta conectar a Redis al arrancar
# el worker en vez de morir si Redis todavía no está listo.
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Modo síncrono: .delay() ejecuta la tarea en el mismo proceso, sin Redis ni worker.
# Solo para pruebas/CI; en producción debe quedar en False.
CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", default=False, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = CELERY_TASK_ALWAYS_EAGER  # que los errores no se escondan

# --- Registros (logging) ---
# Todo sale por consola (stdout/stderr) con fecha, nivel y nombre del logger, que es
# lo que Docker captura: `docker compose logs web worker beat`.
# El nivel se puede subir o bajar desde el .env sin tocar el código (LOG_LEVEL=DEBUG).
LOG_LEVEL = config("LOG_LEVEL", default="INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "estandar": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "estandar",
        },
    },
    # Cualquier logger del proyecto (cines.services, cines.locks, usuarios...)
    # propaga al root y sale por la consola sin configurarlo uno por uno.
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        # Django trae su propio handler de consola; se vacía para que sus mensajes
        # salgan una sola vez, por el root y con nuestro formato.
        "django": {
            "handlers": [],
            "level": "INFO",
            "propagate": True,
        },
    },
}