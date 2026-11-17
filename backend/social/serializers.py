from rest_framework import serializers

from media.models import Media
from social.models import ElementoLista, Lista, ReporteResena, Resena


MAX_RESENA_TEXTO_LENGTH = 5000


class ResenaSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.username", read_only=True)
    usuario_id = serializers.IntegerField(read_only=True)
    media_id = serializers.IntegerField(read_only=True)
    media_titulo = serializers.CharField(source="media.titulo", read_only=True)
    media_poster_url = serializers.CharField(source="media.poster_url", read_only=True)
    media_tipo = serializers.CharField(source="media.tipo", read_only=True)
    texto = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=MAX_RESENA_TEXTO_LENGTH,
    )

    class Meta:
        model = Resena
        fields = (
            "id",
            "usuario",
            "usuario_id",
            "media_id",
            "media_titulo",
            "media_poster_url",
            "media_tipo",
            "puntuacion",
            "texto",
            "fecha_creacion",
            "fecha_actualizacion",
        )
        read_only_fields = ("id", "fecha_creacion", "fecha_actualizacion")

    def validate_texto(self, value):
        normalized = " ".join(value.split())
        if len(normalized) > MAX_RESENA_TEXTO_LENGTH:
            raise serializers.ValidationError(
                f"El texto de la reseña no puede superar "
                f"{MAX_RESENA_TEXTO_LENGTH} caracteres."
            )
        return normalized

    def validate(self, attrs):
        media = (
            self.instance.media
            if self.instance is not None
            else self.context.get("media")
        )
        if media and media.estado == Media.Estado.PROXIMO_ESTRENO:
            raise serializers.ValidationError(
                {
                    "detail": (
                        "No se pueden crear ni editar reseñas de títulos "
                        "próximos a estrenarse."
                    )
                }
            )
        return attrs


class ReporteResenaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReporteResena
        fields = ("id", "resena", "usuario", "motivo", "fecha")
        read_only_fields = ("id", "resena", "usuario", "fecha")


class ElementoListaSerializer(serializers.ModelSerializer):
    media_id = serializers.IntegerField(source="media.id", read_only=True)
    media_titulo = serializers.CharField(source="media.titulo", read_only=True)
    media_poster_url = serializers.CharField(source="media.poster_url", read_only=True)
    media_tipo = serializers.CharField(source="media.tipo", read_only=True)
    media_estado = serializers.CharField(source="media.estado", read_only=True)

    class Meta:
        model = ElementoLista
        fields = (
            "id",
            "media_id",
            "media_titulo",
            "media_poster_url",
            "media_tipo",
            "media_estado",
            "orden",
            "fecha_agregado",
        )
        read_only_fields = ("id", "fecha_agregado")


class ListaSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.username", read_only=True)
    usuario_id = serializers.IntegerField(read_only=True)
    total_elementos = serializers.IntegerField(read_only=True)

    class Meta:
        model = Lista
        fields = (
            "id",
            "usuario",
            "usuario_id",
            "nombre",
            "descripcion",
            "tipo",
            "publica",
            "total_elementos",
            "fecha_creacion",
            "fecha_actualizacion",
        )
        read_only_fields = (
            "id",
            "usuario",
            "usuario_id",
            "total_elementos",
            "fecha_creacion",
            "fecha_actualizacion",
        )

    def validate(self, attrs):
        tipo = attrs.get("tipo", getattr(self.instance, "tipo", None))
        request = self.context.get("request")
        if request and request.user.is_authenticated and tipo in [Lista.Tipo.FAVORITAS, Lista.Tipo.POR_VER]:
            qs = Lista.objects.filter(usuario=request.user, tipo=tipo)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"tipo": f"Ya tienes una lista de tipo '{tipo}'."}
                )
        return attrs


class ListaDetalleSerializer(ListaSerializer):
    elementos = ElementoListaSerializer(
        source="elementos_lista", many=True, read_only=True
    )

    class Meta(ListaSerializer.Meta):
        fields = ListaSerializer.Meta.fields + ("elementos",)


class AgregarElementoSerializer(serializers.Serializer):
    media_id = serializers.IntegerField(required=True)
    orden = serializers.IntegerField(required=False, default=0)

