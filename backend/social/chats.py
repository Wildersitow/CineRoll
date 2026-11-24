"""Chat: mensajes privados entre usuarios y sala pública de cada título.

Rutas (todas bajo /api/):
  GET  chats/                       bandeja: una fila por conversación privada.
  GET  chats/usuarios/<username>/   mensajes con esa persona.
  POST chats/usuarios/<username>/   enviar un mensaje privado.
  GET  chats/media/<id>/            mensajes de la sala del título (público).
  POST chats/media/<id>/            escribir en la sala (requiere sesión).

Paginación por cursor, pensada para el sondeo cada pocos segundos del frontend:
  - sin parámetros: los últimos POR_PAGINA mensajes.
  - ?despues=<id>: los siguientes después de ese id (para traer lo nuevo).
  - ?antes=<id>:   los anteriores a ese id (para "Cargar mensajes anteriores").
Respuesta: {"results": [...], "hay_anteriores": bool, "hay_mas": bool}, siempre
del más antiguo al más nuevo.
"""
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Case, F, Max, Q, When
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from media.models import Media
from social.models import LONGITUD_MAXIMA_MENSAJE, Mensaje

Usuario = get_user_model()

POR_PAGINA = 50


class MensajeSerializer(serializers.ModelSerializer):
    autor = serializers.CharField(source="autor.username", read_only=True)
    autor_avatar = serializers.CharField(source="autor.avatar", read_only=True)

    class Meta:
        model = Mensaje
        fields = ("id", "autor", "autor_avatar", "texto", "fecha")
        read_only_fields = fields


class NuevoMensajeSerializer(serializers.Serializer):
    texto = serializers.CharField(max_length=LONGITUD_MAXIMA_MENSAJE, trim_whitespace=True)
    envio = serializers.UUIDField(required=False, allow_null=True)


def _cursor(request, nombre):
    valor = request.query_params.get(nombre)
    if valor in (None, ""):
        return None
    try:
        numero = int(valor)
    except ValueError:
        raise ValidationError({nombre: "Debe ser un número entero."})
    if numero < 0:
        raise ValidationError({nombre: "Debe ser un número positivo."})
    return numero


def pagina_de_mensajes(request, queryset):
    queryset = queryset.select_related("autor")
    despues = _cursor(request, "despues")
    antes = _cursor(request, "antes")

    if despues is not None:
        filas = list(queryset.filter(id__gt=despues).order_by("id")[: POR_PAGINA + 1])
        hay_mas = len(filas) > POR_PAGINA
        filas = filas[:POR_PAGINA]
        hay_anteriores = queryset.filter(id__lte=despues).exists()
    else:
        base = queryset.filter(id__lt=antes) if antes is not None else queryset
        filas = list(base.order_by("-id")[: POR_PAGINA + 1])
        hay_anteriores = len(filas) > POR_PAGINA
        filas = filas[:POR_PAGINA][::-1]
        hay_mas = False

    return Response(
        {
            "results": MensajeSerializer(filas, many=True).data,
            "hay_anteriores": hay_anteriores,
            "hay_mas": hay_mas,
        }
    )


def crear_mensaje(request, **destino):
    datos = NuevoMensajeSerializer(data=request.data)
    datos.is_valid(raise_exception=True)
    envio = datos.validated_data.get("envio")

    if envio is not None:
        previo = Mensaje.objects.filter(autor=request.user, envio=envio).first()
        if previo is not None:
            return Response(MensajeSerializer(previo).data, status=status.HTTP_200_OK)

    try:
        with transaction.atomic():
            mensaje = Mensaje.objects.create(
                autor=request.user, texto=datos.validated_data["texto"], envio=envio, **destino
            )
    except IntegrityError:
        # Dos peticiones con el mismo `envio` a la vez: gana la primera.
        mensaje = Mensaje.objects.get(autor=request.user, envio=envio)
        return Response(MensajeSerializer(mensaje).data, status=status.HTTP_200_OK)
    return Response(MensajeSerializer(mensaje).data, status=status.HTTP_201_CREATED)


class BandejaChatsView(APIView):
    """GET /api/chats/: conversaciones privadas, la más reciente primero."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        yo = request.user
        ultimos = (
            Mensaje.objects.filter(Q(autor=yo) | Q(destinatario=yo), destinatario__isnull=False)
            .annotate(otro=Case(When(autor=yo, then=F("destinatario")), default=F("autor")))
            .values("otro")
            .annotate(ultimo=Max("id"))
            .values_list("ultimo", flat=True)
        )
        mensajes = (
            Mensaje.objects.filter(id__in=list(ultimos))
            .select_related("autor", "destinatario")
            .order_by("-id")
        )
        filas = []
        for mensaje in mensajes:
            otro = mensaje.destinatario if mensaje.autor_id == yo.pk else mensaje.autor
            filas.append(
                {
                    "usuario": otro.username,
                    "nombre": otro.get_full_name() or otro.username,
                    "avatar": otro.avatar,
                    "ultimo_mensaje": {
                        "texto": mensaje.texto,
                        "fecha": serializers.DateTimeField().to_representation(mensaje.fecha),
                        "mio": mensaje.autor_id == yo.pk,
                    },
                }
            )
        return Response(filas)


class ChatPrivadoView(APIView):
    """GET/POST /api/chats/usuarios/<username>/: conversación con otra persona."""

    permission_classes = (IsAuthenticated,)

    def get_otro(self, request, username):
        otro = get_object_or_404(Usuario, username=username, is_active=True)
        if otro.pk == request.user.pk:
            raise ValidationError({"usuario": "No puedes enviarte mensajes a ti mismo."})
        return otro

    def get(self, request, username):
        otro = self.get_otro(request, username)
        yo = request.user
        conversacion = Mensaje.objects.filter(
            Q(autor=yo, destinatario=otro) | Q(autor=otro, destinatario=yo)
        )
        return pagina_de_mensajes(request, conversacion)

    def post(self, request, username):
        return crear_mensaje(request, destinatario=self.get_otro(request, username))


class SalaMediaView(APIView):
    """GET/POST /api/chats/media/<id>/: sala pública sobre un título."""

    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, media_id):
        media = get_object_or_404(Media, pk=media_id)
        return pagina_de_mensajes(request, Mensaje.objects.filter(media=media))

    def post(self, request, media_id):
        return crear_mensaje(request, media=get_object_or_404(Media, pk=media_id))
