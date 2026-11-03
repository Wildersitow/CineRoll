from rest_framework import serializers

from cines.models import Cine, Funcion


class CineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cine
        fields = ("id", "nombre", "ciudad", "direccion", "sitio_web")


class FuncionSerializer(serializers.ModelSerializer):
    cine = CineSerializer(read_only=True)
    media_id = serializers.IntegerField(read_only=True)
    media_titulo = serializers.CharField(source="media.titulo", read_only=True)

    class Meta:
        model = Funcion
        fields = (
            "id",
            "media_id",
            "media_titulo",
            "cine",
            "fecha_hora",
            "sala",
            "formato",
            "fecha_actualizacion",
        )