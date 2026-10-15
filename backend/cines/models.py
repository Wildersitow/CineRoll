from django.db import models


class Cine(models.Model):
    nombre = models.CharField(max_length=150)
    ciudad = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255, blank=True)
    sitio_web = models.URLField(blank=True)

    class Meta:
        ordering = ["ciudad", "nombre"]
        verbose_name = "cine"
        verbose_name_plural = "cines"

    def __str__(self):
        return f"{self.nombre} ({self.ciudad})"


class Funcion(models.Model):
    cine = models.ForeignKey(Cine, on_delete=models.CASCADE, related_name="funciones")
    media = models.ForeignKey(
        "media.Media", on_delete=models.CASCADE, related_name="funciones"
    )
    fecha_hora = models.DateTimeField()
    sala = models.CharField(max_length=100, blank=True)
    formato = models.CharField(max_length=50, blank=True)
    fuente_scraping = models.URLField(blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["fecha_hora", "cine__nombre"]
        verbose_name = "función"
        verbose_name_plural = "funciones"
        indexes = [
            models.Index(fields=["cine", "fecha_hora"], name="cines_func_cine_fecha_idx"),
            models.Index(fields=["media", "fecha_hora"], name="cines_func_media_fecha_idx"),
        ]

    def __str__(self):
        return f"{self.media} — {self.cine} — {self.fecha_hora:%Y-%m-%d %H:%M}"


class TituloPendiente(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de revisión"
        RESUELTO = "resuelto", "Resuelto"
        IGNORADO = "ignorado", "Ignorado"

    titulo_original = models.CharField(max_length=200)
    titulo_normalizado = models.CharField(max_length=200)
    cine_nombre = models.CharField(max_length=150)
    ciudad = models.CharField(max_length=100)
    fuente_scraping = models.URLField(blank=True)
    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    media_asociada = models.ForeignKey(
        "media.Media",
        on_delete=models.SET_NULL,
        related_name="titulos_pendientes",
        blank=True,
        null=True,
    )
    primera_deteccion = models.DateTimeField(auto_now_add=True)
    ultima_deteccion = models.DateTimeField(auto_now=True)
    apariciones_detectadas = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["estado", "titulo_normalizado", "cine_nombre"]
        verbose_name = "título pendiente de cartelera"
        verbose_name_plural = "títulos pendientes de cartelera"
        constraints = [
            models.UniqueConstraint(
                fields=["titulo_normalizado", "cine_nombre", "ciudad"],
                name="cines_pending_title_unique",
            )
        ]

    def __str__(self):
        return f"{self.titulo_original} — {self.cine_nombre} ({self.ciudad})"
