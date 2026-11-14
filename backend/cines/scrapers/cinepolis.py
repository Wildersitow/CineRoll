import json
import re
from collections.abc import Mapping
from datetime import date, datetime, time, timezone as datetime_timezone
from urllib.error import URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from cines.services import (
    CarteleraData,
    NormalizedShowtime,
    ScraperError,
    normalize_showtimes,
)


CINEPOLIS_CARTELERA_URL = (
    "https://cinepolis.com.co/Cartelera.aspx/GetNowPlayingByCity"
)
USER_AGENT = "CineRoll cartelera scraper/0.1 (development project)"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class CinepolisScraperError(ScraperError):
    """Raised when Cinépolis cartelera cannot be fetched or parsed."""


def scrape_cartelera(
    city_key: str = "valledupar-colombia",
    timeout: float = 20.0,
) -> list[NormalizedShowtime]:
    return scrape_cartelera_completa(city_key=city_key, timeout=timeout).funciones


def scrape_cartelera_completa(
    city_key: str = "valledupar-colombia",
    timeout: float = 20.0,
) -> CarteleraData:
    city_key = city_key.strip().lower()
    if not re.fullmatch(r"[a-z0-9-]+", city_key):
        raise ValueError("city_key debe contener solo letras, números y guiones.")

    body = json.dumps(
        {"claveCiudad": city_key, "esVIP": False},
        separators=(",", ":"),
    ).encode("utf-8")
    request = Request(
        CINEPOLIS_CARTELERA_URL,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://cinepolis.com.co/cartelera/{city_key}",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read(MAX_RESPONSE_BYTES + 1)
            charset = response.headers.get_content_charset() or "utf-8"
    except URLError as exc:
        raise CinepolisScraperError(
            f"No se pudo consultar la cartelera de Cinépolis para {city_key}: {exc}"
        ) from exc

    if len(response_body) > MAX_RESPONSE_BYTES:
        raise CinepolisScraperError(
            "La respuesta de Cinépolis excede el tamaño permitido."
        )

    try:
        response_text = response_body.decode(charset)
    except (LookupError, UnicodeDecodeError) as exc:
        raise CinepolisScraperError(
            "Cinépolis devolvió una codificación no válida."
        ) from exc

    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise CinepolisScraperError(
            "La respuesta de cartelera de Cinépolis no es JSON válido."
        ) from exc

    return parse_cartelera_data(payload, city_key, CINEPOLIS_CARTELERA_URL)


def parse_cartelera_data(
    payload: object,
    city_key: str,
    source_url: str,
) -> CarteleraData:
    if not isinstance(payload, dict):
        raise CinepolisScraperError("La respuesta de Cinépolis debe ser un objeto JSON.")
    data = payload.get("d")
    if not isinstance(data, dict):
        raise CinepolisScraperError("La respuesta de Cinépolis no contiene el objeto 'd'.")

    cinemas = _required_list(data, "Cinemas", "d")
    showtimes: list[dict[str, object]] = []
    for cinema in cinemas:
        if not isinstance(cinema, dict):
            raise CinepolisScraperError("Cinépolis devolvió un cine inválido.")
        if cinema.get("CityKey") != city_key:
            raise CinepolisScraperError(
                f"Cinépolis devolvió una ciudad distinta de la solicitada: {city_key}."
            )

        cinema_name = _required_text(cinema, "Name", "cine")
        city_name = _required_text(cinema, "CityName", "ciudad")
        cinema_id = cinema.get("Id")
        if cinema_id is None:
            raise CinepolisScraperError("Cinépolis omitió el identificador del cine.")

        for day in _required_list(cinema, "Dates", cinema_name):
            if not isinstance(day, dict):
                raise CinepolisScraperError("Cinépolis devolvió una fecha inválida.")
            show_date = _parse_filter_date(day.get("FilterDate"))

            for movie in _required_list(day, "Movies", "fecha"):
                if not isinstance(movie, dict):
                    raise CinepolisScraperError("Cinépolis devolvió una película inválida.")
                title = movie.get("Title") or movie.get("OriginalTitle")
                if not isinstance(title, str) or not title.strip():
                    raise CinepolisScraperError(
                        "Cinépolis omitió el título de una película."
                    )

                for movie_format in _required_list(movie, "Formats", title):
                    if not isinstance(movie_format, dict):
                        raise CinepolisScraperError(
                            f"Cinépolis devolvió un formato inválido para {title}."
                        )
                    format_name = _required_text(movie_format, "Name", "formato")
                    language = _required_text(movie_format, "Language", "idioma")

                    for session in _required_list(movie_format, "Showtimes", title):
                        if not isinstance(session, dict):
                            raise CinepolisScraperError(
                                f"Cinépolis devolvió una función inválida para {title}."
                            )
                        session_cinema_id = session.get("CinemaId")
                        session_id = session.get("ShowtimeId")
                        if (
                            session_cinema_id is None
                            or str(session_cinema_id) != str(cinema_id)
                            or session_id is None
                        ):
                            raise CinepolisScraperError(
                                f"Cinépolis devolvió identificadores incompletos "
                                f"o inconsistentes para {title}."
                            )
                        showtime = _parse_time(session.get("Time"), title)
                        showtimes.append(
                            {
                                "titulo": title.strip(),
                                "cine": cinema_name,
                                "ciudad": city_name,
                                "fecha": show_date,
                                "hora": showtime,
                                "sala": "",
                                "formato": [format_name, language],
                                "fuente_scraping": source_url,
                                "cine_id_origen": str(session_cinema_id),
                                "funcion_id_origen": str(session_id),
                            }
                        )

    try:
        normalized = normalize_showtimes(showtimes)
    except ValueError as exc:
        raise CinepolisScraperError(
            f"No se pudo normalizar la cartelera de Cinépolis: {exc}"
        ) from exc
    return CarteleraData(funciones=normalized, proximos_estrenos=[])


def _required_list(
    record: Mapping[str, object],
    field: str,
    context: str,
) -> list[object]:
    value = record.get(field)
    if not isinstance(value, list):
        raise CinepolisScraperError(
            f"La lista '{field}' de Cinépolis no es válida ({context})."
        )
    return value


def _required_text(record: Mapping[str, object], field: str, context: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CinepolisScraperError(
            f"Cinépolis omitió el campo '{field}' ({context})."
        )
    return re.sub(r"\s+", " ", value).strip()


def _parse_filter_date(value: object) -> date:
    if not isinstance(value, str):
        raise CinepolisScraperError("Cinépolis omitió la fecha de las funciones.")
    match = re.fullmatch(r"/Date\((-?\d+)(?:[+-]\d{4})?\)/", value)
    if match is None:
        raise CinepolisScraperError(
            f"Cinépolis devolvió una fecha inválida: {value!r}."
        )
    try:
        timestamp = int(match.group(1)) / 1000
        return datetime.fromtimestamp(
            timestamp,
            tz=datetime_timezone.utc,
        ).astimezone(ZoneInfo("America/Bogota")).date()
    except (OverflowError, OSError, ValueError) as exc:
        raise CinepolisScraperError(
            f"Cinépolis devolvió una fecha fuera de rango: {value!r}."
        ) from exc


def _parse_time(value: object, title: str) -> time:
    if not isinstance(value, str):
        raise CinepolisScraperError(
            f"Cinépolis omitió la hora de una función de {title}."
        )
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise CinepolisScraperError(
            f"Cinépolis devolvió una hora inválida para {title}: {value!r}."
        ) from exc
