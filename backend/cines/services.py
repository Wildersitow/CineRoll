from collections.abc import Iterable, Mapping
from datetime import date, datetime, time
import unicodedata
import re
from typing import TypedDict
from zoneinfo import ZoneInfo

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


def normalize_title(title: str) -> str:
    """Normalize title accents, punctuation, and exhibition-format suffixes."""
    decomposed = unicodedata.normalize("NFKD", title.casefold())
    without_accents = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    tokens = re.findall(r"[a-z0-9]+", without_accents)
    while tokens and tokens[-1] in TITLE_QUALIFIERS:
        tokens.pop()
    return " ".join(tokens)


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