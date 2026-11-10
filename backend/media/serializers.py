from rest_framework import serializers

from media.models import Credito, Genero, Media, Persona
from social.services import resumen_puntuacion


class GeneroSerializer(serializers.ModelSerializer):
	class Meta:
		model = Genero
		fields = ("id", "nombre")


class PersonaSerializer(serializers.ModelSerializer):
	class Meta:
		model = Persona
		fields = ("id", "nombre")


class PersonaCrudSerializer(serializers.ModelSerializer):
	class Meta:
		model = Persona
		fields = ("id", "nombre", "biografia", "fecha_nacimiento")


class MediaWriteSerializer(serializers.ModelSerializer):
	generos = serializers.PrimaryKeyRelatedField(
		many=True, queryset=Genero.objects.all(), required=False
	)

	class Meta:
		model = Media
		fields = (
			"id",
			"titulo",
			"titulo_original",
			"tipo",
			"sinopsis",
			"fecha_estreno",
			"duracion",
			"poster_url",
			"trailer_url",
			"estado",
			"generos",
		)


class MediaListSerializer(serializers.ModelSerializer):
	generos = GeneroSerializer(many=True, read_only=True)
	promedio_puntuacion = serializers.SerializerMethodField()
	total_votos = serializers.SerializerMethodField()

	class Meta:
		model = Media
		fields = (
			"id",
			"titulo",
			"titulo_original",
			"sinopsis",
			"fecha_estreno",
			"duracion",
			"poster_url",
			"trailer_url",
			"tipo",
			"estado",
			"generos",
			"promedio_puntuacion",
			"total_votos",
		)

	def get_promedio_puntuacion(self, obj):
		return self._resumen(obj)["promedio"]

	def get_total_votos(self, obj):
		return self._resumen(obj)["total_votos"]

	@staticmethod
	def _resumen(obj):
		"""Usa las anotaciones de la vista; si no existen, consulta el servicio."""
		if hasattr(obj, "total_votos") and hasattr(obj, "promedio_puntuacion"):
			promedio = obj.promedio_puntuacion
			return {
				"promedio": None if promedio is None else round(promedio, 2),
				"total_votos": obj.total_votos,
			}
		return resumen_puntuacion(obj.pk)


class MediaDetailSerializer(MediaListSerializer):
	reparto = serializers.SerializerMethodField()
	directores = serializers.SerializerMethodField()

	class Meta(MediaListSerializer.Meta):
		fields = MediaListSerializer.Meta.fields + ("reparto", "directores")

	def get_reparto(self, obj):
		return self._personas_por_rol(obj, Credito.Rol.ACTOR)

	def get_directores(self, obj):
		return self._personas_por_rol(obj, Credito.Rol.DIRECTOR)

	@staticmethod
	def _personas_por_rol(obj, rol):
		personas = [
			credito.persona
			for credito in obj.creditos.all()
			if credito.rol == rol
		]
		return PersonaSerializer(personas, many=True).data
