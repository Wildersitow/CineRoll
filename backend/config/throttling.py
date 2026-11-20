"""Límites de uso de la API, por ámbito.

Una sola clase de throttle (configurada en REST_FRAMEWORK) decide el ámbito de cada
petición, así las vistas de las demás personas no tienen que declarar nada.

Ámbitos (las tasas están en REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]):
  - acceso:           login, registro y cambio de contraseña. Se cuenta por IP.
  - escritura_social: escrituras en las vistas de social/. Se cuenta por usuario.
  - general:          todo lo demás.
"""
import logging

from redis.exceptions import RedisError
from rest_framework.permissions import SAFE_METHODS
from rest_framework.throttling import SimpleRateThrottle

logger = logging.getLogger(__name__)

# Nombres de ruta (name= en urls.py) que cuentan como "acceso".
URLS_ACCESO = frozenset(
    {
        "auth_login",
        "usuario_login",
        "token_obtain_pair",
        "auth_registro",
        "auth_cambiar_clave",
        "usuarios_me_clave",
        "usuarios_me_password",
        "usuario_me_clave",
    }
)

# Rutas de escritura social que vivan fuera del paquete social/ (si las hay).
URLS_ESCRITURA_SOCIAL = frozenset()


def ambito_de(request, view):
    """Devuelve 'acceso', 'escritura_social' o 'general' para esta petición."""
    resolver = getattr(request, "resolver_match", None)
    nombre = getattr(resolver, "url_name", None)

    if nombre in URLS_ACCESO:
        return "acceso"

    if request.method not in SAFE_METHODS and (
        nombre in URLS_ESCRITURA_SOCIAL or type(view).__module__.startswith("social.")
    ):
        return "escritura_social"

    return "general"


class LimitePorAmbito(SimpleRateThrottle):
    def __init__(self):
        # La tasa depende de la petición, así que no se resuelve aquí (como hace
        # SimpleRateThrottle) sino en allow_request.
        pass

    def allow_request(self, request, view):
        self.scope = ambito_de(request, view)
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        try:
            return super().allow_request(request, view)
        except RedisError:
            # Sin Redis no hay con qué contar: se deja pasar y se avisa en el log.
            logger.warning(
                "No se pudo consultar el límite de uso (%s); se deja pasar la petición.",
                self.scope,
                exc_info=True,
            )
            return True

    def get_cache_key(self, request, view):
        usuario = getattr(request, "user", None)
        if self.scope != "acceso" and usuario is not None and usuario.is_authenticated:
            ident = f"user_{usuario.pk}"
        else:
            ident = f"ip_{self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}