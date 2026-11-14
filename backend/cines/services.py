from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time
import unicodedata
import re
from typing import Callable, TypedDict
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Exists, F, OuterRef
from django.utils import timezone

from cines.models import Cine, Funcion, TituloPendiente
from media.models import Media


COLOMBIA_TIMEZONE = ZoneInfo("America/Bogota")
TITLE_QUALIFIERS = {
    "2d",
    "3d",
    "4dx",
    "atmos",
    "dob",
    "doblada",
    "doblado",
    "dublado",
    "dublada",
    "espanol",
    "castellano",
    "hd",
    "imax",
    "lat",
    "latino",
    "sub",
    "subtitulada",
    "subtitulado",
    "vose",
    "xd",
}

class ScraperError(RuntimeError):
    pass


class NormalizedShowtime(TypedDict):
    titulo: str
    cine: str
    ciudad: str
    fecha: date
    hora: time
    sala: str
    formato: str
    fuente_scraping: str
    cine_id_origen: str
    funcion_id_origen: str


class UpcomingRelease(TypedDict):
    titulo: str
    fecha_estreno: date
    fuente_scraping: str


@dataclass(frozen=True)
class CarteleraData:
    funciones: list[NormalizedShowtime]
    proximos_estrenos: list[UpcomingRelease]


@dataclass(frozen=True)
class ScraperConfig:
    scrape: Callable[[str], CarteleraData]
    website: str


CANONICAL_CITY = "valledupar"
CITY_PROVIDER_KEYS = {
    CANONICAL_CITY: {
        "cinepolis": "valledupar-colombia",
        "royal_films": "1006",
        "cineland": "0051",
    },
    "bogota": {
        "cinemark": "bogota",
    },
}


def _scrape_cinemark(city_slug: str) -> CarteleraData:
    from cines.scrapers.cinemark import scrape_cartelera_completa

    return scrape_cartelera_completa(city_slug=city_slug)


def _scrape_cinepolis(city_key: str) -> CarteleraData:
    from cines.scrapers.cinepolis import scrape_cartelera_completa

    return scrape_cartelera_completa(city_key=city_key)


def _scrape_royal_films(city_id: str) -> CarteleraData:
    from cines.scrapers.royal_films import scrape_cartelera_completa

    return scrape_cartelera_completa(city_id=city_id)


SCRAPERS = {
    "cinemark": ScraperConfig(
        scrape=_scrape_cinemark,
        website="https://www.cinemark.com.co/",
    ),
    "cinepolis": ScraperConfig(
        scrape=_scrape_cinepolis,
        website="https://cinepolis.com.co/",
    ),
    "royal_films": ScraperConfig(
        scrape=_scrape_royal_films,
        website="https://cinemasroyalfilms.com/",
    ),
}


@dataclass(frozen=True)
class CarteleraScrapeResult:
    cine: str
    ciudad: str
    funciones_leidas: int
    funciones_asociadas: int
    funciones_creadas: int
    funciones_actualizadas: int
    titulos_pendientes: int
    peliculas_en_cartelera: int
    estrenos_leidos: int
    estrenos_asociados: int
    funciones_vencidas_eliminadas: int
    peliculas_fuera_cartelera: int
    estrenos_sin_coincidencia: tuple[str, ...]
    titulos_pendientes_mostrar: tuple[str, ...]


def _fold_tokens(text: str) -> list[str]:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.findall(r"[a-z0-9]+", without_accents)


def normalize_title(title: str) -> str:
    """Normalize title accents, punctuation, and exhibition-format suffixes."""
    tokens = _fold_tokens(title)
    while tokens and tokens[-1] in TITLE_QUALIFIERS:
        tokens.pop()
    return " ".join(tokens)


def normalize_city(city: str) -> str:
    return " ".join(_fold_tokens(city))


def match_media_title(title: str, catalog: Iterable[Media] | None = None) -> Media | None:
    """Return a unique movie matching title/original title, or None if uncertain."""
    normalized = normalize_title(title)
    if not normalized:
        return None

    movies = catalog if catalog is not None else Media.objects.filter(tipo=Media.Tipo.PELICULA)
    matches: dict[int, Media] = {}
    for movie in movies:
        candidates = (movie.titulo, movie.titulo_original)
        if any(value and normalize_title(value) == normalized for value in candidates):
            matches[movie.pk] = movie

    if len(matches) != 1:
        return None
    return next(iter(matches.values()))

def scrape_and_save_cartelera(
    cinema_provider: str,
    city_slug: str = "bogota",
) -> CarteleraScrapeResult:
    """Scrape, match, persist, and clean one cinema's showtimes."""
    city_slug = city_slug.strip().lower()
    try:
        scraper_config = SCRAPERS[cinema_provider]
    except KeyError as exc:
        raise ValueError(
            f"No existe scraper configurado para '{cinema_provider}'."
        ) from exc

    city_provider_keys = CITY_PROVIDER_KEYS.get(city_slug)
    if city_provider_keys is None:
        raise ValueError(f"No existe configuración para la ciudad '{city_slug}'.")
    provider_city_key = city_provider_keys.get(cinema_provider)
    if provider_city_key is None:
        raise ValueError(
            f"No existe configuración de '{cinema_provider}' para la ciudad "
            f"'{city_slug}'."
        )

    cartelera = scraper_config.scrape(provider_city_key)
    website = scraper_config.website
    records = [
        {**record, "ciudad": city_slug}
        for record in cartelera.funciones
    ]
    movies = list(Media.objects.filter(tipo=Media.Tipo.PELICULA))
    manual_matches = _build_manual_matches()
    matched = 0
    pending = 0
    created_functions = 0
    updated_functions = 0
    cinema_cache = _build_cinema_cache()
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
                _record_pending(record)
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
            cinema = _get_or_create_cinema(record, cinema_cache, website)
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

        now_showing = _mark_now_showing(matched_media_ids)
        deleted_functions, expired_media = cleanup_expired_showtimes()

    pending_titles = (
        TituloPendiente.objects.filter(
            ciudad=city_slug,
            cine_nombre__in={record["cine"] for record in records},
            estado=TituloPendiente.Estado.PENDIENTE,
        )
        .order_by("titulo_normalizado", "cine_nombre")
        .distinct()[:20]
    )

    return CarteleraScrapeResult(
        cine=cinema_provider,
        ciudad=city_slug,
        funciones_leidas=len(records),
        funciones_asociadas=matched,
        funciones_creadas=created_functions,
        funciones_actualizadas=updated_functions,
        titulos_pendientes=pending,
        peliculas_en_cartelera=now_showing,
        estrenos_leidos=len(cartelera.proximos_estrenos),
        estrenos_asociados=matched_releases,
        funciones_vencidas_eliminadas=deleted_functions,
        peliculas_fuera_cartelera=expired_media,
        estrenos_sin_coincidencia=tuple(unmatched_releases),
        titulos_pendientes_mostrar=tuple(
            f"#{item.pk} {item.titulo_original} — {item.cine_nombre} ({item.ciudad})"
            for item in pending_titles
        ),
    )


def _build_manual_matches() -> dict[str, Media]:
    return {
        pending.titulo_normalizado: pending.media_asociada
        for pending in TituloPendiente.objects.filter(
            estado=TituloPendiente.Estado.RESUELTO,
            media_asociada__isnull=False,
        ).select_related("media_asociada")
    }


def _mark_now_showing(media_ids: set[int]) -> int:
    if not media_ids:
        return 0

    future_media_ids = Funcion.objects.filter(
        media_id__in=media_ids,
        fecha_hora__gte=timezone.now(),
    ).values("media_id")
    return (
        Media.objects.filter(pk__in=future_media_ids)
        .exclude(estado=Media.Estado.EN_CARTELERA)
        .exclude(fecha_estreno__gt=timezone.localdate())
        .update(estado=Media.Estado.EN_CARTELERA)
    )


def _build_cinema_cache() -> dict[tuple[str, str], Cine]:
    return {
        (normalize_title(cinema.nombre), normalize_title(cinema.ciudad)): cinema
        for cinema in Cine.objects.all()
    }


def _get_or_create_cinema(
    record: NormalizedShowtime,
    cache: dict[tuple[str, str], Cine],
    website: str,
) -> Cine:
    key = (normalize_title(record["cine"]), normalize_title(record["ciudad"]))
    cinema = cache.get(key)
    if cinema is None:
        cinema = Cine.objects.create(
            nombre=record["cine"],
            ciudad=record["ciudad"],
            direccion="",
            sitio_web=website,
        )
        cache[key] = cinema
    return cinema


def _record_pending(record: NormalizedShowtime) -> None:
    normalized = normalize_title(record["titulo"])
    if not normalized:
        raise ValueError(
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


@transaction.atomic
def cleanup_expired_showtimes(now: datetime | None = None) -> tuple[int, int]:
    """Delete past showtimes and move movies without future functions off the billboard."""
    current_time = now or timezone.now()
    expired_functions = Funcion.objects.filter(fecha_hora__lt=current_time)
    deleted_count = expired_functions.count()
    expired_functions.delete()

    media_without_future_showtimes = Media.objects.filter(
        tipo=Media.Tipo.PELICULA,
        estado=Media.Estado.EN_CARTELERA,
    ).filter(
        ~Exists(
            Funcion.objects.filter(
                media_id=OuterRef("pk"),
                fecha_hora__gte=current_time,
            )
        )
    )
    moved_off_billboard = media_without_future_showtimes.update(
        estado=Media.Estado.FUERA_CARTELERA
    )
    return deleted_count, moved_off_billboard


def normalize_showtimes(
    records: Iterable[Mapping[str, object]],
) -> list[NormalizedShowtime]:
    """Normalize scraper records and remove repeated showtimes."""
    normalized: list[NormalizedShowtime] = []
    seen: set[tuple[str, ...]] = set()

    for record in records:
        showtime = normalize_showtime(record)
        identity = (
            showtime["titulo"].casefold(),
            showtime["cine"].casefold(),
            showtime["ciudad"].casefold(),
            showtime["fecha"].isoformat(),
            showtime["hora"].isoformat(),
            showtime["sala"].casefold(),
            tuple(
                sorted(
                    part.strip().casefold()
                    for part in showtime["formato"].split(",")
                    if part.strip()
                )
            ),
        )
        if identity in seen:
            continue
        seen.add(identity)
        normalized.append(showtime)

    return normalized


def normalize_showtime(record: Mapping[str, object]) -> NormalizedShowtime:
    """Convert one scraper record to CineRoll's common showtime contract."""
    showtime = _parse_datetime(record)
    return {
        "titulo": _required_text(record, "titulo"),
        "cine": _required_text(record, "cine"),
        "ciudad": _required_text(record, "ciudad"),
        "fecha": showtime.date(),
        "hora": showtime.timetz(),
        "sala": _optional_text(record.get("sala")),
        "formato": _normalize_formats(record.get("formato")),
        "fuente_scraping": _optional_text(record.get("fuente_scraping")),
        "cine_id_origen": _optional_text(record.get("cine_id_origen")),
        "funcion_id_origen": _optional_text(record.get("funcion_id_origen")),
    }


def _required_text(record: Mapping[str, object], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"El campo '{field}' es obligatorio para normalizar la función.")
    return _clean_text(value)


def _optional_text(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return _clean_text(value)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _parse_datetime(record: Mapping[str, object]) -> datetime:
    raw_datetime = record.get("fecha_hora")
    if isinstance(raw_datetime, datetime):
        showtime = raw_datetime
    elif isinstance(raw_datetime, str):
        try:
            showtime = datetime.fromisoformat(raw_datetime)
        except ValueError as exc:
            raise ValueError("El campo 'fecha_hora' debe estar en formato ISO.") from exc
    elif raw_datetime is None:
        showtime = _combine_date_and_time(record.get("fecha"), record.get("hora"))
    else:
        raise ValueError("El campo 'fecha_hora' debe ser una fecha y hora ISO.")

    if showtime.tzinfo is None:
        return showtime.replace(tzinfo=COLOMBIA_TIMEZONE)
    return showtime.astimezone(COLOMBIA_TIMEZONE)


def _combine_date_and_time(raw_date: object, raw_time: object) -> datetime:
    if isinstance(raw_date, datetime):
        parsed_date = raw_date.date()
    elif isinstance(raw_date, date):
        parsed_date = raw_date
    elif isinstance(raw_date, str):
        try:
            parsed_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise ValueError("El campo 'fecha' debe tener formato AAAA-MM-DD.") from exc
    else:
        raise ValueError("Se requiere 'fecha_hora' o los campos 'fecha' y 'hora'.")

    if isinstance(raw_time, datetime):
        parsed_time = raw_time.timetz()
    elif isinstance(raw_time, time):
        parsed_time = raw_time
    elif isinstance(raw_time, str):
        try:
            parsed_time = time.fromisoformat(raw_time)
        except ValueError as exc:
            raise ValueError("El campo 'hora' debe tener formato ISO.") from exc
    else:
        raise ValueError("Se requiere 'fecha_hora' o los campos 'fecha' y 'hora'.")

    return datetime.combine(parsed_date, parsed_time)


def _normalize_formats(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        candidates = value.split(",")
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, Mapping)):
        candidates = list(value)
    else:
        candidates = [value]

    formats: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if isinstance(candidate, Mapping):
            candidate = candidate.get("Description", candidate.get("description", ""))
        if not isinstance(candidate, str):
            if candidate is None:
                continue
            candidate = str(candidate)
        cleaned = _clean_text(candidate)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            formats.append(cleaned)
    return ", ".join(formats)