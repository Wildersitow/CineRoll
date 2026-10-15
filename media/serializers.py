from rest_framework import serializers

from media.models import Credito, Genero, Media, Persona


class GeneroSerializer(serializers.ModelSerializer):
	class Meta:
		model = Genero
		fields = ("id", "nombre")


class PersonaSerializer(serializers.ModelSerializer):
	class Meta:
		model = Persona
		fields = ("id", "nombre")


class MediaListSerializer(serializers.ModelSerializer):
	generos = GeneroSerializer(many=True, read_only=True)

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
		)


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
