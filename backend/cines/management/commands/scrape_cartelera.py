from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from cines.models import Cine, Funcion, TituloPendiente
from cines.scrapers.cinemark import CinemarkScraperError, scrape_cartelera
from cines.services import NormalizedShowtime, match_media_title, normalize_title
from media.models import Media


class Command(BaseCommand):
    help = "Obtiene la cartelera de un cine, relaciona películas y guarda funciones."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cine",
            required=True,
            choices=("cinemark",),
            help="Cine cuyo scraper se ejecutará.",
        )
        parser.add_argument(
            "--ciudad",
            default="bogota",
            help="Slug de la ciudad en el sitio del cine (por defecto: bogota).",
        )

    def handle(self, *_args, **options):
        cinema_provider = options["cine"]
        city_slug = options["ciudad"].strip().lower()
        try:
            records = self._scrape(cinema_provider, city_slug)
        except (CinemarkScraperError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        movies = list(Media.objects.filter(tipo=Media.Tipo.PELICULA))
        matched = 0
        pending = 0
        created_functions = 0
        updated_functions = 0
        cinema_cache = self._build_cinema_cache()

        with transaction.atomic():
            for record in records:
                media = match_media_title(record["titulo"], movies)
                if media is None:
                    self._record_pending(record)
                    pending += 1
                    continue

                TituloPendiente.objects.filter(
                    titulo_normalizado=normalize_title(record["titulo"]),
                    cine_nombre=record["cine"],
                    ciudad=record["ciudad"],
                    estado=TituloPendiente.Estado.PENDIENTE,
                ).update(
                    estado=TituloPendiente.Estado.RESUELTO,
                    media_asociada=media,
                    ultima_deteccion=timezone.now(),
                )
                cinema = self._get_or_create_cinema(record, cinema_cache)
                scheduled_at = datetime.combine(record["fecha"], record["hora"])
                _, created = Funcion.objects.update_or_create(
                    cine=cinema,
                    media=media,
                    fecha_hora=scheduled_at,
                    sala=record["sala"],
                    formato=record["formato"],
                    defaults={"fuente_scraping": record["fuente_scraping"]},
                )
                matched += 1
                if created:
                    created_functions += 1
                else:
                    updated_functions += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Cartelera {cinema_provider} ({city_slug}): "
                f"{len(records)} funciones leídas, {matched} asociadas al catálogo, "
                f"{created_functions} guardadas, {updated_functions} actualizadas, "
                f"{pending} pendientes de revisión."
            )
        )
        if pending:
            self.stdout.write("Títulos pendientes:")
            for item in (
                TituloPendiente.objects.filter(
                    ciudad=city_slug,
                    cine_nombre__in={record["cine"] for record in records},
                    estado=TituloPendiente.Estado.PENDIENTE,
                )
                .order_by("titulo_normalizado", "cine_nombre")
                .distinct()[:20]
            ):
                self.stdout.write(
                    f"  #{item.pk} {item.titulo_original} — "
                    f"{item.cine_nombre} ({item.ciudad})"
                )
            if pending > 20:
                self.stdout.write("  (se muestran como máximo 20 títulos)")

    def _scrape(self, cinema_provider: str, city_slug: str) -> list[NormalizedShowtime]:
        if cinema_provider == "cinemark":
            return scrape_cartelera(city_slug=city_slug)
        raise CommandError(f"No existe scraper configurado para '{cinema_provider}'.")

    def _build_cinema_cache(self) -> dict[tuple[str, str], Cine]:
        return {
            (normalize_title(cinema.nombre), normalize_title(cinema.ciudad)): cinema
            for cinema in Cine.objects.all()
        }

    def _get_or_create_cinema(
        self,
        record: NormalizedShowtime,
        cache: dict[tuple[str, str], Cine],
    ) -> Cine:
        key = (normalize_title(record["cine"]), normalize_title(record["ciudad"]))
        cinema = cache.get(key)
        if cinema is None:
            cinema = Cine.objects.create(
                nombre=record["cine"],
                ciudad=record["ciudad"],
                direccion="",
                sitio_web="https://www.cinemark.com.co/",
            )
            cache[key] = cinema
        return cinema

    def _record_pending(self, record: NormalizedShowtime) -> None:
        normalized = normalize_title(record["titulo"])
        if not normalized:
            raise CommandError(
                f"El scraper devolvió un título sin contenido: {record['titulo']!r}."
            )
        pending, created = TituloPendiente.objects.get_or_create(
            titulo_normalizado=normalized,
            cine_nombre=record["cine"],
            ciudad=record["ciudad"],
            defaults={
                "titulo_original": record["titulo"],
                "fuente_scraping": record["fuente_scraping"],
            },
        )
        if created:
            return

        TituloPendiente.objects.filter(pk=pending.pk).update(
            titulo_original=record["titulo"],
            fuente_scraping=record["fuente_scraping"],
            ultima_deteccion=timezone.now(),
            apariciones_detectadas=F("apariciones_detectadas") + 1,
        )
