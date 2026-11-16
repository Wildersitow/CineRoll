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

    def __str__(self):
        return f"Sugerencia de {self.usuario} sobre {self.media} ({self.campo})"

