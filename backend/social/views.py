from django.contrib.auth import get_user_model
from django.db import IntegrityError, models, transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import (
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from media.models import Media
from social.models import (
    ComentarioResena,
    ElementoLista,
    LikeResena,
    Lista,
    RegistroTitulo,
    ReporteResena,
    Resena,
    SugerenciaEdicion,
)
from social.serializers import (
    ComentarioResenaSerializer,
    AgregarElementoSerializer,
    ElementoListaSerializer,
    ListaDetalleSerializer,
    ListaSerializer,
    ReporteResenaSerializer,
    ResenaSerializer,
    ResolverSugerenciaSerializer,
    SugerenciaEdicionSerializer,
)
from social.registro import actualizar_registro, datos_registro, registrar_resena
from social.resenas import anotar_resenas, estadisticas_media
from social.services import resumen_puntuacion
from social.sugerencias import aprobar_sugerencia, rechazar_sugerencia
from usuarios.permissions import EsAdministrador, EsAutorOLecturaPublica

Usuario = get_user_model()


MENSAJE_RESENA_REPETIDA = (
    "Ya reseñaste este título. Edita tu reseña existente en lugar de crear otra."
)
MENSAJE_REPORTE_RESENA_REPETIDO = "Ya reportaste esta reseña."


def listas_con_total():
    return (
        Lista.objects.select_related("usuario")
        .annotate(total_elementos_anotado=models.Count("elementos_lista"))
        .order_by("-fecha_creacion", "-id")
    )


class MediaResenaListCreateView(ListCreateAPIView):
    """GET: reseñas visibles de un título (público, paginado). POST: crear la propia."""

    serializer_class = ResenaSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get_media(self):
        if not hasattr(self, "_media"):
            self._media = get_object_or_404(Media, pk=self.kwargs["media_id"])
        return self._media

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["media"] = self.get_media()
        return context

    def get_queryset(self):
        return anotar_resenas(
            Resena.objects.visibles()
            .filter(media=self.get_media())
            .select_related("usuario", "media"),
            self.request.user,
        )

    def perform_create(self, serializer):
        media = self.get_media()
        usuario = self.request.user
        if Resena.objects.filter(usuario=usuario, media=media).exists():
            raise ValidationError({"detail": MENSAJE_RESENA_REPETIDA})
        try:
            with transaction.atomic():
                serializer.save(usuario=usuario, media=media)
                registrar_resena(usuario, media)
        except IntegrityError:  # dos peticiones simultáneas del mismo usuario
            raise ValidationError({"detail": MENSAJE_RESENA_REPETIDA})


class ResenasListView(ListAPIView):
    serializer_class = ResenaSerializer
    permission_classes = (AllowAny,)
    http_method_names = ("get", "head", "options")

    def get_queryset(self):
        queryset = Resena.objects.visibles().select_related("usuario", "media")

        con_texto = self.request.query_params.get("con_texto")
        if con_texto is not None:
            valor = con_texto.casefold()
            if valor not in {"true", "false"}:
                raise ValidationError(
                    {"con_texto": "Debe ser 'true' o 'false'."}
                )
            if valor == "true":
                queryset = queryset.exclude(texto="")
            else:
                queryset = queryset.filter(texto="")

        media_id = self.request.query_params.get("media")
        if media_id is not None:
            if not media_id.isdecimal() or int(media_id) < 1:
                raise ValidationError(
                    {"media": "Debe ser un identificador de título válido."}
                )
            queryset = queryset.filter(media_id=int(media_id))

        return anotar_resenas(queryset, self.request.user).order_by("-fecha_creacion", "-pk")


class ResenaLikeView(APIView):
    """
    PUT /api/resenas/<pk>/like/    marca "me gusta" (idempotente).
    DELETE /api/resenas/<pk>/like/ lo quita.
    Responde {"resena_id", "me_gusta", "total_likes"}.
    """

    permission_classes = (IsAuthenticated,)

    def responder(self, request, resena):
        return Response(
            {
                "resena_id": resena.pk,
                "me_gusta": resena.likes.filter(usuario=request.user).exists(),
                "total_likes": resena.likes.count(),
            }
        )

    def put(self, request, pk):
        resena = get_object_or_404(Resena.objects.visibles(), pk=pk)
        LikeResena.objects.get_or_create(usuario=request.user, resena=resena)
        return self.responder(request, resena)

    def delete(self, request, pk):
        resena = get_object_or_404(Resena.objects.visibles(), pk=pk)
        LikeResena.objects.filter(usuario=request.user, resena=resena).delete()
        return self.responder(request, resena)


class ResenaComentariosView(ListCreateAPIView):
    """GET: comentarios de una reseña (público, paginado, del más antiguo al más nuevo). POST: comentar."""

    serializer_class = ComentarioResenaSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get_resena(self):
        if not hasattr(self, "_resena"):
            self._resena = get_object_or_404(Resena.objects.visibles(), pk=self.kwargs["pk"])
        return self._resena

    def get_queryset(self):
        return ComentarioResena.objects.filter(resena=self.get_resena()).select_related("usuario")

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user, resena=self.get_resena())


class ComentarioResenaDetailView(APIView):
    """DELETE /api/comentarios/<pk>/: lo borra su autor o el autor de la reseña."""

    permission_classes = (IsAuthenticated,)

    def delete(self, request, pk):
        comentario = get_object_or_404(
            ComentarioResena.objects.select_related("resena"), pk=pk
        )
        if request.user.pk not in (comentario.usuario_id, comentario.resena.usuario_id):
            raise PermissionDenied("Solo puedes borrar tus comentarios o los de tu reseña.")
        comentario.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MediaEstadisticasView(APIView):
    """GET /api/media/<media_id>/estadisticas/: nota media, distribución y actividad."""

    permission_classes = (AllowAny,)

    def get(self, request, media_id):
        media = get_object_or_404(Media, pk=media_id)
        return Response(estadisticas_media(media))


class MediaResenaResumenView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, media_id):
        try:
            resumen = resumen_puntuacion(media_id)
        except Media.DoesNotExist as exc:
            raise NotFound("El título no existe.") from exc
        return Response(resumen)


class ResenaDetailView(RetrieveUpdateDestroyAPIView):
    """Ver una reseña (público); editarla o borrarla solo su autor."""

    queryset = Resena.objects.visibles().select_related("usuario")
    serializer_class = ResenaSerializer
    permission_classes = (EsAutorOLecturaPublica,)
    campo_autor = "usuario"


class ReportarResenaView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        resena = get_object_or_404(Resena.objects.visibles(), pk=pk)
        if ReporteResena.objects.filter(resena=resena, usuario=request.user).exists():
            raise ValidationError({"detail": MENSAJE_REPORTE_RESENA_REPETIDO})

        serializer = ReporteResenaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                reporte = serializer.save(resena=resena, usuario=request.user)
        except IntegrityError as exc:
            if not ReporteResena.objects.filter(
                resena=resena, usuario=request.user
            ).exists():
                raise
            raise ValidationError(
                {"detail": MENSAJE_REPORTE_RESENA_REPETIDO}
            ) from exc

        return Response(
            ReporteResenaSerializer(reporte).data,
            status=status.HTTP_201_CREATED,
        )


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

    def perform_destroy(self, instance):
        if instance.tipo in (Lista.Tipo.FAVORITAS, Lista.Tipo.POR_VER):
            raise ValidationError(
                {"detail": "Las listas Favoritas y Por ver no se pueden eliminar."}
            )
        super().perform_destroy(instance)

    def get_queryset(self):
        qs = Lista.objects.select_related("usuario").prefetch_related(
            "elementos_lista__media"
        )
        if self.request.user.is_authenticated:
            return qs.filter(
                models.Q(publica=True) | models.Q(usuario=self.request.user)
            )
        return qs.filter(publica=True)


class ListaElementoListCreateView(GenericAPIView):
    """
    GET: listar elementos de una lista.
    POST: agregar un título a una lista (solo su autor).
    DELETE: quitar un título de la lista pasando media_id en el cuerpo o query param.
    """

    serializer_class = AgregarElementoSerializer

    def get_lista(self, lista_id):
        lista = get_object_or_404(
            Lista.objects.select_related("usuario"),
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
        pagina = self.paginate_queryset(elementos)
        serializer = ElementoListaSerializer(pagina, many=True)
        return self.get_paginated_response(serializer.data)

    def post(self, request, lista_id):
        lista = self.get_lista(lista_id)
        serializer = self.get_serializer(data=request.data)
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

        valor = str(media_id)
        if not valor.isascii() or not valor.isdecimal():
            raise ValidationError(
                {"media_id": "Debe ser un identificador de título válido."}
            )
        campo_id = serializers.IntegerField(min_value=1, max_value=2**63 - 1)
        try:
            media_id = campo_id.run_validation(valor)
        except ValidationError as exc:
            raise ValidationError({"media_id": exc.detail}) from exc

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


class UsuarioListasListView(ListAPIView):
    """
    GET /api/usuarios/<username>/listas/
    Listado paginado de listas públicas de un usuario (o todas si quien consulta es el dueño).
    """

    serializer_class = ListaSerializer

    def get_queryset(self):
        target_user = get_object_or_404(Usuario, username=self.kwargs["username"])
        qs = listas_con_total().filter(usuario=target_user)
        if not (self.request.user.is_authenticated and self.request.user == target_user):
            qs = qs.filter(publica=True)
        return qs


class MisListasView(ListAPIView):
    """
    GET /api/usuarios/me/listas/
    Listado paginado de todas las listas del usuario autenticado.
    """

    serializer_class = ListaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return listas_con_total().filter(usuario=self.request.user)


class MediaMisListasView(APIView):
    """
    GET /api/media/<media_id>/mis-listas/
    Indica en cuáles listas del usuario autenticado está el título indicado
    (ej. favoritas, por ver o listas personalizadas).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, media_id):
        media = get_object_or_404(Media, pk=media_id)
        listas_con_titulo = (
            Lista.objects.filter(usuario=request.user, elementos=media)
            .values("id", "nombre", "tipo")
        )
        tipos_presentes = {lista["tipo"] for lista in listas_con_titulo}

        return Response(
            {
                "media_id": media.id,
                "en_favoritas": Lista.Tipo.FAVORITAS in tipos_presentes,
                "en_por_ver": Lista.Tipo.POR_VER in tipos_presentes,
                "listas": list(listas_con_titulo),
            },
            status=status.HTTP_200_OK,
        )


class RegistroTituloSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(
        choices=[("", "Sin estado"), *RegistroTitulo.Estado.choices], required=False
    )
    me_gusta = serializers.BooleanField(required=False)
    pendiente = serializers.BooleanField(required=False)


class MiRegistroMediaView(APIView):
    """
    GET /api/media/<media_id>/mi-registro/
        {"media_id", "estado": ""|"visto"|"viendo", "me_gusta", "pendiente"}
    PATCH con cualquiera de estado, me_gusta o pendiente; responde igual que GET.
    "pendiente" equivale a estar en la lista Por ver del usuario.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, media_id):
        media = get_object_or_404(Media, pk=media_id)
        return Response(datos_registro(request.user, media))

    def patch(self, request, media_id):
        media = get_object_or_404(Media, pk=media_id)
        serializer = RegistroTituloSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data:
            raise ValidationError(
                {"detail": "Envía al menos uno de: estado, me_gusta, pendiente."}
            )
        if (
            serializer.validated_data.get("estado")
            and media.estado == Media.Estado.PROXIMO_ESTRENO
        ):
            raise ValidationError(
                {"estado": "Aún no se estrena: puedes dejarlo pendiente o darle me gusta."}
            )
        return Response(
            actualizar_registro(request.user, media, serializer.validated_data)
        )


class MediaSugerenciaListCreateView(ListCreateAPIView):
    """Crea sugerencias y permite listar las pendientes de un título."""

    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = SugerenciaEdicionSerializer

    def get_media(self):
        if not hasattr(self, "_media"):
            self._media = get_object_or_404(Media, pk=self.kwargs["media_id"])
        return self._media

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["media"] = self.get_media()
        return context

    def get_queryset(self):
        queryset = SugerenciaEdicion.objects.select_related(
            "usuario", "media", "revisado_por"
        ).filter(media=self.get_media())
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            queryset = queryset.filter(usuario=self.request.user) if self.request.user.is_authenticated else queryset.none()
        estado = self.request.query_params.get("estado")
        if estado:
            if estado not in SugerenciaEdicion.Estado.values:
                raise ValidationError({"estado": "Estado de sugerencia no válido."})
            queryset = queryset.filter(estado=estado)
        return queryset

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save(usuario=self.request.user, media=self.get_media())
        except IntegrityError:
            raise ValidationError(
                {"detail": "Ya existe una sugerencia pendiente para este título y campo."}
            )


class SugerenciasModeracionView(ListAPIView):
    """Listado administrativo paginado de todas las sugerencias."""

    permission_classes = (EsAdministrador,)
    serializer_class = SugerenciaEdicionSerializer

    def get_queryset(self):
        queryset = SugerenciaEdicion.objects.select_related(
            "usuario", "media", "revisado_por"
        ).order_by("-fecha_creacion", "-id")

        estado = self.request.query_params.get("estado")
        if estado:
            if estado not in SugerenciaEdicion.Estado.values:
                raise ValidationError({"estado": "Estado de sugerencia no válido."})
            queryset = queryset.filter(estado=estado)

        media = self.request.query_params.get("media")
        if media:
            if not media.isdecimal() or int(media) < 1:
                raise ValidationError({"media": "Debe ser un identificador de título válido."})
            queryset = queryset.filter(media_id=int(media))

        return queryset


class AprobarSugerenciaView(APIView):
    permission_classes = (EsAdministrador,)

    def post(self, request, pk):
        sugerencia = get_object_or_404(
            SugerenciaEdicion.objects.select_related("usuario", "media", "revisado_por"),
            pk=pk,
        )
        sugerencia = aprobar_sugerencia(sugerencia, request.user)
        return Response(SugerenciaEdicionSerializer(sugerencia).data)


class RechazarSugerenciaView(APIView):
    permission_classes = (EsAdministrador,)

    def post(self, request, pk):
        sugerencia = get_object_or_404(
            SugerenciaEdicion.objects.select_related("usuario", "media", "revisado_por"),
            pk=pk,
        )
        serializer = ResolverSugerenciaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sugerencia = rechazar_sugerencia(
            sugerencia,
            request.user,
            motivo_rechazo=serializer.validated_data["motivo_rechazo"],
        )
        return Response(SugerenciaEdicionSerializer(sugerencia).data)
