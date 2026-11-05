from django.db.models import Avg, Count, FloatField, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce

from social.models import Resena


def resumen_puntuacion(media_id):
    """Promedio de la comunidad y cantidad de votos de un título (sin reseñas ocultas).

    Devuelve {"promedio": float | None, "total_votos": int}. El promedio es None
    mientras nadie haya puntuado.
    """
    datos = Resena.objects.visibles().filter(media_id=media_id).aggregate(
        promedio=Avg("puntuacion"), total_votos=Count("id")
    )
    promedio = datos["promedio"]
    return {
        "promedio": None if promedio is None else round(float(promedio), 2),
        "total_votos": datos["total_votos"],
    }


def anotar_puntuacion(queryset):
    """Agrega `promedio_puntuacion` y `total_votos` a un queryset de Media.

    Usa subconsultas (no JOIN) para que los filtros por género u otros joins del
    catálogo no multipliquen filas ni distorsionen el conteo.
    """
    resenas = (
        Resena.objects.visibles()
        .filter(media=OuterRef("pk"))
        .order_by()
        .values("media")
    )
    return queryset.annotate(
        promedio_puntuacion=Subquery(
            resenas.annotate(valor=Avg("puntuacion")).values("valor"),
            output_field=FloatField(),
        ),
        total_votos=Coalesce(
            Subquery(
                resenas.annotate(valor=Count("pk")).values("valor"),
                output_field=IntegerField(),
            ),
            0,
        ),
    )
