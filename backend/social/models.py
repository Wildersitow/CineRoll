from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Escala de puntuación acordada: números enteros de 1 a 10.
PUNTUACION_MINIMA = 1
PUNTUACION_MAXIMA = 10


class ResenaQuerySet(models.QuerySet):
    def visibles(self):
        """Reseñas que no fueron ocultadas por moderación."""
        return self.filter(oculta=False)


class Resena(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resenas"
    )
    media = models.ForeignKey(
        "media.Media", on_delete=models.CASCADE, related_name="resenas"
    )
    puntuacion = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(PUNTUACION_MINIMA),
            MaxValueValidator(PUNTUACION_MAXIMA),
        ]
    )
    texto = models.TextField(blank=True)
    oculta = models.BooleanField(
        default=False,
        help_text="Una reseña oculta no se muestra ni cuenta en el promedio.",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    objects = ResenaQuerySet.as_manager()

    class Meta:
        ordering = ["-fecha_creacion", "-id"]
        verbose_name = "reseña"
        verbose_name_plural = "reseñas"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "media"], name="social_resena_unica"
            ),
            models.CheckConstraint(
                condition=models.Q(puntuacion__gte=PUNTUACION_MINIMA)
                & models.Q(puntuacion__lte=PUNTUACION_MAXIMA),
                name="social_resena_puntuacion_ok",
            ),
        ]
        indexes = [
            models.Index(fields=["media", "oculta"], name="social_resena_media_idx"),
        ]

    def __str__(self):
        return f"{self.usuario} → {self.media}: {self.puntuacion}/{PUNTUACION_MAXIMA}"


class ReporteResena(models.Model):
    resena = models.ForeignKey(
        Resena, on_delete=models.CASCADE, related_name="reportes"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reportes_resenas",
    )
    motivo = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "reporte de reseña"
        verbose_name_plural = "reportes de reseñas"
        constraints = [
            models.UniqueConstraint(
                fields=["resena", "usuario"], name="social_reporte_resena_unico"
            ),
        ]

    def __str__(self):
        return f"Reporte de {self.usuario} sobre reseña {self.resena_id}"


class Lista(models.Model):
    """Listas de títulos de usuarios: favoritas, por ver y personalizadas."""

    class Tipo(models.TextChoices):
        FAVORITAS = "favoritas", "Favoritas"
        POR_VER = "por_ver", "Por ver"
        PERSONALIZADA = "personalizada", "Personalizada"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listas"
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(
        max_length=20, choices=Tipo.choices, default=Tipo.PERSONALIZADA
    )
    publica = models.BooleanField(
        default=True,
        help_text="Las listas públicas pueden ser consultadas por otros usuarios.",
    )
    elementos = models.ManyToManyField(
        "media.Media", through="ElementoLista", related_name="listas", blank=True
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion", "-id"]
        verbose_name = "lista"
        verbose_name_plural = "listas"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "tipo"],
                condition=models.Q(tipo__in=["favoritas", "por_ver"]),
                name="social_lista_sistema_unica_por_usuario",
            ),
        ]
        indexes = [
            models.Index(fields=["usuario", "publica"], name="social_lista_usr_pub_idx"),
            models.Index(fields=["tipo"], name="social_lista_tipo_idx"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.usuario})"

    @property
    def total_elementos(self):
        anotado = getattr(self, "total_elementos_anotado", None)
        if anotado is not None:
            return anotado
        return self.elementos_lista.count()


class ElementoLista(models.Model):
    """Asociación de un título de Media dentro de una Lista."""

    lista = models.ForeignKey(
        Lista, on_delete=models.CASCADE, related_name="elementos_lista"
    )
    media = models.ForeignKey(
        "media.Media", on_delete=models.CASCADE, related_name="en_listas"
    )
    orden = models.PositiveIntegerField(default=0)
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["orden", "-fecha_agregado", "-id"]
        verbose_name = "elemento de lista"
        verbose_name_plural = "elementos de lista"
        constraints = [
            models.UniqueConstraint(
                fields=["lista", "media"], name="social_elementolista_unico"
            ),
        ]

    def __str__(self):
        return f"{self.media} en {self.lista}"


class Seguimiento(models.Model):
    """Relación social donde un usuario sigue la actividad de otro usuario."""

    seguidor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="siguiendo"
    )
    seguido = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seguidores"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion", "-id"]
        verbose_name = "seguimiento"
        verbose_name_plural = "seguimientos"
        constraints = [
            models.UniqueConstraint(
                fields=["seguidor", "seguido"], name="social_seguimiento_unico"
            ),
            models.CheckConstraint(
                condition=~models.Q(seguidor=models.F("seguido")),
                name="social_seguimiento_no_auto",
            ),
        ]

    def __str__(self):
        return f"{self.seguidor} sigue a {self.seguido}"


class SugerenciaEdicion(models.Model):
    """Sugerencia de un usuario para corregir o enriquecer una ficha del catálogo."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sugerencias_edicion",
    )
    media = models.ForeignKey(
        "media.Media",
        on_delete=models.CASCADE,
        related_name="sugerencias_edicion",
    )
    campo = models.CharField(
        max_length=50,
        help_text="Nombre del campo a editar (ej. titulo, sinopsis, fecha_estreno).",
    )
    valor_propuesto = models.TextField(
        help_text="Nuevo valor sugerido para el campo indicado."
    )
    valor_anterior = models.TextField(
        blank=True,
        default="",
        help_text="Valor que tenía el campo antes de aprobar la sugerencia.",
    )
    motivo = models.TextField(
        blank=True,
        help_text="Explicación o fuente que justifica la corrección.",
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    motivo_rechazo = models.TextField(
        blank=True,
        help_text="Justificación dada por el moderador en caso de rechazo.",
    )
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sugerencias_revisadas",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_creacion", "-id"]
        verbose_name = "sugerencia de edición"
        verbose_name_plural = "sugerencias de edición"
        indexes = [
            models.Index(fields=["estado"], name="social_sugerencia_estado_idx"),
            models.Index(
                fields=["media", "estado"], name="social_sugerencia_med_est_idx"
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "media", "campo"],
                condition=models.Q(estado="pendiente"),
                name="social_sugerencia_pendiente_unica",
            ),
        ]

    def __str__(self):
        return f"Sugerencia de {self.usuario} sobre {self.media} ({self.campo})"



class RegistroTitulo(models.Model):
    """
    Cómo lleva un usuario un título: si ya lo vio o lo está viendo, y si le gustó.
    "Pendiente" no se guarda aquí: es estar en la lista Por ver del usuario.
    """

    class Estado(models.TextChoices):
        VISTO = "visto", "Visto"
        VIENDO = "viendo", "Viendo"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="registros"
    )
    media = models.ForeignKey(
        "media.Media", on_delete=models.CASCADE, related_name="registros"
    )
    estado = models.CharField(max_length=10, choices=Estado.choices, blank=True)
    me_gusta = models.BooleanField(default=False)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_actualizacion", "-id"]
        verbose_name = "registro de título"
        verbose_name_plural = "registros de títulos"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "media"], name="social_registro_unico"
            ),
        ]

    def __str__(self):
        return f"{self.usuario} · {self.media}: {self.estado or 'sin estado'}"


class LikeResena(models.Model):
    """Un "me gusta" de un usuario a una reseña."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes_resenas"
    )
    resena = models.ForeignKey(Resena, on_delete=models.CASCADE, related_name="likes")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "me gusta de reseña"
        verbose_name_plural = "me gusta de reseñas"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "resena"], name="social_like_resena_unico"
            ),
        ]

    def __str__(self):
        return f"{self.usuario} ♥ reseña {self.resena_id}"


class ComentarioResena(models.Model):
    """Comentario de un usuario debajo de una reseña."""

    resena = models.ForeignKey(
        Resena, on_delete=models.CASCADE, related_name="comentarios"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comentarios_resenas",
    )
    texto = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha_creacion", "id"]
        verbose_name = "comentario de reseña"
        verbose_name_plural = "comentarios de reseñas"
        indexes = [
            models.Index(fields=["resena", "fecha_creacion"], name="social_coment_resena_idx"),
        ]

    def __str__(self):
        return f"{self.usuario} en reseña {self.resena_id}"


LONGITUD_MAXIMA_MENSAJE = 2000


class Mensaje(models.Model):
    """Mensaje de chat: privado entre dos usuarios o en la sala pública de un título.

    Cada mensaje va a un destinatario o a un título (media), nunca a los dos.
    `envio` lo genera el navegador para cada envío: si la petición se repite
    (doble clic, red lenta) no se duplica el mensaje.
    """

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mensajes_enviados"
    )
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mensajes_recibidos",
        null=True,
        blank=True,
    )
    media = models.ForeignKey(
        "media.Media",
        on_delete=models.CASCADE,
        related_name="mensajes",
        null=True,
        blank=True,
    )
    texto = models.TextField(max_length=LONGITUD_MAXIMA_MENSAJE)
    envio = models.UUIDField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "mensaje"
        verbose_name_plural = "mensajes"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(destinatario__isnull=False, media__isnull=True)
                    | models.Q(destinatario__isnull=True, media__isnull=False)
                ),
                name="social_mensaje_un_destino",
            ),
            models.UniqueConstraint(
                fields=["autor", "envio"], name="social_mensaje_envio_unico"
            ),
        ]
        indexes = [
            models.Index(fields=["autor", "destinatario", "id"], name="social_msj_privado_idx"),
            models.Index(fields=["media", "id"], name="social_msj_sala_idx"),
        ]

    def __str__(self):
        destino = f"@{self.destinatario}" if self.destinatario_id else f"sala {self.media_id}"
        return f"{self.autor} → {destino}: {self.texto[:40]}"
