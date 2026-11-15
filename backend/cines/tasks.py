from dataclasses import asdict

from celery import shared_task

from cines.services import cleanup_expired_showtimes, scrape_and_save_cartelera


@shared_task
def ping():
    return "pong"


@shared_task
def scrape_cartelera_task(cine, ciudad):
    """Scrapea la cartelera de un cine en una ciudad.

    Es solo un envoltorio: toda la lógica (scraping, matching, guardado,
    sincronización y limpieza) vive en cines.services.scrape_and_save_cartelera.
    """
    resultado = scrape_and_save_cartelera(cinema_provider=cine, city_slug=ciudad)
    # Celery serializa en JSON, y un dataclass no lo es: se devuelve como dict.
    return asdict(resultado)


@shared_task
def limpiar_cartelera_vencida():
    """Borra funciones ya pasadas y saca de cartelera lo que no tiene funciones futuras."""
    funciones_eliminadas, peliculas_fuera = cleanup_expired_showtimes()
    return {
        "funciones_vencidas_eliminadas": funciones_eliminadas,
        "peliculas_fuera_cartelera": peliculas_fuera,
    }