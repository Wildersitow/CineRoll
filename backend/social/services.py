from django.db.models import (
    Avg,
    Count,
    FloatField,
    IntegerField,
    Max,
    OuterRef,
    Q,
    Subquery,
)
from django.db.models.functions import Coalesce

from media.models import Media
from social.models import PUNTUACION_MAXIMA, PUNTUACION_MINIMA, Resena


# # 

def resumen_puntuacion(media_id):
    """Agrega el promedio, total y distribución de notas sin reseñas ocultas.

    El promedio es None mientras nadie haya puntuado. Todos los datos se
    obtienen en una sola consulta agregada.
    """
    resenas_visibles = Q(resenas__oculta=False)
    datos = Media.objects.filter(pk=media_id).aggregate(
        existe_media=Max("pk"),
        promedio=Avg("resenas__puntuacion", filter=resenas_visibles),
        total_votos=Count("resenas__id", filter=resenas_visibles),
        **{
            f"nota_{nota}": Count(
                "resenas__id",
                filter=resenas_visibles & Q(resenas__puntuacion=nota),
            )
            for nota in range(PUNTUACION_MINIMA, PUNTUACION_MAXIMA + 1)
        },
    )
    if datos["existe_media"] is None:
        raise Media.DoesNotExist(f"No existe Media con id {media_id}.")

    promedio = datos["promedio"]
    return {
        "promedio": None if promedio is None else round(float(promedio), 2),
        "total_votos": datos["total_votos"],
        "distribucion": {
            str(nota): datos[f"nota_{nota}"]
            for nota in range(PUNTUACION_MINIMA, PUNTUACION_MAXIMA + 1)
        },
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
