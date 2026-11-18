from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from media.serializers import MediaWriteSerializer
from social.models import SugerenciaEdicion


CAMPOS_SUGERENCIA_EDITABLES = (
    "titulo",
    "titulo_original",
    "sinopsis",
    "fecha_estreno",
    "duracion",
    "poster_url",
    "trailer_url",
)


def _valor_a_texto(valor):
    if valor is None:
        return ""
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return str(valor)


def _resolver_pendiente(sugerencia):
    if sugerencia.estado != SugerenciaEdicion.Estado.PENDIENTE:
        raise ValidationError({"detail": "Una sugerencia ya resuelta no puede resolverse otra vez."})


@transaction.atomic
def aprobar_sugerencia(sugerencia, administrador):
    """Vuelve a validar y aplica una sugerencia pendiente de forma atómica."""
    sugerencia = (
        SugerenciaEdicion.objects.select_for_update()
        .select_related("media")
        .get(pk=sugerencia.pk)
    )
    _resolver_pendiente(sugerencia)

    campo = sugerencia.campo
    if campo not in CAMPOS_SUGERENCIA_EDITABLES:
        raise ValidationError({"campo": ["Este campo no admite sugerencias de edición."]})

    media = sugerencia.media
    serializer = MediaWriteSerializer(media, data={campo: sugerencia.valor_propuesto}, partial=True)
    if not serializer.is_valid():
        raise ValidationError({"valor_propuesto": serializer.errors.get(campo, ["Valor no válido."])})

    valor_validado = serializer.validated_data[campo]
    valor_actual = getattr(media, campo)
    if valor_validado == valor_actual:
        raise ValidationError(
            {"valor_propuesto": ["El valor propuesto debe ser diferente al valor actual."]}
        )

    sugerencia.valor_anterior = _valor_a_texto(valor_actual)
    setattr(media, campo, valor_validado)
    media.save(update_fields=[campo])

    sugerencia.estado = SugerenciaEdicion.Estado.APROBADA
    sugerencia.revisado_por = administrador
    sugerencia.fecha_resolucion = timezone.now()
    sugerencia.save(
        update_fields=[
            "valor_anterior",
            "estado",
            "revisado_por",
            "fecha_resolucion",
        ]
    )
    return sugerencia


@transaction.atomic
def rechazar_sugerencia(sugerencia, administrador, motivo_rechazo):
    """Marca una sugerencia pendiente como rechazada de forma atómica."""
    sugerencia = SugerenciaEdicion.objects.select_for_update().get(pk=sugerencia.pk)
    _resolver_pendiente(sugerencia)

    motivo_rechazo = str(motivo_rechazo or "").strip()
    if not motivo_rechazo:
        raise ValidationError({"motivo_rechazo": ["El motivo de rechazo es obligatorio."]})

    sugerencia.estado = SugerenciaEdicion.Estado.RECHAZADA
    sugerencia.revisado_por = administrador
    sugerencia.motivo_rechazo = motivo_rechazo
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
