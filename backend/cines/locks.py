"""Candado en Redis para que no corran dos scrapes del mismo cine a la vez."""
import logging
from contextlib import contextmanager

import redis
from django.conf import settings

logger = logging.getLogger(__name__)


def _cliente():
    return redis.Redis.from_url(
        settings.CELERY_BROKER_URL,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


@contextmanager
def candado_scraping(cine, ciudad, timeout):
    """Intenta tomar el candado de un cine-ciudad sin esperar.

    Entrega True si la ejecución puede continuar y False si ya hay otra en curso.
    `timeout` es la vida máxima del candado en segundos: si el worker muere sin
    liberarlo, expira solo y no queda bloqueado para siempre.

    Si Redis falla, se continúa sin candado y se avisa en el log (el candado es
    una salvaguarda, no debe tumbar el scraping).
    """
    candado = None
    try:
        candado = _cliente().lock(f"cartelera:candado:{cine}:{ciudad}", timeout=timeout)
        adquirido = candado.acquire(blocking=False)
    except redis.exceptions.RedisError:
        logger.warning(
            "No se pudo usar el candado de Redis para %s (%s); se continúa sin él.",
            cine,
            ciudad,
            exc_info=True,
        )
        candado = None
        adquirido = True

    if not adquirido:
        yield False
        return

    try:
        yield True
    finally:
        if candado is not None:
            try:
                candado.release()
            except redis.exceptions.RedisError:
                logger.warning(
                    "No se pudo liberar el candado de %s (%s).", cine, ciudad
                )