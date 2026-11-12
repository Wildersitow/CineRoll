"""Configuración de producción.

Se activa con DJANGO_SETTINGS_MODULE=config.settings.production (en el .env del
servidor o como variable de entorno). Todo lo que cambia entre servidores se lee
del entorno; si falta una variable obligatoria, Django no arranca y avisa cuál es.
"""
from decouple import Csv

from .base import *

DEBUG = False

# Dominios desde los que se sirve la API, separados por comas.
# Ejemplo: ALLOWED_HOSTS=api.cineroll.com,cineroll.com
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())

# Orígenes del frontend que pueden consumir la API, con https:// y sin "/" final.
# Ejemplo: CORS_ALLOWED_ORIGINS=https://cineroll.com
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", cast=Csv())
CORS_ALLOW_ALL_ORIGINS = False

# Necesario para que el Django Admin acepte formularios por https.
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

# Carpeta donde `python manage.py collectstatic` junta los archivos del admin.
STATIC_ROOT = BASE_DIR / "staticfiles"

# Seguridad cuando el sitio se sirve por https (lo normal en producción).
# Se puede apagar con USAR_HTTPS=False mientras se prueba sin certificado.
USAR_HTTPS = config("USAR_HTTPS", default=True, cast=bool)
SESSION_COOKIE_SECURE = USAR_HTTPS
CSRF_COOKIE_SECURE = USAR_HTTPS
SECURE_SSL_REDIRECT = USAR_HTTPS
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30 if USAR_HTTPS else 0  # 30 días
SECURE_HSTS_INCLUDE_SUBDOMAINS = USAR_HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"