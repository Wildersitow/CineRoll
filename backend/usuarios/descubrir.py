"""Encontrar personas: búsqueda de usuarios y usuarios recomendados.

  GET /api/usuarios/?search=<texto>       busca por usuario, nombre o apellido (paginado).
  GET /api/recomendaciones/usuarios/      hasta LIMITE_RECOMENDADOS personas para seguir.

Recomendados: primero quienes siguen las personas que tú sigues ("en común"),
luego los más seguidos y los que más reseñan. Nunca incluye a quien ya sigues
ni a ti. Sin sesión, solo los más seguidos y activos.
"""
from django.contrib.auth import get_user_model
from django.db.models import Case, Count, Exists, OuterRef, Q, Value, When
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from social.models import Seguimiento

Usuario = get_user_model()

LONGITUD_MINIMA_BUSQUEDA = 2
LIMITE_RECOMENDADOS = 8


class UsuarioResumenSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()
    total_resenas = serializers.IntegerField(read_only=True)
    total_seguidores = serializers.IntegerField(read_only=True)
    en_comun = serializers.IntegerField(read_only=True, default=0)
    lo_sigo = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            "id", "username", "nombre", "avatar", "biografia",
            "total_resenas", "total_seguidores", "en_comun", "lo_sigo",
        )
        read_only_fields = fields

    def get_nombre(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_lo_sigo(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        return bool(getattr(obj, "lo_sigo_anotado", False))


def usuarios_con_resumen(request):
    qs = Usuario.objects.filter(is_active=True).annotate(
        total_resenas=Count("resenas", filter=Q(resenas__oculta=False), distinct=True),
        total_seguidores=Count("seguidores", distinct=True),
    )
    if request.user.is_authenticated:
        qs = qs.annotate(
            lo_sigo_anotado=Exists(
                Seguimiento.objects.filter(seguidor=request.user, seguido=OuterRef("pk"))
            )
        )
    return qs


class BuscarUsuariosView(ListAPIView):
    serializer_class = UsuarioResumenSerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        texto = self.request.query_params.get("search", "").strip().lstrip("@")
        if len(texto) < LONGITUD_MINIMA_BUSQUEDA:
            return Usuario.objects.none()
        filtro = Q(username__icontains=texto)
        for palabra in texto.split():
            filtro |= Q(first_name__icontains=palabra) | Q(last_name__icontains=palabra)
        return (
            usuarios_con_resumen(self.request)
            .filter(filtro)
            # Usuario exacto primero, luego los que empiezan así, luego los más seguidos.
            .order_by(
                Case(
                    When(username__iexact=texto, then=Value(0)),
                    When(username__istartswith=texto, then=Value(1)),
                    default=Value(2),
                ),
                "-total_seguidores", "-total_resenas", "username"
            )
        )


class UsuariosRecomendadosView(ListAPIView):
    serializer_class = UsuarioResumenSerializer
    permission_classes = (AllowAny,)
    pagination_class = None

    def get_queryset(self):
        qs = usuarios_con_resumen(self.request)
        orden = ["-total_seguidores", "-total_resenas", "-date_joined"]
        yo = self.request.user
        if yo.is_authenticated:
            sigo = Seguimiento.objects.filter(seguidor=yo).values("seguido")
            qs = (
                qs.exclude(pk=yo.pk)
                .exclude(seguidores__seguidor=yo)
                .annotate(
                    en_comun=Count(
                        "seguidores",
                        filter=Q(seguidores__seguidor__in=sigo),
                        distinct=True,
                    )
                )
            )
            orden.insert(0, "-en_comun")
        return qs.order_by(*orden)[:LIMITE_RECOMENDADOS]
