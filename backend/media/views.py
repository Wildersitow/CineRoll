import unicodedata

from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import (
	ListCreateAPIView,
	RetrieveUpdateDestroyAPIView,
)

from cines.models import Funcion
from cines.views import _filter_by_city as filtrar_por_ciudad
from cines.views import _filter_by_date as filtrar_por_fecha
from media.models import Genero, Media, Persona
from usuarios.permissions import EsAdministradorOLecturaPublica
from media.serializers import (
	GeneroSerializer,
	MediaDetailSerializer,
	MediaListSerializer,
	MediaWriteSerializer,
	PersonaCrudSerializer,
	PersonaDetailSerializer,
)
from social.services import anotar_puntuacion


class MediaListView(ListCreateAPIView):
	queryset = anotar_puntuacion(Media.objects.prefetch_related("generos"))
	serializer_class = MediaListSerializer
	permission_classes = (EsAdministradorOLecturaPublica,)
	filter_backends = (SearchFilter, OrderingFilter)
	search_fields = ("titulo", "titulo_original", "sinopsis")
	ordering_fields = ("fecha_estreno", "titulo", "promedio_puntuacion")

	def get_serializer_class(self):
		if self.request.method == "POST":
			return MediaWriteSerializer
		return super().get_serializer_class()

	def get_queryset(self):
		queryset = super().get_queryset()
		params = self.request.query_params

		genero = params.get("genero")
		if genero:
			genero_normalizado = self._normalizar_texto(genero)
			genero_ids = [
				genero_id
				for genero_id, nombre in Genero.objects.values_list("id", "nombre")
				if self._normalizar_texto(nombre) == genero_normalizado
			]
			if genero_ids:
				queryset = queryset.filter(generos__id__in=genero_ids).distinct()
			else:
				queryset = queryset.none()

		tipo = params.get("tipo")
		if tipo:
			if tipo not in Media.Tipo.values:
				raise ValidationError({"tipo": "Tipo de media no válido."})
			queryset = queryset.filter(tipo=tipo)

		anio = params.get("anio")
		if anio:
			if not anio.isdecimal() or not 1 <= int(anio) <= 9999:
				raise ValidationError({"anio": "Debe ser un año válido."})
			queryset = queryset.filter(fecha_estreno__year=int(anio))

		estado = params.get("estado")
		if estado:
			if estado not in Media.Estado.values:
				raise ValidationError({"estado": "Estado de media no válido."})
			queryset = queryset.filter(estado=estado)

		# Filtros de cartelera: cine, ciudad y fecha se aplican sobre la MISMA
		# función (p. ej. "tiene función en el cine X el día Y"), por eso se
		# construye un único queryset de funciones y se filtra por sus media_id.
		funciones = None

		cine = params.get("cine")
		if cine is not None:
			if not cine.isdecimal() or int(cine) < 1:
				raise ValidationError({"cine": "Debe ser un identificador de cine válido."})
			funciones = Funcion.objects.filter(cine_id=int(cine))

		ciudad = params.get("ciudad")
		if ciudad is not None:
			funciones = filtrar_por_ciudad(
				funciones if funciones is not None else Funcion.objects.all(),
				ciudad,
			)

		fecha = params.get("fecha")
		if fecha is not None:
			funciones = filtrar_por_fecha(
				funciones if funciones is not None else Funcion.objects.all(),
				fecha,
			)

		if funciones is not None:
			queryset = queryset.filter(id__in=funciones.values("media_id"))

		min_votos = params.get("min_votos")
		if min_votos is not None:
			if not min_votos.isdecimal():
				raise ValidationError({"min_votos": "Debe ser un entero no negativo."})
			queryset = queryset.filter(total_votos__gte=int(min_votos))

		return queryset

	@staticmethod
	def _normalizar_texto(texto):
		texto_descompuesto = unicodedata.normalize("NFKD", texto.casefold())
		return "".join(
			caracter
			for caracter in texto_descompuesto
			if not unicodedata.combining(caracter)
		)


class MediaDetailView(RetrieveUpdateDestroyAPIView):
	queryset = anotar_puntuacion(
		Media.objects.prefetch_related("generos", "creditos__persona")
	)
	serializer_class = MediaDetailSerializer
	permission_classes = (EsAdministradorOLecturaPublica,)

	def get_serializer_class(self):
		if self.request.method in ("PUT", "PATCH"):
			return MediaWriteSerializer
		return super().get_serializer_class()


class GeneroListView(ListCreateAPIView):
	queryset = Genero.objects.all()
	serializer_class = GeneroSerializer
	permission_classes = (EsAdministradorOLecturaPublica,)


class GeneroDetailView(RetrieveUpdateDestroyAPIView):
	queryset = Genero.objects.all()
	serializer_class = GeneroSerializer
	permission_classes = (EsAdministradorOLecturaPublica,)


class PersonaListView(ListCreateAPIView):
	queryset = Persona.objects.all()
	serializer_class = PersonaCrudSerializer
	permission_classes = (EsAdministradorOLecturaPublica,)


class PersonaDetailView(RetrieveUpdateDestroyAPIView):
	queryset = Persona.objects.prefetch_related("creditos__media")
	serializer_class = PersonaDetailSerializer
	permission_classes = (EsAdministradorOLecturaPublica,)
