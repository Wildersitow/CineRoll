from rest_framework import serializers

from media.models import Media
from media.serializers import MediaWriteSerializer
from social.models import (
    ComentarioResena,
    ElementoLista,
    Lista,
    RegistroTitulo,
    ReporteResena,
    Resena,
    SugerenciaEdicion,
)
from social.sugerencias import CAMPOS_SUGERENCIA_EDITABLES


MAX_RESENA_TEXTO_LENGTH = 5000


class ResenaSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.username", read_only=True)
    usuario_id = serializers.IntegerField(read_only=True)
    media_id = serializers.IntegerField(read_only=True)
    media_titulo = serializers.CharField(source="media.titulo", read_only=True)
    media_poster_url = serializers.CharField(source="media.poster_url", read_only=True)
    media_tipo = serializers.CharField(source="media.tipo", read_only=True)
    texto = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=MAX_RESENA_TEXTO_LENGTH,
    )
    usuario_avatar = serializers.CharField(source="usuario.avatar", read_only=True)
    total_likes = serializers.SerializerMethodField()
    me_gusta = serializers.SerializerMethodField()
    total_comentarios = serializers.SerializerMethodField()
    estado_autor = serializers.SerializerMethodField()
    autor_le_gusta = serializers.SerializerMethodField()

    class Meta:
        model = Resena
        fields = (
            "id",
            "usuario",
            "usuario_id",
            "media_id",
            "media_titulo",
            "media_poster_url",
            "media_tipo",
            "puntuacion",
            "texto",
            "fecha_creacion",
            "fecha_actualizacion",
            "usuario_avatar",
            "total_likes",
            "me_gusta",
            "total_comentarios",
            "estado_autor",
            "autor_le_gusta",
        )
        read_only_fields = ("id", "fecha_creacion", "fecha_actualizacion")

    # Los listados anotan estos valores (ver social.resenas.anotar_resenas);
    # si no vienen anotados, se calculan aquí.
    def get_total_likes(self, obj):
        valor = getattr(obj, "total_likes_anotado", None)
        return valor if valor is not None else obj.likes.count()

    def get_total_comentarios(self, obj):
        valor = getattr(obj, "total_comentarios_anotado", None)
        return valor if valor is not None else obj.comentarios.count()

    def get_me_gusta(self, obj):
        valor = getattr(obj, "me_gusta_anotado", None)
        if valor is not None:
            return valor
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(usuario=request.user).exists()

    def _registro_autor(self, obj):
        if not hasattr(obj, "_registro_autor"):
            obj._registro_autor = RegistroTitulo.objects.filter(
                usuario_id=obj.usuario_id, media_id=obj.media_id
            ).values("estado", "me_gusta").first() or {}
        return obj._registro_autor

    def get_estado_autor(self, obj):
        if hasattr(obj, "estado_autor_anotado"):
            return obj.estado_autor_anotado or ""
        return self._registro_autor(obj).get("estado", "")

    def get_autor_le_gusta(self, obj):
        if hasattr(obj, "autor_le_gusta_anotado"):
            return bool(obj.autor_le_gusta_anotado)
        return bool(self._registro_autor(obj).get("me_gusta"))

    def validate_texto(self, value):
        normalized = " ".join(value.split())
        if len(normalized) > MAX_RESENA_TEXTO_LENGTH:
            raise serializers.ValidationError(
                f"El texto de la reseña no puede superar "
                f"{MAX_RESENA_TEXTO_LENGTH} caracteres."
            )
        return normalized

    def validate(self, attrs):
        media = (
            self.instance.media
            if self.instance is not None
            else self.context.get("media")
        )
        if media and media.estado == Media.Estado.PROXIMO_ESTRENO:
            raise serializers.ValidationError(
                {
                    "detail": (
                        "No se pueden crear ni editar reseñas de títulos "
                        "próximos a estrenarse."
                    )
                }
            )
        return attrs


class ReporteResenaSerializer(serializers.ModelSerializer):
    motivo = serializers.CharField(max_length=1000)

    class Meta:
        model = ReporteResena
        fields = ("id", "resena", "usuario", "motivo", "fecha")
        read_only_fields = ("id", "resena", "usuario", "fecha")


class ElementoListaSerializer(serializers.ModelSerializer):
    media_id = serializers.IntegerField(source="media.id", read_only=True)
    media_titulo = serializers.CharField(source="media.titulo", read_only=True)
    media_poster_url = serializers.CharField(source="media.poster_url", read_only=True)
    media_tipo = serializers.CharField(source="media.tipo", read_only=True)
    media_estado = serializers.CharField(source="media.estado", read_only=True)

    class Meta:
        model = ElementoLista
        fields = (
            "id",
            "media_id",
            "media_titulo",
            "media_poster_url",
            "media_tipo",
            "media_estado",
            "orden",
            "fecha_agregado",
        )
        read_only_fields = ("id", "fecha_agregado")


class ListaSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.username", read_only=True)
    usuario_id = serializers.IntegerField(read_only=True)
    total_elementos = serializers.IntegerField(read_only=True)

    class Meta:
        model = Lista
        fields = (
            "id",
            "usuario",
            "usuario_id",
            "nombre",
            "descripcion",
            "tipo",
            "publica",
            "total_elementos",
            "fecha_creacion",
            "fecha_actualizacion",
        )
        read_only_fields = (
            "id",
            "usuario",
            "usuario_id",
            "total_elementos",
            "fecha_creacion",
            "fecha_actualizacion",
        )

    def validate(self, attrs):
        tipo = attrs.get("tipo", getattr(self.instance, "tipo", None))
        if self.instance is not None and tipo != self.instance.tipo:
            raise serializers.ValidationError(
                {"tipo": "No se puede cambiar el tipo de una lista ya creada."}
            )
        request = self.context.get("request")
        if request and request.user.is_authenticated and tipo in [Lista.Tipo.FAVORITAS, Lista.Tipo.POR_VER]:
            qs = Lista.objects.filter(usuario=request.user, tipo=tipo)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"tipo": f"Ya tienes una lista de tipo '{tipo}'."}
                )
        return attrs


class ListaDetalleSerializer(ListaSerializer):
    elementos = ElementoListaSerializer(
        source="elementos_lista", many=True, read_only=True
    )

    class Meta(ListaSerializer.Meta):
        fields = ListaSerializer.Meta.fields + ("elementos",)


class AgregarElementoSerializer(serializers.Serializer):
    media_id = serializers.IntegerField(required=True)
    orden = serializers.IntegerField(required=False, default=0)


class SugerenciaEdicionSerializer(serializers.ModelSerializer):
    valor_propuesto = serializers.CharField(max_length=5000)
    motivo = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    usuario = serializers.CharField(source="usuario.username", read_only=True)
    usuario_id = serializers.IntegerField(read_only=True)
    media_id = serializers.IntegerField(read_only=True)
    media_titulo = serializers.CharField(source="media.titulo", read_only=True)
    revisado_por = serializers.CharField(
        source="revisado_por.username", read_only=True, default=None
    )

    class Meta:
        model = SugerenciaEdicion
        fields = (
            "id",
            "usuario",
            "usuario_id",
            "media_id",
            "media_titulo",
            "campo",
            "valor_propuesto",
            "valor_anterior",
            "motivo",
            "estado",
            "motivo_rechazo",
            "revisado_por",
            "fecha_creacion",
            "fecha_resolucion",
        )
        read_only_fields = (
            "id",
            "usuario",
            "usuario_id",
            "media_id",
            "media_titulo",
            "estado",
            "valor_anterior",
            "motivo_rechazo",
            "revisado_por",
            "fecha_creacion",
            "fecha_resolucion",
        )

    def validate_campo(self, value):
        if value not in CAMPOS_SUGERENCIA_EDITABLES:
            raise serializers.ValidationError(
                "Campo no editable. Solo se permiten: "
                + ", ".join(CAMPOS_SUGERENCIA_EDITABLES)
                + "."
            )
        return value

    def validate_valor_propuesto(self, value):
        normalized = str(value).strip()
        return normalized

    def validate(self, attrs):
        if self.instance is not None:
            return attrs

        campo = attrs.get("campo")
        valor = attrs.get("valor_propuesto")
        media = self.context.get("media")
        request = self.context.get("request")

        if not campo or valor is None or media is None:
            return attrs

        media_serializer = MediaWriteSerializer(
            media,
            data={campo: valor},
            partial=True,
        )
        if not media_serializer.is_valid():
            raise serializers.ValidationError(
                {"valor_propuesto": media_serializer.errors.get(campo, ["Valor no válido."])}
            )

        valor_validado = media_serializer.validated_data[campo]
        valor_actual = getattr(media, campo)

        if valor_validado == valor_actual:
            raise serializers.ValidationError(
                {"valor_propuesto": ["El valor propuesto debe ser diferente al valor actual."]}
            )

        if hasattr(valor_validado, "isoformat"):
            valor_validado = valor_validado.isoformat()
        attrs["valor_propuesto"] = str(valor_validado)

        if request and request.user.is_authenticated:
            existe_pendiente = SugerenciaEdicion.objects.filter(
                usuario=request.user,
                media=media,
                campo=campo,
                estado=SugerenciaEdicion.Estado.PENDIENTE,
            ).exists()
            if existe_pendiente:
                raise serializers.ValidationError(
                    {"detail": "Ya existe una sugerencia pendiente para este título y campo."}
                )

        return attrs


class ResolverSugerenciaSerializer(serializers.Serializer):
    motivo_rechazo = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=1000,
    )



MAX_COMENTARIO_LENGTH = 1000


class ComentarioResenaSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.username", read_only=True)
    usuario_avatar = serializers.CharField(source="usuario.avatar", read_only=True)
    texto = serializers.CharField(max_length=MAX_COMENTARIO_LENGTH)

    class Meta:
        model = ComentarioResena
        fields = ("id", "resena", "usuario", "usuario_avatar", "texto", "fecha_creacion")
        read_only_fields = ("id", "resena", "fecha_creacion")

    def validate_texto(self, value):
        texto = value.strip()
        if not texto:
            raise serializers.ValidationError("El comentario no puede estar vacío.")
        return texto
