from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from social.models import Resena, Seguimiento
from social.serializers import ResenaSerializer

Usuario = get_user_model()


class UsuarioSeguimientoSerializer(serializers.ModelSerializer):
    """Representación resumida de un usuario para listas de seguidores y seguidos."""

    nombre = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ["id", "username", "nombre", "avatar"]

    def get_nombre(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class SeguirUsuarioView(APIView):
    """
    POST: Seguir a un usuario (201 si es nuevo, 200 si ya lo seguía).
    DELETE: Dejar de seguir a un usuario (204 idempotente).
    Seguirse a sí mismo devuelve 400.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, username):
        target_user = get_object_or_404(Usuario, username=username)
        if request.user == target_user:
            raise ValidationError({"detail": "No puedes seguirte a ti mismo."})

        seguimiento, created = Seguimiento.objects.get_or_create(
            seguidor=request.user, seguido=target_user
        )
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        mensaje = (
            f"Ahora sigues a {target_user.username}."
            if created
            else f"Ya sigues a {target_user.username}."
        )
        return Response({"mensaje": mensaje}, status=status_code)

    def delete(self, request, username):
        target_user = get_object_or_404(Usuario, username=username)
        if request.user == target_user:
            raise ValidationError({"detail": "No puedes dejar de seguirte a ti mismo."})

        Seguimiento.objects.filter(
            seguidor=request.user, seguido=target_user
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SeguidoresListView(ListAPIView):
    """
    Listado paginado de usuarios que siguen a un usuario específico.
    GET /api/usuarios/<username>/seguidores/
    """

    serializer_class = UsuarioSeguimientoSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        target_user = get_object_or_404(Usuario, username=self.kwargs["username"])
        return (
            Usuario.objects.filter(siguiendo__seguido=target_user)
            .order_by("-siguiendo__fecha_creacion", "-id")
        )


class SiguiendoListView(ListAPIView):
    """
    Listado paginado de usuarios a los que sigue un usuario específico.
    GET /api/usuarios/<username>/siguiendo/
    """

    serializer_class = UsuarioSeguimientoSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        target_user = get_object_or_404(Usuario, username=self.kwargs["username"])
        return (
            Usuario.objects.filter(seguidores__seguidor=target_user)
            .order_by("-seguidores__fecha_creacion", "-id")
        )


class FeedActividadView(ListAPIView):
    """
    Feed de actividad del usuario autenticado.
    GET /api/usuarios/me/feed/
    Devuelve las reseñas visibles más recientes de los usuarios a quienes sigo.
    """

    serializer_class = ResenaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        siguiendo_ids = Seguimiento.objects.filter(
            seguidor=self.request.user
        ).values_list("seguido_id", flat=True)
        return (
            Resena.objects.visibles()
            .filter(usuario_id__in=siguiendo_ids)
            .select_related("usuario", "media")
            .order_by("-fecha_creacion", "-id")
        )
