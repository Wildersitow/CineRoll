"""Datos de película que los cines publican junto a sus funciones.

Cada cine nombra los campos a su manera (``Synopsis``, ``pelicula_sinopsis``,
``GraphicUrl``, ``RunTime``...). En vez de depender de un nombre exacto, que
puede cambiar sin aviso, se buscan por palabras clave y se valida el valor.
Si un dato no aparece o no es válido, simplemente se omite.
"""

from collections.abc import Iterable, Mapping
from datetime import date, datetime, timezone as datetime_timezone
import html
import re
from typing import TypedDict
from urllib.parse import urljoin
from zoneinfo import ZoneInfo


URL_MAX_LENGTH = 200


class MovieMetadata(TypedDict, total=False):
    sinopsis: str
    duracion: int
    poster_url: str
    trailer_url: str
    fecha_estreno: date
    generos: list[str]


SYNOPSIS_KEYS = ("sinopsis", "synopsis", "overview", "resumen", "descripcion", "description")
SYNOPSIS_EXCLUDED = ("rating", "clasif", "censura", "format", "idioma", "language", "sala")
DURATION_KEYS = ("duracion", "duration", "runtime", "minutos", "length")
POSTER_KEYS = (
    "poster",
    "afiche",
    "caratula",
    "graphicurl",
    "graphic",
    "cover",
    "imagen",
    "image",
    "img",
    "foto",
)
POSTER_EXCLUDED = ("backdrop", "banner", "fondo", "background", "thumb", "logo", "icon")
TRAILER_KEYS = ("trailer", "youtube", "video")
RELEASE_KEYS = ("fechaestreno", "estreno", "openingdate", "opening", "releasedate", "release")
GENRE_KEYS = ("generos", "genero", "genres", "genre")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")


def extract_movie_metadata(
    movie: Mapping[str, object],
    base_url: str = "",
) -> MovieMetadata:
    """Saca sinopsis, duración, póster, tráiler, estreno y géneros de un objeto."""
    fields = _flatten(movie)
    metadata: MovieMetadata = {}

    synopsis = _first(
        fields, SYNOPSIS_KEYS, _parse_synopsis, excluded=SYNOPSIS_EXCLUDED
    )
    if synopsis:
        metadata["sinopsis"] = synopsis

    duration = _first(fields, DURATION_KEYS, _parse_duration)
    if duration:
        metadata["duracion"] = duration

    poster = _first(
        fields,
        POSTER_KEYS,
        lambda value: _parse_image_url(value, base_url),
        excluded=POSTER_EXCLUDED,
    )
    if poster:
        metadata["poster_url"] = poster

    trailer = _first(fields, TRAILER_KEYS, lambda value: _parse_url(value, base_url))
    if trailer:
        metadata["trailer_url"] = trailer

    release = _first(fields, RELEASE_KEYS, _parse_date)
    if release:
        metadata["fecha_estreno"] = release

    genres = _first(fields, GENRE_KEYS, _parse_genres)
    if genres:
        metadata["generos"] = genres

    return metadata


def merge_metadata(
    current: MovieMetadata | None,
    incoming: MovieMetadata | None,
) -> MovieMetadata:
    """Completa los datos que faltan sin pisar los que ya se tenían."""
    merged: MovieMetadata = dict(current or {})  # type: ignore[assignment]
    for key, value in (incoming or {}).items():
        if value and not merged.get(key):
            merged[key] = value  # type: ignore[literal-required]
    return merged


def parse_duration(value: object) -> int | None:
    return _parse_duration(value)


def _flatten(movie: Mapping[str, object]) -> list[tuple[str, object]]:
    """Devuelve (clave_normalizada, valor), incluidos los objetos anidados de un nivel."""
    fields: list[tuple[str, object]] = []
    nested: list[tuple[str, object]] = []
    for key, value in movie.items():
        if not isinstance(key, str):
            continue
        normalized = re.sub(r"[^a-z0-9]", "", key.casefold())
        if isinstance(value, Mapping):
            for inner_key, inner_value in value.items():
                if isinstance(inner_key, str):
                    nested.append(
                        (
                            normalized + re.sub(r"[^a-z0-9]", "", inner_key.casefold()),
                            inner_value,
                        )
                    )
        fields.append((normalized, value))
    return fields + nested


def _first(fields, keywords, parser, excluded: Iterable[str] = ()):
    for keyword in keywords:
        for key, value in fields:
            if keyword not in key or any(word in key for word in excluded):
                continue
            parsed = parser(value)
            if parsed:
                return parsed
    return None


def _parse_synopsis(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = html.unescape(re.sub(r"<[^>]+>", " ", value))
    text = re.sub(r"\s+", " ", text).strip()
    # Evita confundir un nombre corto (por ejemplo, un formato) con la sinopsis.
    if len(text) < 25 or " " not in text:
        return None
    return text


def _parse_duration(value: object) -> int | None:
    minutes: float | None = None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        minutes = float(value)
        if 1800 <= minutes <= 24000:
            minutes /= 60
    elif isinstance(value, str):
        text = value.strip().casefold()
        clock = re.fullmatch(r"(\d{1,2}):(\d{2})(?::\d{2})?", text)
        hours_minutes = re.search(r"(\d+)\s*h(?:oras?|rs?)?\.?\s*(?:(\d+)\s*m)?", text)
        plain = re.search(r"(\d+)", text)
        if clock:
            minutes = int(clock.group(1)) * 60 + int(clock.group(2))
        elif hours_minutes:
            minutes = int(hours_minutes.group(1)) * 60 + int(hours_minutes.group(2) or 0)
        elif plain:
            minutes = int(plain.group(1))
    if minutes is None or not 20 <= minutes <= 400:
        return None
    return int(round(minutes))


def _parse_url(value: object, base_url: str) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or " " in text:
        return None
    if text.startswith("//"):
        text = "https:" + text
    elif not text.startswith(("http://", "https://")):
        if not base_url or not ("/" in text or "." in text):
            return None
        text = urljoin(base_url.rstrip("/") + "/", text.lstrip("/"))
    if len(text) > URL_MAX_LENGTH:
        return None
    return text


def _parse_image_url(value: object, base_url: str) -> str | None:
    if isinstance(value, Mapping):
        for key in ("url", "Url", "URL", "src", "large", "medium"):
            found = _parse_image_url(value.get(key), base_url)
            if found:
                return found
        return None
    if isinstance(value, list):
        for item in value:
            found = _parse_image_url(item, base_url)
            if found:
                return found
        return None
    url = _parse_url(value, base_url)
    if url is None:
        return None
    path = url.split("?", 1)[0].casefold()
    if not (path.endswith(IMAGE_EXTENSIONS) or "image" in path or "img" in path or "poster" in path):
        return None
    return url


def _parse_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    ms_date = re.fullmatch(r"/Date\((-?\d+)(?:[+-]\d{4})?\)/", text)
    try:
        if ms_date:
            return (
                datetime.fromtimestamp(int(ms_date.group(1)) / 1000, tz=datetime_timezone.utc)
                .astimezone(ZoneInfo("America/Bogota"))
                .date()
            )
        if re.match(r"\d{4}-\d{2}-\d{2}", text):
            parsed = date.fromisoformat(text[:10])
        else:
            latin = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
            if not latin:
                return None
            parsed = date(int(latin.group(3)), int(latin.group(2)), int(latin.group(1)))
    except (OverflowError, OSError, ValueError):
        return None
    if not 1900 <= parsed.year <= 2100:
        return None
    return parsed


def _parse_genres(value: object) -> list[str] | None:
    names: list[str] = []
    if isinstance(value, str):
        names = re.split(r"\s*[,/|]\s*", value)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, Mapping):
                name = item.get("name") or item.get("nombre") or item.get("Name")
                if isinstance(name, str):
                    names.append(name)
    cleaned: list[str] = []
    for name in names:
        name = re.sub(r"\s+", " ", name).strip()
        # Descarta códigos ("12") o textos largos que no son un género.
        if len(name) < 4 or name.isdigit() or len(name) > 60:
            continue
        name = name[:1].upper() + name[1:].lower() if name.isupper() else name
        if name.casefold() not in {item.casefold() for item in cleaned}:
            cleaned.append(name)
    return cleaned or None
