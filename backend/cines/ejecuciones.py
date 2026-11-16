"""Registro de ejecuciones del scraper en la tabla EjecucionScraping."""
from contextlib import contextmanager

from django.utils import timezone

from cines.models import EjecucionScraping

CAMPOS_CONTEO = (
    "funciones_leidas",
    "funciones_asociadas",
    "funciones_creadas",
    "funciones_actualizadas",
    "titulos_pendientes",
    "peliculas_en_cartelera",
    "estrenos_leidos",
    "estrenos_asociados",
    "funciones_vencidas_eliminadas",
    "funciones_obsoletas_eliminadas",
    "peliculas_fuera_cartelera",
)


def aplicar_resultado(ejecucion, resultado):
    for campo in CAMPOS_CONTEO:
        setattr(ejecucion, campo, getattr(resultado, campo))
    ejecucion.advertencia = resultado.advertencia


@contextmanager
def registrar_ejecucion(cine, ciudad, intento=1):
    """Crea la fila "en curso" y la cierra como exitosa o fallida.

    La fila se crea fuera de la transacción del servicio, así que sobrevive
    aunque el scraping falle y se deshaga todo lo que guardó.
    """
    ejecucion = EjecucionScraping.objects.create(
        cine=cine, ciudad=ciudad, intento=intento
    )
    try:
        yield ejecucion
    except Exception as exc:
        ejecucion.estado = EjecucionScraping.Estado.FALLIDA
        ejecucion.mensaje_error = f"{type(exc).__name__}: {exc}"
        ejecucion.fin = timezone.now()
        ejecucion.save()
        raise
    else:
        ejecucion.estado = EjecucionScraping.Estado.EXITOSA
        ejecucion.fin = timezone.now()
        ejecucion.save()


def registrar_omitida(cine, ciudad, intento=1):
    """Deja constancia de que no se ejecutó porque ya había otra en curso."""
    return EjecucionScraping.objects.create(
        cine=cine,
        ciudad=ciudad,
        intento=intento,
        estado=EjecucionScraping.Estado.OMITIDA,
        fin=timezone.now(),
    )