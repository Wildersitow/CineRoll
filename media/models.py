from django.db import models


class Genero(models.Model):
	nombre = models.CharField(max_length=100, unique=True)

	class Meta:
		ordering = ["nombre"]
		verbose_name = "género"
		verbose_name_plural = "géneros"

	def __str__(self):
		return self.nombre


class Media(models.Model):
	class Tipo(models.TextChoices):
		PELICULA = "pelicula", "Película"
		SERIE = "serie", "Serie"
		ANIME = "anime", "Anime"

	class Estado(models.TextChoices):
		EN_CARTELERA = "en_cartelera", "En cartelera"
		PROXIMO_ESTRENO = "proximo_estreno", "Próximo estreno"
		FUERA_CARTELERA = "fuera_cartelera", "Fuera de cartelera"

	titulo = models.CharField(max_length=200)
	titulo_original = models.CharField(max_length=200, blank=True)
	tipo = models.CharField(max_length=10, choices=Tipo.choices)
	sinopsis = models.TextField(blank=True)
	fecha_estreno = models.DateField(blank=True, null=True)
	duracion = models.PositiveSmallIntegerField(blank=True, null=True)
	poster_url = models.URLField(blank=True)
	trailer_url = models.URLField(blank=True)
	estado = models.CharField(
		max_length=20,
		choices=Estado.choices,
		default=Estado.PROXIMO_ESTRENO,
	)
	generos = models.ManyToManyField(Genero, related_name="medias", blank=True)
	personas = models.ManyToManyField(
		"Persona", through="Credito", related_name="medias", blank=True
	)

	class Meta:
		ordering = ["titulo"]
		verbose_name = "medio"
		verbose_name_plural = "medios"

	def __str__(self):
		return f"{self.titulo} ({self.get_tipo_display()})"


class Persona(models.Model):
	nombre = models.CharField(max_length=200)
	biografia = models.TextField(blank=True)
	fecha_nacimiento = models.DateField(blank=True, null=True)

	class Meta:
		ordering = ["nombre"]

	def __str__(self):
		return self.nombre


class Credito(models.Model):
	class Rol(models.TextChoices):
		ACTOR = "actor", "Actor"
		DIRECTOR = "director", "Director"

	media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name="creditos")
	persona = models.ForeignKey(
		Persona, on_delete=models.CASCADE, related_name="creditos"
	)
	rol = models.CharField(max_length=10, choices=Rol.choices)

	class Meta:
		ordering = ["media", "persona", "rol"]
		constraints = [
			models.UniqueConstraint(
				fields=["media", "persona", "rol"],
				name="unique_media_persona_rol",
			)
		]

	def __str__(self):
		return f"{self.persona} - {self.get_rol_display()} - {self.media}"
