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
