from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cines import tmdb
from cines.services import apply_genres_and_credits, normalize_title
from media.models import Media


class Command(BaseCommand):
    help = (
        "Completa con TMDB las películas que el scraper creó sin esos datos "
        "(póster, sinopsis, duración, tráiler, géneros y reparto). Solo llena "
        "los campos vacíos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--todas",
            action="store_true",
            help="Incluye también las películas del catálogo que no creó el scraper.",
        )

    def handle(self, *_args, **options):
        if not tmdb.configurado():
            raise CommandError("Configura TMDB_API_KEY en las variables del backend.")

        peliculas = Media.objects.filter(tipo=Media.Tipo.PELICULA, tmdb_id__isnull=True)
        if not options["todas"]:
            peliculas = peliculas.filter(creado_automaticamente=True)

        completadas = 0
        sin_resultado = []
        for media in peliculas.order_by("pk"):
            titulos = [titulo for titulo in (media.titulo, media.titulo_original) if titulo]
            encontrada = tmdb.buscar_pelicula(titulos, normalize_title)
            if encontrada is None:
                sin_resultado.append(media.titulo)
                continue
            otra = Media.objects.filter(tmdb_id=encontrada.tmdb_id).first()
            if otra is not None:
                self.stdout.write(
                    f"  #{media.pk} {media.titulo}: TMDB la identifica igual que "
                    f"#{otra.pk} {otra.titulo}; revisa si está duplicada."
                )
                continue
            with transaction.atomic():
                _completar(media, encontrada)
            completadas += 1
            self.stdout.write(f"  #{media.pk} {media.titulo}: completada.")

        self.stdout.write(
            self.style.SUCCESS(
                f"{completadas} películas completadas con TMDB, "
                f"{len(sin_resultado)} sin resultado."
            )
        )
        for titulo in sin_resultado:
            self.stdout.write(f"  Sin resultado: {titulo}")


def _completar(media: Media, encontrada: "tmdb.TmdbPelicula") -> None:
    media.tmdb_id = encontrada.tmdb_id
    campos = {
        "sinopsis": encontrada.sinopsis,
        "duracion": encontrada.duracion,
        "poster_url": encontrada.poster_url,
        "backdrop_url": encontrada.backdrop_url,
        "trailer_url": encontrada.trailer_url,
        "fecha_estreno": encontrada.fecha_estreno,
    }
    if (
        encontrada.titulo_original
        and normalize_title(encontrada.titulo_original) != normalize_title(media.titulo)
    ):
        campos["titulo_original"] = encontrada.titulo_original
    for campo, valor in campos.items():
        if valor and not getattr(media, campo):
            setattr(media, campo, valor)
    media.save()
    apply_genres_and_credits(
        media,
        encontrada.generos if not media.generos.exists() else (),
        encontrada.directores if not media.creditos.exists() else (),
        encontrada.actores if not media.creditos.exists() else (),
    )
