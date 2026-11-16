from rest_framework import serializers

from social.models import ElementoLista, Lista, Resena


class ResenaSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.username", read_only=True)
    usuario_id = serializers.IntegerField(read_only=True)
    media_id = serializers.IntegerField(read_only=True)
    media_titulo = serializers.CharField(source="media.titulo", read_only=True)
    media_poster_url = serializers.CharField(source="media.poster_url", read_only=True)
    media_tipo = serializers.CharField(source="media.tipo", read_only=True)

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

