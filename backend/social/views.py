from django.contrib.auth import get_user_model
from django.db import IntegrityError, models, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import (
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from media.models import Media
from social.models import ElementoLista, Lista, Resena
from social.serializers import (
    AgregarElementoSerializer,
    ElementoListaSerializer,
    ListaDetalleSerializer,
    ListaSerializer,
    ResenaSerializer,
)
from usuarios.permissions import EsAutorOLecturaPublica

Usuario = get_user_model()


MENSAJE_RESENA_REPETIDA = (
    "Ya reseñaste este título. Edita tu reseña existente en lugar de crear otra."
)

def listas_con_total():
    return Lista.objects.select_related("usuario").annotate(
        total_elementos_anotado=models.Count("elementos_lista")
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


class ListaListCreateView(ListCreateAPIView):
    """
    GET: listar listas (propias si está autenticado; públicas si se filtra o es anónimo).
    Filtros opcionales: ?usuario=<username>, ?usuario_id=<id>, ?tipo=<tipo>.
    POST: crear una nueva lista propia.
    """

    serializer_class = ListaSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        qs = listas_con_total()
        username = self.request.query_params.get("usuario")
        usuario_id = self.request.query_params.get("usuario_id")
        tipo = self.request.query_params.get("tipo")

        if username:
            target_user = get_object_or_404(Usuario, username=username)
            if self.request.user.is_authenticated and self.request.user == target_user:
                qs = qs.filter(usuario=target_user)
            else:
                qs = qs.filter(usuario=target_user, publica=True)
        elif usuario_id:
            target_user = get_object_or_404(Usuario, pk=usuario_id)
            if self.request.user.is_authenticated and self.request.user == target_user:
                qs = qs.filter(usuario=target_user)
            else:
                qs = qs.filter(usuario=target_user, publica=True)
        else:
            if self.request.user.is_authenticated:
                qs = qs.filter(usuario=self.request.user)
            else:
                qs = qs.filter(publica=True)

        if tipo:
            qs = qs.filter(tipo=tipo)

        return qs

    def perform_create(self, serializer):
        tipo = serializer.validated_data.get("tipo", Lista.Tipo.PERSONALIZADA)
        if tipo in [Lista.Tipo.FAVORITAS, Lista.Tipo.POR_VER]:
            if Lista.objects.filter(usuario=self.request.user, tipo=tipo).exists():
                raise ValidationError({"tipo": f"Ya tienes una lista de tipo '{tipo}'."})
        try:
            with transaction.atomic():
                serializer.save(usuario=self.request.user)
        except IntegrityError:
            raise ValidationError({"tipo": f"Ya tienes una lista de tipo '{tipo}'."})


class ListaDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: ver detalle de una lista (incluyendo sus elementos).
    PUT/PATCH: editar lista (solo su autor).
    DELETE: borrar lista (solo su autor).
    """

    permission_classes = (EsAutorOLecturaPublica,)
    campo_autor = "usuario"

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListaDetalleSerializer
        return ListaSerializer

    def get_queryset(self):
        qs = Lista.objects.select_related("usuario").prefetch_related(
            "elementos_lista__media"
        )
        if self.request.user.is_authenticated:
            return qs.filter(
                models.Q(publica=True) | models.Q(usuario=self.request.user)
            )
        return qs.filter(publica=True)


class ListaElementoListCreateView(APIView):
    """
    GET: listar elementos de una lista.
    POST: agregar un título a una lista (solo su autor).
    DELETE: quitar un título de la lista pasando media_id en el cuerpo o query param.
    """

    def get_lista(self, lista_id):
        lista = get_object_or_404(
            Lista.objects.select_related("usuario").prefetch_related(
                "elementos_lista__media"
            ),
            pk=lista_id,
        )
        autenticado = self.request.user.is_authenticated
        es_autor = autenticado and lista.usuario == self.request.user

        if self.request.method != "GET" and not autenticado:
            raise NotAuthenticated()
        if not lista.publica and not es_autor:
            raise NotFound()
        if self.request.method != "GET" and not es_autor:
            raise PermissionDenied("No tienes permiso para modificar esta lista.")
        return lista

    def get(self, request, lista_id):
        lista = self.get_lista(lista_id)
        elementos = lista.elementos_lista.select_related("media").all()
        serializer = ElementoListaSerializer(elementos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, lista_id):
        lista = self.get_lista(lista_id)
        serializer = AgregarElementoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        media_id = serializer.validated_data["media_id"]
        orden = serializer.validated_data.get("orden", 0)

        media = get_object_or_404(Media, pk=media_id)

        if ElementoLista.objects.filter(lista=lista, media=media).exists():
            raise ValidationError({"detail": "El título ya está en la lista."})

        try:
            with transaction.atomic():
                elemento = ElementoLista.objects.create(
                    lista=lista, media=media, orden=orden
                )
        except IntegrityError:
            raise ValidationError({"detail": "El título ya está en la lista."})

        return Response(
            ElementoListaSerializer(elemento).data,
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, lista_id):
        lista = self.get_lista(lista_id)
        media_id = request.data.get("media_id") or request.query_params.get("media_id")
        if not media_id:
            raise ValidationError({"detail": "Se requiere media_id para eliminar el elemento."})

        elemento = get_object_or_404(ElementoLista, lista=lista, media_id=media_id)
        elemento.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListaElementoDetailView(APIView):
    """
    DELETE: quitar un título de la lista mediante /api/listas/<lista_id>/elementos/<media_id>/
    """

    def delete(self, request, lista_id, media_id):
        lista = get_object_or_404(Lista.objects.select_related("usuario"), pk=lista_id)
        if not request.user.is_authenticated:
            raise NotAuthenticated()
        if lista.usuario != request.user:
            if not lista.publica:
                raise NotFound()
            raise PermissionDenied("No tienes permiso para modificar esta lista.")

        elemento = get_object_or_404(ElementoLista, lista=lista, media_id=media_id)
        elemento.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UsuarioListasListView(APIView):
    """
    GET: obtener las listas de un usuario.
    Si quien consulta es el mismo usuario, devuelve todas sus listas.
    Si es otro usuario o visitante, solo devuelve las listas públicas.
    """

    def get(self, request, username):
        target_user = get_object_or_404(Usuario, username=username)
        listas = listas_con_total().filter(usuario=target_user)
        if not (request.user.is_authenticated and request.user == target_user):
            listas = listas.filter(publica=True)

        serializer = ListaSerializer(listas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MisListasView(APIView):
    """
    GET: todas las listas del usuario autenticado (/api/usuarios/me/listas/).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        listas = listas_con_total().filter(usuario=request.user)
        serializer = ListaSerializer(listas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)