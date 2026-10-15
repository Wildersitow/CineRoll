from django.db import models


class Cine(models.Model):
    nombre = models.CharField(max_length=150)
    ciudad = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)
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
