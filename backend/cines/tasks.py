from dataclasses import asdict

from celery import shared_task

from cines.locks import candado_scraping
from cines.services import (
    ScraperError,
    cleanup_expired_showtimes,
    scrape_and_save_cartelera,
)

from cines.ejecuciones import aplicar_resultado, registrar_ejecucion, registrar_omitida

MAX_REINTENTOS = 3
LIMITE_SUAVE_SEGUNDOS = 300  # lanza SoftTimeLimitExceeded dentro de la tarea
LIMITE_DURO_SEGUNDOS = 360  # el worker mata la tarea
# El candado vive un poco más que la tarea, por si el worker muere sin liberarlo.
VIDA_CANDADO_SEGUNDOS = LIMITE_DURO_SEGUNDOS + 60


@shared_task
def ping():
    return "pong"


@shared_task(
    bind=True,
    autoretry_for=(ScraperError,),
    max_retries=MAX_REINTENTOS,
    retry_backoff=60,  # esperas de ~60 s, ~120 s y ~240 s
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=LIMITE_SUAVE_SEGUNDOS,
    time_limit=LIMITE_DURO_SEGUNDOS,
)
def scrape_cartelera_task(self, cine, ciudad):
    """Scrapea la cartelera de un cine en una ciudad.

    Es solo un envoltorio: toda la lógica (scraping, matching, guardado,
    sincronización y limpieza) vive en cines.services.scrape_and_save_cartelera.
    Ante un ScraperError se reintenta con espera creciente (máximo 3 veces).
    Cada intento queda registrado en EjecucionScraping.
    """
    intento = self.request.retries + 1
    with candado_scraping(cine, ciudad, VIDA_CANDADO_SEGUNDOS) as libre:
        if not libre:
            registrar_omitida(cine, ciudad, intento)
            return {
                "cine": cine,
                "ciudad": ciudad,
                "omitido": True,
                "motivo": "ya_en_ejecucion",
            }
        with registrar_ejecucion(cine, ciudad, intento) as ejecucion:
            resultado = scrape_and_save_cartelera(
                cinema_provider=cine, city_slug=ciudad
            )
            aplicar_resultado(ejecucion, resultado)
    # Celery serializa en JSON, y un dataclass no lo es: se devuelve como dict.
    return asdict(resultado)


@shared_task(soft_time_limit=60, time_limit=90)
def limpiar_cartelera_vencida():
    """Borra funciones ya pasadas y saca de cartelera lo que no tiene funciones futuras."""
    funciones_eliminadas, peliculas_fuera = cleanup_expired_showtimes()
    return {
        "funciones_vencidas_eliminadas": funciones_eliminadas,
        "peliculas_fuera_cartelera": peliculas_fuera,
    }