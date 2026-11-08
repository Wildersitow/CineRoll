from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly

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
            .select_related("usuario")
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
