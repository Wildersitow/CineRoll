from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from media.models import Media
from social.models import Resena
from social.serializers import ResenaSerializer
from usuarios.permissions import EsAutorOLecturaPublica

MENSAJE_RESENA_REPETIDA = (
    "Ya reseñaste este título. Edita tu reseña existente en lugar de crear otra."
)


class MediaResenaListCreateView(ListCreateAPIView):
    """GET: reseñas visibles de un título (público, paginado). POST: crear la propia."""

    serializer_class = ResenaSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get_media(self):
        if not hasattr(self, "_media"):
            self._media = get_object_or_404(Media, pk=self.kwargs["media_id"])
        return self._media

    def get_queryset(self):
        return (
            Resena.objects.visibles()
            .filter(media=self.get_media())
            .select_related("usuario", "media")
        )

    def perform_create(self, serializer):
        media = self.get_media()
        usuario = self.request.user
        if Resena.objects.filter(usuario=usuario, media=media).exists():
            raise ValidationError({"detail": MENSAJE_RESENA_REPETIDA})
        try:
            with transaction.atomic():
                serializer.save(usuario=usuario, media=media)
        except IntegrityError:  # dos peticiones simultáneas del mismo usuario
            raise ValidationError({"detail": MENSAJE_RESENA_REPETIDA})


class ResenaDetailView(RetrieveUpdateDestroyAPIView):
    """Ver una reseña (público); editarla o borrarla solo su autor."""

    queryset = Resena.objects.visibles().select_related("usuario")
    serializer_class = ResenaSerializer
    permission_classes = (EsAutorOLecturaPublica,)
    campo_autor = "usuario"


class MiResenaMediaView(APIView):
    """
    Retorna la reseña propia del usuario autenticado para un título específico.
    GET /api/media/<media_id>/resenas/propia/ o /api/media/<media_id>/resena-propia/
    Permite al frontend saber si el usuario ya reseñó y precargar su reseña para editarla.
    Requiere autenticación (401 si no está autenticado).
    Si el usuario no ha reseñado el título, devuelve 404.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, media_id):
        media = get_object_or_404(Media, pk=media_id)
        resena = (
            Resena.objects.visibles()
            .filter(media=media, usuario=request.user)
            .select_related("usuario", "media")
            .first()
        )
        if not resena:
            raise NotFound("No has reseñado este título.")
        serializer = ResenaSerializer(resena)
        return Response(serializer.data, status=status.HTTP_200_OK)
