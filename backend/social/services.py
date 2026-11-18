from django.db import transaction
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
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from media.models import Media
from social.models import PUNTUACION_MAXIMA, PUNTUACION_MINIMA, Resena, SugerenciaEdicion


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


CAMPOS_SUGERENCIA_EDITABLES = (
    "titulo",
    "titulo_original",
    "sinopsis",
    "fecha_estreno",
    "duracion",
    "poster_url",
    "trailer_url",
)


def aprobar_sugerencia(sugerencia, administrador):
    """Aplica una sugerencia pendiente a Media y deja auditada la revisión."""
    if sugerencia.estado != SugerenciaEdicion.Estado.PENDIENTE:
        raise ValidationError({"detail": "Solo se pueden aprobar sugerencias pendientes."})

    with transaction.atomic():
        sugerencia = SugerenciaEdicion.objects.select_for_update().select_related("media").get(pk=sugerencia.pk)
        if sugerencia.estado != SugerenciaEdicion.Estado.PENDIENTE:
            raise ValidationError({"detail": "Solo se pueden aprobar sugerencias pendientes."})

        from django.core.exceptions import ValidationError as DjangoValidationError

        media = sugerencia.media
        campo = sugerencia.campo

        if campo not in CAMPOS_SUGERENCIA_EDITABLES:
            raise ValidationError({"campo": ["Este campo no admite sugerencias de edición."]})

        valor = sugerencia.valor_propuesto
        if campo == "fecha_estreno":
            from datetime import date

            try:
                valor = date.fromisoformat(valor)
            except (TypeError, ValueError) as exc:
                raise ValidationError({"valor_propuesto": ["Debe ser una fecha válida."]}) from exc
        elif campo == "duracion":
            try:
                valor = int(valor)
            except (TypeError, ValueError) as exc:
                raise ValidationError({"valor_propuesto": ["Debe ser un número entero válido."]}) from exc
            if valor < 1:
                raise ValidationError({"valor_propuesto": ["La duración debe ser mayor que cero."]})

        setattr(media, campo, valor)
        try:
            media.full_clean(exclude=["tipo", "estado", "generos", "personas"])
        except DjangoValidationError as exc:
            campos = {nombre: mensajes for nombre, mensajes in exc.message_dict.items()}
            raise ValidationError(campos) from exc

        media.save(update_fields=[campo])
        sugerencia.estado = SugerenciaEdicion.Estado.APROBADA
        sugerencia.revisado_por = administrador
        sugerencia.fecha_resolucion = timezone.now()
        sugerencia.save(update_fields=["estado", "revisado_por", "fecha_resolucion"])

    return sugerencia


def rechazar_sugerencia(sugerencia, administrador, motivo_rechazo=""):
    """Marca una sugerencia pendiente como rechazada."""
    if sugerencia.estado != SugerenciaEdicion.Estado.PENDIENTE:
        raise ValidationError({"detail": "Solo se pueden rechazar sugerencias pendientes."})

    with transaction.atomic():
        sugerencia = SugerenciaEdicion.objects.select_for_update().get(pk=sugerencia.pk)
        if sugerencia.estado != SugerenciaEdicion.Estado.PENDIENTE:
            raise ValidationError({"detail": "Solo se pueden rechazar sugerencias pendientes."})
        sugerencia.estado = SugerenciaEdicion.Estado.RECHAZADA
        sugerencia.revisado_por = administrador
        sugerencia.motivo_rechazo = motivo_rechazo.strip()
        sugerencia.fecha_resolucion = timezone.now()
        sugerencia.save(
            update_fields=[
                "estado",
                "revisado_por",
                "motivo_rechazo",
                "fecha_resolucion",
            ]
        )
    return sugerencia
