"""Consultas de apoyo para reseñas (likes, comentarios) y estadísticas de un título."""

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from social.models import (
    ComentarioResena,
    ElementoLista,
    LikeResena,
    Lista,
    RegistroTitulo,
    Resena,
)
from social.services import resumen_puntuacion


def _conteo(modelo):
    return Coalesce(
        Subquery(
            modelo.objects.filter(resena=OuterRef("pk"))
            .order_by()
            .values("resena")
            .annotate(total=Count("pk"))
            .values("total"),
            output_field=IntegerField(),
        ),
        0,
    )


def anotar_resenas(queryset, usuario=None):
    """Añade likes, comentarios, si el usuario la marcó y el registro del autor."""
    registro = RegistroTitulo.objects.filter(
        usuario=OuterRef("usuario"), media=OuterRef("media")
    )
    queryset = queryset.annotate(
        total_likes_anotado=_conteo(LikeResena),
        total_comentarios_anotado=_conteo(ComentarioResena),
        estado_autor_anotado=Subquery(registro.values("estado")[:1]),
        autor_le_gusta_anotado=Subquery(registro.values("me_gusta")[:1]),
    )
    if usuario is not None and usuario.is_authenticated:
        return queryset.annotate(
            me_gusta_anotado=Exists(
                LikeResena.objects.filter(resena=OuterRef("pk"), usuario=usuario)
            )
        )
    return queryset.annotate(me_gusta_anotado=Value(False))


def estadisticas_media(media):
    """Números de la ficha: nota media, distribución y actividad de los usuarios."""
    resumen = resumen_puntuacion(media.pk)
    Usuario = get_user_model()
    registros = RegistroTitulo.objects.filter(media=media)
    return {
        **resumen,
        "vistos": Usuario.objects.filter(
            Q(registros__media=media, registros__estado=RegistroTitulo.Estado.VISTO)
            | Q(resenas__media=media)
        )
        .distinct()
        .count(),
        "viendo": registros.filter(estado=RegistroTitulo.Estado.VIENDO).count(),
        "me_gusta": registros.filter(me_gusta=True).count(),
        "pendientes": ElementoLista.objects.filter(
            media=media, lista__tipo=Lista.Tipo.POR_VER
        ).count(),
        "resenas": Resena.objects.visibles().filter(media=media).exclude(texto="").count(),
        "listas": ElementoLista.objects.filter(
            media=media, lista__tipo=Lista.Tipo.PERSONALIZADA, lista__publica=True
        ).count(),
    }
