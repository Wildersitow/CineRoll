from django.db.models import Max
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from cines.models import Cine, Funcion
from cines.serializers import CineSerializer, FuncionSerializer
from media.models import Media
from usuarios.permissions import EsAdministradorOLecturaPublica


class CineListView(ListCreateAPIView):
    queryset = Cine.objects.all()
    serializer_class = CineSerializer
    permission_classes = (EsAdministradorOLecturaPublica,)


class CineDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Cine.objects.all()
    serializer_class = CineSerializer
    permission_classes = (EsAdministradorOLecturaPublica,)


class UnpaginatedFuncionListView(ListAPIView):
    pagination_class = None

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({"resultados": serializer.data})


class FuncionListView(UnpaginatedFuncionListView):
    serializer_class = FuncionSerializer
    permission_classes = (EsAdministradorOLecturaPublica,)

    def get_queryset(self):
        queryset = Funcion.objects.select_related("cine", "media")
        show_date = self.request.query_params.get("fecha", "hoy")
        queryset = _filter_by_date(queryset, show_date)

        city = self.request.query_params.get("ciudad")
        if city is not None:
            if not city.strip():
                raise ValidationError({"ciudad": "Debe indicar una ciudad."})
            queryset = queryset.filter(cine__ciudad__iexact=city.strip())

        return queryset.order_by("fecha_hora", "cine__nombre", "sala")


class CineFuncionListView(UnpaginatedFuncionListView):
    serializer_class = FuncionSerializer
    permission_classes = (EsAdministradorOLecturaPublica,)

    def get_queryset(self):
        cine = get_object_or_404(Cine, pk=self.kwargs["cine_id"])
        queryset = Funcion.objects.filter(cine=cine).select_related("cine", "media")
        show_date = self.request.query_params.get("fecha", "hoy")
        queryset = _filter_by_date(queryset, show_date)
        return queryset.order_by("fecha_hora", "sala", "media__titulo")


class MediaFuncionListView(APIView):
    permission_classes = (EsAdministradorOLecturaPublica,)

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
            queryset = _filter_by_date(queryset, show_date)

        queryset = queryset.order_by("fecha_hora", "cine__nombre", "sala")
        return Response(
            {
                "ultima_actualizacion": ultima_actualizacion,
                "resultados": FuncionSerializer(queryset, many=True).data,
            }
        )


def _filter_by_date(queryset, show_date):
    if show_date.casefold() == "hoy":
        parsed_date = timezone.localdate()
        return queryset.filter(fecha_hora__date=parsed_date)
    try:
        parsed_date = parse_date(show_date)
    except ValueError:
        parsed_date = None
    if parsed_date is None:
        raise ValidationError({"fecha": "Debe tener formato AAAA-MM-DD."})
    return queryset.filter(fecha_hora__date=parsed_date)
