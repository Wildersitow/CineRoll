from django.db import models
from django.utils import timezone

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
    formato = models.CharField(max_length=150, blank=True)
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

class EjecucionScraping(models.Model):
    """Registro de cada ejecución del scraper de un cine (para auditar y depurar)."""

    class Estado(models.TextChoices):
        EN_CURSO = "en_curso", "En curso"
        EXITOSA = "exitosa", "Exitosa"
        FALLIDA = "fallida", "Fallida"
        OMITIDA = "omitida", "Omitida (ya había una en curso)"

    cine = models.CharField(max_length=50)
    ciudad = models.CharField(max_length=100)
    intento = models.PositiveSmallIntegerField(default=1)
    inicio = models.DateTimeField(default=timezone.now)
    fin = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.EN_CURSO
    )

    # Conteos del CarteleraScrapeResult
    funciones_leidas = models.PositiveIntegerField(default=0)
    funciones_asociadas = models.PositiveIntegerField(default=0)
    funciones_creadas = models.PositiveIntegerField(default=0)
    funciones_actualizadas = models.PositiveIntegerField(default=0)
    titulos_pendientes = models.PositiveIntegerField(default=0)
    peliculas_en_cartelera = models.PositiveIntegerField(default=0)
    estrenos_leidos = models.PositiveIntegerField(default=0)
    estrenos_asociados = models.PositiveIntegerField(default=0)
    funciones_vencidas_eliminadas = models.PositiveIntegerField(default=0)
    funciones_obsoletas_eliminadas = models.PositiveIntegerField(default=0)
    peliculas_fuera_cartelera = models.PositiveIntegerField(default=0)

    advertencia = models.TextField(
        blank=True,
        help_text="Por ejemplo, cuando la salvaguarda impidió borrar funciones.",
    )
    mensaje_error = models.TextField(blank=True)

    class Meta:
        ordering = ["-inicio"]
        verbose_name = "ejecución de scraping"
        verbose_name_plural = "ejecuciones de scraping"
        indexes = [
            models.Index(
                fields=["cine", "ciudad", "-inicio"], name="cines_ejec_cine_ciudad_idx"
            ),
        ]

    def __str__(self):
        return f"{self.cine} ({self.ciudad}) — {self.get_estado_display()} — {self.inicio:%Y-%m-%d %H:%M}"

    @property
    def duracion(self):
        return self.fin - self.inicio if self.fin else None