from django.db.models import Max
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from cines.models import Cine, Funcion
from cines.serializers import CineSerializer, FuncionSerializer
from media.models import Media


class CineListView(ListAPIView):
    queryset = Cine.objects.all()
    serializer_class = CineSerializer
    permission_classes = (AllowAny,)


class MediaFuncionListView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, media_id):
        media = get_object_or_404(Media, pk=media_id)
        queryset = Funcion.objects.filter(media=media).select_related("cine", "media")

        cinema_id = request.query_params.get("cine")
        if cinema_id is not None:
            if not cinema_id.isdecimal() or int(cinema_id) < 1:
                raise ValidationError({"cine": "Debe ser un identificador de cine válido."})
            queryset = queryset.filter(cine_id=int(cinema_id))

        ultima_actualizacion = queryset.aggregate(
            ultima_actualizacion=Max("fecha_actualizacion")
        )["ultima_actualizacion"]

        show_date = request.query_params.get("fecha")
        if show_date is not None:
            try:
                parsed_date = parse_date(show_date)
            except ValueError:
                parsed_date = None
            if parsed_date is None:
                raise ValidationError({"fecha": "Debe tener formato AAAA-MM-DD."})
            queryset = queryset.filter(fecha_hora__date=parsed_date)

        queryset = queryset.order_by("fecha_hora", "cine__nombre", "sala")
        return Response(
            {
                "ultima_actualizacion": ultima_actualizacion,
                "resultados": FuncionSerializer(queryset, many=True).data,
            }
        )
