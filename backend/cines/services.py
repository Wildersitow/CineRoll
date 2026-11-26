from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, time
import logging
import unicodedata
import re
from typing import Callable, NotRequired, TypedDict
from zoneinfo import ZoneInfo

from decouple import config
from django.conf import settings
from django.db import transaction
from django.db.models import Exists, F, OuterRef, Q, QuerySet
from django.utils import timezone

from cines import tmdb
from cines.metadata import MovieMetadata, merge_metadata
from cines.models import Cine, Funcion, TituloPendiente
from media.models import Credito, Genero, Media, Persona


COLOMBIA_TIMEZONE = ZoneInfo("America/Bogota")
MINIMUM_SYNC_PERCENT = 50
TITLE_MAX_LENGTH = TituloPendiente._meta.get_field("titulo_original").max_length
CINEMA_NAME_MAX_LENGTH = Cine._meta.get_field("nombre").max_length
ROOM_MAX_LENGTH = Funcion._meta.get_field("sala").max_length
FORMAT_MAX_LENGTH = Funcion._meta.get_field("formato").max_length

MediaIndex = dict[str, dict[int, Media]]

logger = logging.getLogger(__name__)
TITLE_QUALIFIERS = {
    "2d",
    "3d",
    "4d",
    "4dx",
    "atmos",
    "castellano",
    "dbox",
    "dob",
    "doblada",
    "doblado",
    "doblaje",
    "dolby",
    "dub",
    "dublada",
    "dublado",
    "eng",
    "esp",
    "espanol",
    "hd",
    "imax",
    "ingles",
    "lat",
    "latino",
    "premium",
    "screenx",
    "sub",
    "subs",
    "subt",
    "subtitulada",
    "subtitulado",
    "subtitulos",
    "vip",
    "vo",
    "vos",
    "vose",
    "xd",
    "xe",
}
# Palabras que algunos cines ponen delante del título ("PREVENTA - Avengers").
LEADING_TITLE_QUALIFIERS = {"preventa"}
SMALL_TITLE_WORDS = {
    "a", "al", "and", "con", "de", "del", "el", "en", "for", "in", "la", "las",
    "los", "of", "on", "para", "por", "the", "to", "un", "una", "vs", "y",
}
# Separador entre título y subtítulo: "Hechizo: Bienvenidos a Hexe".
SUBTITLE_SEPARATOR = re.compile(r"\s*:\s*|\s+[-–—]\s+")
MIN_FALLBACK_KEY_LENGTH = 4
MAX_TMDB_LOOKUPS = 60

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
    titulo_alternativo: NotRequired[str]


class UpcomingRelease(TypedDict):
    titulo: str
    fecha_estreno: date
    fuente_scraping: str


@dataclass(frozen=True)
class CarteleraData:
    funciones: list[NormalizedShowtime]
    proximos_estrenos: list[UpcomingRelease]
    # Datos de cada película que publica el cine, por título normalizado.
    peliculas: dict[str, MovieMetadata] = field(default_factory=dict)


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


def _scrape_cineland(theater_code: str) -> CarteleraData:
    from cines.scrapers.cineland import scrape_cartelera_completa

    return scrape_cartelera_completa(theater_code=theater_code)


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
    "cineland": ScraperConfig(
        scrape=_scrape_cineland,
        website="https://home.cineland.co/",
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
    funciones_obsoletas_eliminadas: int = 0
    advertencia: str = ""
    peliculas_creadas: int = 0
    peliculas_creadas_mostrar: tuple[str, ...] = ()


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
    while len(tokens) > 1 and tokens[0] in LEADING_TITLE_QUALIFIERS:
        tokens.pop(0)
    return " ".join(tokens)


def main_title_key(title: str) -> str | None:
    """Título sin subtítulo, normalizado; None si el título no tiene subtítulo."""
    parts = SUBTITLE_SEPARATOR.split(title.strip(), maxsplit=1)
    if len(parts) < 2:
        return None
    main = normalize_title(parts[0])
    if not main or not normalize_title(parts[1]) or main == normalize_title(title):
        return None
    return main


def normalize_city(city: str) -> str:
    return " ".join(_fold_tokens(city))

def format_display_title(raw_title: str, normalized_title: str) -> str:
    tokens = list(re.finditer(r"[^\W_]+", raw_title))
    while tokens and all(
        part in TITLE_QUALIFIERS for part in _fold_tokens(tokens[-1].group())
    ):
        tokens.pop()
    if not tokens:
        return normalized_title

    title = raw_title[: tokens[-1].end()].strip()
    if title.isupper():
        title = title[:1].upper() + title[1:].lower()
    if normalize_title(title) != normalized_title:
        return normalized_title
    return title


def pretty_title(raw_title: str) -> str:
    """Título para mostrar: sin sufijos de formato y sin TODO EN MAYÚSCULAS."""
    tokens = list(re.finditer(r"[^\W_]+", raw_title))
    while tokens and all(
        part in TITLE_QUALIFIERS for part in _fold_tokens(tokens[-1].group())
    ):
        tokens.pop()
    start = 0
    while len(tokens) > 1 and _fold_tokens(tokens[0].group()) == ["preventa"]:
        tokens.pop(0)
        start = tokens[0].start()
    if not tokens:
        return _clean_text(raw_title)
    title = raw_title[start: tokens[-1].end()].strip(" -–—:")
    title = re.sub(r"\s*\(\s*$", "", _clean_text(title))
    if title.upper() != title:
        return title
    return _title_case(title)


def _title_case(text: str) -> str:
    words = text.lower().split(" ")
    result: list[str] = []
    capitalize_next = True
    for word in words:
        letters = re.sub(r"[^\w]", "", word)
        if (
            letters
            and letters not in SMALL_TITLE_WORDS
            and not re.search(r"[aeiouyáéíóú]", letters)
            and not letters.isdigit()
        ):
            # Siglas como "BTS" o "LV".
            formatted = word.upper()
        elif re.fullmatch(r"[ivxlcdm]+", letters) and len(letters) <= 4 and not capitalize_next:
            formatted = word.upper()
        elif capitalize_next or letters not in SMALL_TITLE_WORDS:
            index = next((i for i, ch in enumerate(word) if ch.isalpha()), None)
            formatted = (
                word if index is None else word[:index] + word[index].upper() + word[index + 1:]
            )
        else:
            formatted = word
        result.append(formatted)
        capitalize_next = word.endswith((":", ".", "?", "!", "¿", "¡")) or word in {"-", "–", "—"}
    return " ".join(result)


def build_media_index(catalog: Iterable[Media]) -> MediaIndex:
    index: MediaIndex = {}
    for movie in catalog:
        for value in (movie.titulo, movie.titulo_original):
            if not value:
                continue
            normalized = normalize_title(value)
            if normalized:
                index.setdefault(normalized, {})[movie.pk] = movie
    return index


def match_media_title(
    title: str,
    catalog: Iterable[Media] | None = None,
    alternate_title: str | None = None,
    index: MediaIndex | None = None,
) -> Media | None:
    """Return a unique movie matching either title, or None if uncertain."""
    normalized_titles: set[str] = set()
    for candidate in (title, alternate_title):
        if candidate:
            normalized = normalize_title(candidate)
            if normalized:
                normalized_titles.add(normalized)
    if not normalized_titles:
        return None

    if index is None:
        movies = (
            catalog
            if catalog is not None
            else Media.objects.filter(tipo=Media.Tipo.PELICULA)
        )
        index = build_media_index(movies)

    matches: dict[int, Media] = {}
    for normalized in normalized_titles:
        matches.update(index.get(normalized, {}))

    if len(matches) != 1:
        return None
    return next(iter(matches.values()))

@dataclass
class _NewTitle:
    """Título sin ficha en el catálogo, con todas sus variantes de esta corrida."""

    key: str
    titles: list[str] = field(default_factory=list)
    alternates: list[str] = field(default_factory=list)
    metadata: MovieMetadata = field(default_factory=dict)
    release_date: date | None = None
    first_showtime: date | None = None
    has_showtimes: bool = False


class _Catalog:
    """Índices del catálogo de películas que se actualizan durante la corrida."""

    def __init__(self, movies: Iterable[Media], aliases: dict[str, Media]):
        self.index: MediaIndex = {}
        self.main_index: MediaIndex = {}
        self.plain_index: MediaIndex = {}
        self.by_tmdb: dict[int, Media] = {}
        self.aliases = dict(aliases)
        for movie in movies:
            self.add(movie)

    def add(self, movie: Media) -> None:
        if movie.tmdb_id:
            self.by_tmdb[movie.tmdb_id] = movie
        active = movie.estado != Media.Estado.FUERA_CARTELERA
        for value in (movie.titulo, movie.titulo_original):
            if not value:
                continue
            normalized = normalize_title(value)
            if not normalized:
                continue
            self.index.setdefault(normalized, {})[movie.pk] = movie
            if not active:
                continue
            main = main_title_key(value)
            if main is None:
                self.plain_index.setdefault(normalized, {})[movie.pk] = movie
            else:
                self.main_index.setdefault(main, {})[movie.pk] = movie

    def add_alias(self, normalized: str, movie: Media) -> None:
        if normalized and not self.is_direct(normalized, movie):
            self.aliases[normalized] = movie

    def is_direct(self, normalized: str, movie: Media) -> bool:
        return movie.pk in self.index.get(normalized, {})

    def resolve(
        self,
        title: str,
        alternate_title: str | None = None,
    ) -> tuple[Media | None, bool]:
        """Devuelve (película, ambigua). Ambigua = varias fichas posibles."""
        raw_titles = [value for value in (title, alternate_title) if value]
        keys = {normalize_title(value) for value in raw_titles} - {""}
        if not keys:
            return None, False

        matches: dict[int, Media] = {}
        for key in keys:
            matches.update(self.index.get(key, {}))
        if len(matches) == 1:
            return next(iter(matches.values())), False

        for key in keys:
            if key in self.aliases:
                return self.aliases[key], False
        if matches:
            return None, True

        # "Hechizo" ↔ "Hechizo: Bienvenidos a Hexe" solo entre películas vigentes.
        fallback: dict[int, Media] = {}
        for value in raw_titles:
            main = main_title_key(value)
            if main is None:
                full = normalize_title(value)
                if len(full) >= MIN_FALLBACK_KEY_LENGTH:
                    fallback.update(self.main_index.get(full, {}))
            elif len(main) >= MIN_FALLBACK_KEY_LENGTH:
                fallback.update(self.plain_index.get(main, {}))
        if len(fallback) == 1:
            return next(iter(fallback.values())), False
        return None, len(fallback) > 1


def auto_create_enabled() -> bool:
    value = getattr(settings, "CARTELERA_CREAR_PELICULAS", None)
    if value is None:
        return config("CARTELERA_CREAR_PELICULAS", default=True, cast=bool)
    return bool(value)


def scrape_and_save_cartelera(
    cinema_provider: str,
    city_slug: str = "bogota",
    crear_peliculas: bool | None = None,
) -> CarteleraScrapeResult:
    """Scrape, match, persist, and clean one cinema's showtimes.

    Con ``crear_peliculas`` (por defecto, el ajuste CARTELERA_CREAR_PELICULAS,
    activo si no se define) los títulos sin ficha en el catálogo se crean con los
    datos del cine y, si hay TMDB_API_KEY, con los de TMDB.
    """
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
    if crear_peliculas is None:
        crear_peliculas = auto_create_enabled()

    cartelera = scraper_config.scrape(provider_city_key)
    website = scraper_config.website
    synchronization_time = timezone.now()
    previous_future_count = _future_showtimes_for_source(
        city_slug,
        website,
        synchronization_time,
    ).count()
    records = [
        {**record, "ciudad": city_slug}
        for record in cartelera.funciones
    ]
    catalog = _Catalog(
        Media.objects.filter(tipo=Media.Tipo.PELICULA),
        _build_manual_matches(),
    )
    # Fichas de otros tipos con tmdb_id también cuentan, para no repetir el id.
    for other in Media.objects.exclude(tipo=Media.Tipo.PELICULA).exclude(tmdb_id=None):
        catalog.by_tmdb[other.tmdb_id] = other
    ignored_titles = _build_ignored_titles()

    new_titles: dict[str, _NewTitle] = {}
    tmdb_results: dict[str, tmdb.TmdbPelicula | None] = {}
    if crear_peliculas:
        new_titles = _collect_new_titles(cartelera, records, catalog, ignored_titles)
        # Las consultas a TMDB se hacen antes de abrir la transacción.
        if tmdb.configurado():
            for key, new_title in list(new_titles.items())[:MAX_TMDB_LOOKUPS]:
                tmdb_results[key] = tmdb.buscar_pelicula(
                    new_title.titles + new_title.alternates,
                    normalize_title,
                )

    matched = 0
    pending = 0
    created_functions = 0
    updated_functions = 0
    cinema_cache = _build_cinema_cache()
    matched_media_ids: set[int] = set()
    matched_releases = 0
    unmatched_releases: list[str] = []
    incoming_future_count = 0
    expected_future_functions: set[tuple[int, int, datetime, str, str]] = set()
    obsolete_functions_deleted = 0
    synchronization_warning: str | None = None
    created_media: list[Media] = []
    remembered_aliases: set[tuple[str, str, str]] = set()

    with transaction.atomic():
        for new_title in new_titles.values():
            media, created = _resolve_or_create_media(
                new_title, catalog, tmdb_results.get(new_title.key)
            )
            if media is None:
                continue
            if created:
                created_media.append(media)
            keys = {
                normalize_title(value)
                for value in new_title.titles + new_title.alternates
            } - {""}
            for key in keys:
                catalog.add_alias(key, media)
            # Los títulos pendientes de cualquier cine quedan resueltos con la nueva ficha.
            TituloPendiente.objects.filter(
                titulo_normalizado__in=keys,
                estado=TituloPendiente.Estado.PENDIENTE,
            ).update(
                estado=TituloPendiente.Estado.RESUELTO,
                media_asociada=media,
                ultima_deteccion=timezone.now(),
            )

        for release in cartelera.proximos_estrenos:
            media, _ambiguous = catalog.resolve(release["titulo"])
            if media is None:
                unmatched_releases.append(release["titulo"])
                continue
            media.fecha_estreno = release["fecha_estreno"]
            media.estado = Media.Estado.PROXIMO_ESTRENO
            media.save(update_fields=["fecha_estreno", "estado"])
            matched_releases += 1

        for record in records:
            normalized = normalize_title(record["titulo"])
            ignored_key = (normalized, record["cine"], record["ciudad"])
            if ignored_key in ignored_titles:
                continue

            media, _ambiguous = catalog.resolve(
                record["titulo"],
                alternate_title=record.get("titulo_alternativo"),
            )
            if media is None:
                _record_pending(record)
                pending += 1
                continue

            TituloPendiente.objects.filter(
                Q(titulo_normalizado=normalized) | Q(titulo_original=record["titulo"]),
                cine_nombre=record["cine"],
                ciudad=record["ciudad"],
                estado=TituloPendiente.Estado.PENDIENTE,
            ).update(
                estado=TituloPendiente.Estado.RESUELTO,
                media_asociada=media,
                ultima_deteccion=timezone.now(),
            )
            alias_key = (normalized, record["cine"], record["ciudad"])
            if (
                normalized
                and alias_key not in remembered_aliases
                and not catalog.is_direct(normalized, media)
                and not (
                    record.get("titulo_alternativo")
                    and catalog.is_direct(
                        normalize_title(record["titulo_alternativo"]), media
                    )
                )
            ):
                # Guarda la equivalencia para no volver a buscarla (ni gastar TMDB).
                _remember_alias(record, normalized, media)
                remembered_aliases.add(alias_key)

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
            if scheduled_at >= synchronization_time:
                incoming_future_count += 1
                expected_future_functions.add(
                    (
                        cinema.pk,
                        media.pk,
                        scheduled_at,
                        record["sala"],
                        record["formato"],
                    )
                )
            matched += 1
            matched_media_ids.add(media.pk)
            if created:
                created_functions += 1
            else:
                updated_functions += 1

        if not records:
            synchronization_warning = (
                f"Se omitió la sincronización de funciones futuras de "
                f"{cinema_provider} ({city_slug}): la respuesta llegó vacía."
            )
        elif (
            previous_future_count
            and incoming_future_count * 100
            < previous_future_count * MINIMUM_SYNC_PERCENT
        ):
            synchronization_warning = (
                f"Se omitió la sincronización de funciones futuras de "
                f"{cinema_provider} ({city_slug}): "
                f"{incoming_future_count} funciones válidas frente a "
                f"{previous_future_count} previas, menos del "
                f"{MINIMUM_SYNC_PERCENT}%."
            )
        else:
            obsolete_functions_deleted = _delete_obsolete_future_showtimes(
                city_slug,
                website,
                synchronization_time,
                expected_future_functions,
            )

        now_showing = _mark_now_showing(matched_media_ids)
        deleted_functions, expired_media = cleanup_expired_showtimes()

    if synchronization_warning:
        logger.warning(synchronization_warning)

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
        funciones_obsoletas_eliminadas=obsolete_functions_deleted,
        advertencia=synchronization_warning or "",
        peliculas_creadas=len(created_media),
        peliculas_creadas_mostrar=tuple(
            f"#{media.pk} {media.titulo}"
            + (" (con datos de TMDB)" if media.tmdb_id else "")
            for media in created_media
        ),
    )


def _collect_new_titles(
    cartelera: CarteleraData,
    records: list[NormalizedShowtime],
    catalog: _Catalog,
    ignored_titles: set[tuple[str, str, str]],
) -> dict[str, _NewTitle]:
    """Agrupa los títulos sin ficha; las variantes que normalizan igual van juntas."""
    new_titles: dict[str, _NewTitle] = {}

    def collect(title: str, alternate: str | None) -> _NewTitle | None:
        media, ambiguous = catalog.resolve(title, alternate)
        if media is not None or ambiguous:
            return None
        key = normalize_title(title)
        if not key:
            return None
        group = new_titles.setdefault(key, _NewTitle(key=key))
        if title not in group.titles:
            group.titles.append(title)
        if alternate and alternate not in group.alternates:
            group.alternates.append(alternate)
        for candidate in (title, alternate):
            if candidate:
                group.metadata = merge_metadata(
                    group.metadata,
                    cartelera.peliculas.get(normalize_title(candidate)),
                )
        return group

    for release in cartelera.proximos_estrenos:
        group = collect(release["titulo"], None)
        if group is not None and group.release_date is None:
            group.release_date = release["fecha_estreno"]

    for record in records:
        ignored_key = (normalize_title(record["titulo"]), record["cine"], record["ciudad"])
        if ignored_key in ignored_titles:
            continue
        group = collect(record["titulo"], record.get("titulo_alternativo"))
        if group is not None:
            group.has_showtimes = True
            if group.first_showtime is None or record["fecha"] < group.first_showtime:
                group.first_showtime = record["fecha"]
    return new_titles


def _resolve_or_create_media(
    new_title: _NewTitle,
    catalog: _Catalog,
    tmdb_movie: "tmdb.TmdbPelicula | None",
) -> tuple[Media | None, bool]:
    """Busca otra vez (puede haberse creado en esta corrida) y si no, crea la ficha."""
    for title in new_title.titles:
        alternate = new_title.alternates[0] if new_title.alternates else None
        media, ambiguous = catalog.resolve(title, alternate)
        if media is not None:
            return media, False
        if ambiguous:
            return None, False

    if tmdb_movie is not None:
        existing = catalog.by_tmdb.get(tmdb_movie.tmdb_id)
        if existing is not None:
            return existing, False
        # El catálogo puede tenerla con el título que usa TMDB, aún sin tmdb_id.
        existing, ambiguous = catalog.resolve(
            tmdb_movie.titulo, tmdb_movie.titulo_original or None
        )
        if ambiguous:
            return None, False
        if existing is not None:
            if existing.tmdb_id is None:
                existing.tmdb_id = tmdb_movie.tmdb_id
                existing.save(update_fields=["tmdb_id"])
                catalog.by_tmdb[tmdb_movie.tmdb_id] = existing
            return existing, False

    media = _create_media(new_title, tmdb_movie)
    catalog.add(media)
    return media, True


def _create_media(
    new_title: _NewTitle,
    tmdb_movie: "tmdb.TmdbPelicula | None",
) -> Media:
    metadata = new_title.metadata
    display_titles = [pretty_title(title) for title in new_title.titles]
    # Si algún cine escribe el título con mayúsculas y minúsculas, se prefiere ese.
    mixed = [title for title, raw in zip(display_titles, new_title.titles) if raw.upper() != raw]
    titulo = Counter(mixed or display_titles).most_common(1)[0][0]
    titulo_original = next(
        (
            pretty_title(alternate)
            for alternate in new_title.alternates
            if normalize_title(alternate) != new_title.key
        ),
        "",
    )
    sinopsis = metadata.get("sinopsis", "")
    duracion = metadata.get("duracion")
    poster_url = metadata.get("poster_url", "")
    trailer_url = metadata.get("trailer_url", "")
    backdrop_url = ""
    fecha_estreno = new_title.release_date or metadata.get("fecha_estreno")
    generos = list(metadata.get("generos", []))
    directores: tuple[str, ...] = ()
    actores: tuple[str, ...] = ()

    if tmdb_movie is not None:
        titulo = tmdb_movie.titulo or titulo
        if tmdb_movie.titulo_original and normalize_title(
            tmdb_movie.titulo_original
        ) != normalize_title(titulo):
            titulo_original = tmdb_movie.titulo_original
        elif normalize_title(titulo_original) == normalize_title(titulo):
            titulo_original = ""
        sinopsis = tmdb_movie.sinopsis or sinopsis
        duracion = tmdb_movie.duracion or duracion
        poster_url = tmdb_movie.poster_url or poster_url
        backdrop_url = tmdb_movie.backdrop_url
        trailer_url = tmdb_movie.trailer_url or trailer_url
        fecha_estreno = fecha_estreno or tmdb_movie.fecha_estreno
        generos = list(tmdb_movie.generos) or generos
        directores = tmdb_movie.directores
        actores = tmdb_movie.actores

    # Con funciones ya publicadas, la película no puede estrenarse después de la primera.
    if (
        new_title.first_showtime
        and fecha_estreno
        and fecha_estreno > new_title.first_showtime
    ):
        fecha_estreno = new_title.first_showtime

    media = Media.objects.create(
        titulo=_truncate(titulo, TITLE_MAX_LENGTH),
        titulo_original=_truncate(titulo_original, TITLE_MAX_LENGTH),
        tipo=Media.Tipo.PELICULA,
        sinopsis=sinopsis,
        duracion=duracion if duracion and 0 < duracion < 32767 else None,
        poster_url=poster_url,
        backdrop_url=backdrop_url,
        trailer_url=trailer_url,
        fecha_estreno=fecha_estreno,
        estado=Media.Estado.PROXIMO_ESTRENO,
        tmdb_id=tmdb_movie.tmdb_id if tmdb_movie else None,
        creado_automaticamente=True,
    )
    apply_genres_and_credits(media, generos, directores, actores)
    logger.info("Película creada desde la cartelera: %s (#%s)", media.titulo, media.pk)
    return media


def apply_genres_and_credits(
    media: Media,
    generos: Iterable[str],
    directores: Iterable[str] = (),
    actores: Iterable[str] = (),
) -> None:
    genre_field_length = Genero._meta.get_field("nombre").max_length
    for nombre in generos:
        nombre = _truncate(_clean_text(nombre), genre_field_length)
        if not nombre:
            continue
        genero = Genero.objects.filter(nombre__iexact=nombre).first()
        if genero is None:
            genero = Genero.objects.create(nombre=nombre)
        media.generos.add(genero)

    person_field_length = Persona._meta.get_field("nombre").max_length
    for rol, nombres in ((Credito.Rol.DIRECTOR, directores), (Credito.Rol.ACTOR, actores)):
        for nombre in nombres:
            nombre = _truncate(_clean_text(nombre), person_field_length)
            if not nombre:
                continue
            persona = Persona.objects.filter(nombre__iexact=nombre).first()
            if persona is None:
                persona = Persona.objects.create(nombre=nombre)
            Credito.objects.get_or_create(media=media, persona=persona, rol=rol)


def _remember_alias(record: NormalizedShowtime, normalized: str, media: Media) -> None:
    TituloPendiente.objects.update_or_create(
        titulo_normalizado=normalized,
        cine_nombre=record["cine"],
        ciudad=record["ciudad"],
        defaults={
            "titulo_original": record["titulo"],
            "fuente_scraping": record["fuente_scraping"],
            "estado": TituloPendiente.Estado.RESUELTO,
            "media_asociada": media,
        },
    )


def _future_showtimes_for_source(
    city_slug: str,
    website: str,
    now: datetime,
) -> QuerySet[Funcion]:
    return Funcion.objects.filter(
        cine__ciudad=city_slug,
        cine__sitio_web=website,
        fecha_hora__gte=now,
    )


def _delete_obsolete_future_showtimes(
    city_slug: str,
    website: str,
    now: datetime,
    expected_functions: set[tuple[int, int, datetime, str, str]],
) -> int:
    current_functions = _future_showtimes_for_source(
        city_slug,
        website,
        now,
    ).values_list("pk", "cine_id", "media_id", "fecha_hora", "sala", "formato")
    obsolete_ids = [
        function_id
        for (
            function_id,
            cinema_id,
            media_id,
            scheduled_at,
            room,
            format_name,
        ) in current_functions
        if (cinema_id, media_id, scheduled_at, room, format_name)
        not in expected_functions
    ]
    if not obsolete_ids:
        return 0
    Funcion.objects.filter(pk__in=obsolete_ids).delete()
    return len(obsolete_ids)


def _build_manual_matches() -> dict[str, Media]:
    matches: dict[str, Media] = {}
    for pending in TituloPendiente.objects.filter(
        estado=TituloPendiente.Estado.RESUELTO,
        media_asociada__isnull=False,
    ).select_related("media_asociada"):
        # También con la normalización actual, por si cambió desde que se guardó.
        for key in (pending.titulo_normalizado, normalize_title(pending.titulo_original)):
            if key:
                matches.setdefault(key, pending.media_asociada)
    return matches

def _build_ignored_titles() -> set[tuple[str, str, str]]:
    ignored: set[tuple[str, str, str]] = set()
    for normalized, original, cinema, city in TituloPendiente.objects.filter(
        estado=TituloPendiente.Estado.IGNORADO
    ).values_list("titulo_normalizado", "titulo_original", "cine_nombre", "ciudad"):
        ignored.add((normalized, cinema, city))
        ignored.add((normalize_title(original), cinema, city))
    return ignored


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
    normalized: NormalizedShowtime = {
        "titulo": _truncate(_required_text(record, "titulo"), TITLE_MAX_LENGTH),
        "cine": _truncate(_required_text(record, "cine"), CINEMA_NAME_MAX_LENGTH),
        "ciudad": _required_text(record, "ciudad"),
        "fecha": showtime.date(),
        "hora": showtime.timetz(),
        "sala": _truncate(_optional_text(record.get("sala")), ROOM_MAX_LENGTH),
        "formato": _truncate(
            _normalize_formats(record.get("formato")), FORMAT_MAX_LENGTH
        ),
        "fuente_scraping": _optional_text(record.get("fuente_scraping")),
        "cine_id_origen": _optional_text(record.get("cine_id_origen")),
        "funcion_id_origen": _optional_text(record.get("funcion_id_origen")),
    }
    alternate_title = _optional_text(record.get("titulo_alternativo"))
    if alternate_title:
        normalized["titulo_alternativo"] = alternate_title
    return normalized


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

def _truncate(value: str, limit: int) -> str:
    return value[:limit].rstrip()


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