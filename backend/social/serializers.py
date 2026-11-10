from rest_framework import serializers

from social.models import Resena


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
