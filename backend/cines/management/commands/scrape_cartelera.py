from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from cines.models import Cine, Funcion, TituloPendiente
from cines.scrapers.cinemark import (
    CinemarkCartelera,
    CinemarkScraperError,
    scrape_cartelera_completa,
)
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
            cartelera = self._scrape(cinema_provider, city_slug)
        except (CinemarkScraperError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        records = cartelera.funciones
        movies = list(Media.objects.filter(tipo=Media.Tipo.PELICULA))
        manual_matches = self._build_manual_matches()
        matched = 0
        pending = 0
        created_functions = 0
        updated_functions = 0
        cinema_cache = self._build_cinema_cache()
        matched_media_ids: set[int] = set()
        matched_releases = 0
        unmatched_releases: list[str] = []

        with transaction.atomic():
            for release in cartelera.proximos_estrenos:
                media = match_media_title(release["titulo"], movies)
                if media is None:
                    unmatched_releases.append(release["titulo"])
                    continue
                media.fecha_estreno = release["fecha_estreno"]
                media.estado = Media.Estado.PROXIMO_ESTRENO
                media.save(update_fields=["fecha_estreno", "estado"])
                matched_releases += 1

            for record in records:
                media = match_media_title(record["titulo"], movies)
                if media is None:
                    media = manual_matches.get(normalize_title(record["titulo"]))
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
                matched_media_ids.add(media.pk)
                if created:
                    created_functions += 1
                else:
                    updated_functions += 1

            now_showing = self._mark_now_showing(matched_media_ids)

        self.stdout.write(
            self.style.SUCCESS(
                f"Cartelera {cinema_provider} ({city_slug}): "
                f"{len(records)} funciones leídas, {matched} asociadas al catálogo, "
                f"{created_functions} guardadas, {updated_functions} actualizadas, "
                f"{pending} pendientes de revisión, "
                f"{now_showing} películas pasadas a 'en cartelera', "
                f"{len(cartelera.proximos_estrenos)} próximos estrenos leídos, "
                f"{matched_releases} asociados a Media."
            )
        )
        if unmatched_releases:
            self.stdout.write("Próximos estrenos sin coincidencia en Media:")
            for title in unmatched_releases:
                self.stdout.write(f"  {title}")
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

    def _scrape(self, cinema_provider: str, city_slug: str) -> CinemarkCartelera:
        if cinema_provider == "cinemark":
            return scrape_cartelera_completa(city_slug=city_slug)
        raise CommandError(f"No existe scraper configurado para '{cinema_provider}'.")

    def _build_manual_matches(self) -> dict[str, Media]:
        """Títulos que un administrador resolvió a mano en el admin de pendientes."""
        return {
            pending.titulo_normalizado: pending.media_asociada
            for pending in TituloPendiente.objects.filter(
                estado=TituloPendiente.Estado.RESUELTO,
                media_asociada__isnull=False,
            ).select_related("media_asociada")
        }

    def _mark_now_showing(self, media_ids: set[int]) -> int:
        """Marca 'en cartelera' las películas con funciones, salvo estrenos futuros."""
        today = timezone.localdate()
        return (
            Media.objects.filter(pk__in=media_ids)
            .exclude(estado=Media.Estado.EN_CARTELERA)
            .exclude(fecha_estreno__gt=today)
            .update(estado=Media.Estado.EN_CARTELERA)
        )

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
