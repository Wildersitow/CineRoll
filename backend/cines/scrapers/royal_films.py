import json
import re
from collections.abc import Mapping
from datetime import date, datetime, time
from time import sleep
from urllib.error import URLError
from urllib.request import Request, urlopen

from cines.services import (
    CarteleraData,
    NormalizedShowtime,
    ScraperError,
    normalize_showtimes,
)


ROYAL_FILMS_API_URL = "https://cinemasroyalfilms.com/api"
REQUEST_PAUSE_SECONDS = 1.0
USER_AGENT = "CineRoll cartelera scraper/0.1 (development project)"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class RoyalFilmsScraperError(ScraperError):
    """Raised when Royal Films cartelera cannot be fetched or parsed."""


def scrape_cartelera(
    city_id: str = "1006",
    timeout: float = 20.0,
) -> list[NormalizedShowtime]:
    return scrape_cartelera_completa(city_id=city_id, timeout=timeout).funciones


def scrape_cartelera_completa(
    city_id: str = "1006",
    timeout: float = 20.0,
) -> CarteleraData:
    city_id = city_id.strip()
    if not city_id.isdecimal():
        raise ValueError("city_id debe contener solo números.")

    billboard_url = f"{ROYAL_FILMS_API_URL}/billboard/city/{city_id}"
    billboard = _fetch_json(billboard_url, timeout)
    movies = _parse_billboard_movies(billboard)

    function_responses: dict[str, object] = {}
    for movie_id, _title in movies:
        sleep(REQUEST_PAUSE_SECONDS)
        functions_url = (
            f"{ROYAL_FILMS_API_URL}/movies/functions/{movie_id}/city/{city_id}"
        )
        function_responses[movie_id] = _fetch_json(functions_url, timeout)

    return parse_cartelera_data(
        billboard,
        function_responses,
        city_id,
    )


def parse_cartelera_data(
    billboard: object,
    function_responses: Mapping[str, object],
    city_id: str,
) -> CarteleraData:
    records: list[dict[str, object]] = []
    for movie_id, title in _parse_billboard_movies(billboard):
        response = function_responses.get(movie_id)
        if response is None:
            raise RoyalFilmsScraperError(
                f"Falta la respuesta de funciones para la película {movie_id}."
            )
        functions = _response_data(response, f"película {movie_id}")

        for function in functions:
            if not isinstance(function, dict):
                raise RoyalFilmsScraperError(
                    f"Royal Films devolvió una función inválida para {title}."
                )
            function_movie_id = function.get("funcion_pelicula_id")
            if (
                function_movie_id is not None
                and str(function_movie_id) != movie_id
            ):
                raise RoyalFilmsScraperError(
                    f"Royal Films devolvió una función de otra película "
                    f"para {title}."
                )

            cinema = _required_object(function, "multicine", title)
            room = _required_object(function, "sala", title)
            movie_format = _required_object(function, "formato", title)
            cinema_id = function.get("funcion_multicine_id")
            function_id = function.get("funcion_id")
            if cinema_id is None or function_id is None:
                raise RoyalFilmsScraperError(
                    f"Royal Films omitió identificadores de origen para {title}."
                )

            function_date = _parse_date(function.get("funcion_fecha"), title)
            function_time = _parse_local_time(
                function.get("funcion_hora_inicio"),
                title,
            )
            records.append(
                {
                    "titulo": title,
                    "cine": _required_text(cinema, "multicine_nombre", title),
                    "ciudad": "valledupar",
                    "fecha": function_date,
                    "hora": function_time,
                    "sala": _required_text(room, "sala_nombre", title),
                    "formato": _required_text(
                        movie_format,
                        "formato_nombre",
                        title,
                    ),
                    "fuente_scraping": (
                        f"{ROYAL_FILMS_API_URL}/movies/functions/"
                        f"{movie_id}/city/{city_id}"
                    ),
                    "cine_id_origen": str(cinema_id),
                    "funcion_id_origen": str(function_id),
                }
            )

    try:
        normalized = normalize_showtimes(records)
    except ValueError as exc:
        raise RoyalFilmsScraperError(
            f"No se pudo normalizar la cartelera de Royal Films: {exc}"
        ) from exc
    return CarteleraData(funciones=normalized, proximos_estrenos=[])


def _fetch_json(url: str, timeout: float) -> object:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            charset = response.headers.get_content_charset() or "utf-8"
    except URLError as exc:
        raise RoyalFilmsScraperError(
            f"No se pudo consultar la cartelera de Royal Films: {exc}"
        ) from exc

    if len(body) > MAX_RESPONSE_BYTES:
        raise RoyalFilmsScraperError(
            "La respuesta de Royal Films excede el tamaño permitido."
        )
    try:
        return json.loads(body.decode(charset))
    except (LookupError, UnicodeDecodeError) as exc:
        raise RoyalFilmsScraperError(
            "Royal Films devolvió una codificación no válida."
        ) from exc
    except json.JSONDecodeError as exc:
        raise RoyalFilmsScraperError(
            "La respuesta de Royal Films no es JSON válido."
        ) from exc


def _parse_billboard_movies(payload: object) -> list[tuple[str, str]]:
    movies = _response_data(payload, "cartelera")
    parsed: list[tuple[str, str]] = []
    for entry in movies:
        if not isinstance(entry, dict):
            raise RoyalFilmsScraperError(
                "Royal Films devolvió una película inválida en la cartelera."
            )
        movie = entry.get("pelicula")
        if not isinstance(movie, dict):
            raise RoyalFilmsScraperError(
                "Royal Films omitió el objeto película de la cartelera."
            )
        movie_id = movie.get("pelicula_id")
        if movie_id is None or not str(movie_id).isdecimal():
            raise RoyalFilmsScraperError(
                "Royal Films devolvió un identificador de película inválido."
            )
        title = (
            movie.get("pelicula_titulo")
            or movie.get("pelicula_nombre_formato")
            or movie.get("pelicula_nombre_original")
        )
        if not isinstance(title, str) or not title.strip():
            raise RoyalFilmsScraperError(
                "Royal Films omitió el título de una película."
            )
        parsed.append((str(movie_id), re.sub(r"\s+", " ", title).strip()))
    return parsed


def _response_data(payload: object, context: str) -> list[object]:
    if not isinstance(payload, dict) or payload.get("status") is not True:
        raise RoyalFilmsScraperError(
            f"Royal Films devolvió una respuesta inválida para {context}."
        )
    data = payload.get("data")
    if not isinstance(data, list):
        raise RoyalFilmsScraperError(
            f"Royal Films omitió la lista de datos para {context}."
        )
    return data


def _required_object(
    record: Mapping[str, object],
    field: str,
    title: str,
) -> Mapping[str, object]:
    value = record.get(field)
    if not isinstance(value, dict):
        raise RoyalFilmsScraperError(
            f"Royal Films omitió el objeto '{field}' para {title}."
        )
    return value


def _required_text(
    record: Mapping[str, object],
    field: str,
    title: str,
) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RoyalFilmsScraperError(
            f"Royal Films omitió el campo '{field}' para {title}."
        )
    return re.sub(r"\s+", " ", value).strip()


def _parse_date(value: object, title: str) -> date:
    if not isinstance(value, str):
        raise RoyalFilmsScraperError(
            f"Royal Films omitió la fecha de una función de {title}."
        )
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise RoyalFilmsScraperError(
            f"Royal Films devolvió una fecha inválida para {title}: {value!r}."
        ) from exc


def _parse_local_time(value: object, title: str) -> time:
    """Keep the supplied clock time; its UTC suffix is not a timezone conversion."""
    if not isinstance(value, str):
        raise RoyalFilmsScraperError(
            f"Royal Films omitió la hora de una función de {title}."
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RoyalFilmsScraperError(
            f"Royal Films devolvió una hora inválida para {title}: {value!r}."
        ) from exc
    return time(parsed.hour, parsed.minute)
