import unicodedata

from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView

from media.models import Genero, Media
from media.permissions import IsAdminOrReadOnly
from media.serializers import (
	GeneroSerializer,
	MediaDetailSerializer,
	MediaListSerializer,
)


class MediaListView(ListAPIView):
	queryset = Media.objects.prefetch_related("generos")
	serializer_class = MediaListSerializer
	permission_classes = (IsAdminOrReadOnly,)
	filter_backends = (SearchFilter,)
	search_fields = ("titulo", "titulo_original", "sinopsis")

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

		return queryset

	@staticmethod
	def _normalizar_texto(texto):
		texto_descompuesto = unicodedata.normalize("NFKD", texto.casefold())
		return "".join(
			caracter
			for caracter in texto_descompuesto
			if not unicodedata.combining(caracter)
		)


class MediaDetailView(RetrieveAPIView):
	queryset = Media.objects.prefetch_related("generos", "creditos__persona")
	serializer_class = MediaDetailSerializer
	permission_classes = (IsAdminOrReadOnly,)


class GeneroListView(ListAPIView):
	queryset = Genero.objects.all()
	serializer_class = GeneroSerializer
	permission_classes = (IsAdminOrReadOnly,)
