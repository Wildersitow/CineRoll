import json
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
from time import sleep
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.utils import timezone
from decouple import config

from cines.services import (
    CarteleraData,
    NormalizedShowtime,
    ScraperError,
    normalize_showtimes,
)


CINELAND_CARTELERA_URL = "https://cineland.website/api_point_back.php"
CINELAND_CINEMA_NAME = "CineLand C.C. Mayales"
CINELAND_CITY = "valledupar"
DEFAULT_THEATER_CODE = "0051"
DEFAULT_RANGE_DAYS = 7
REQUEST_PAUSE_SECONDS = 1.0
USER_AGENT = "CineRoll cartelera scraper/0.1 (development project)"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class CinelandScraperError(ScraperError):
    """Raised when Cineland's cartelera cannot be fetched or parsed."""


def scrape_cartelera(
    theater_code: str = DEFAULT_THEATER_CODE,
    *,
    days: int = DEFAULT_RANGE_DAYS,
    start_date: date | None = None,
    timeout: float = 20.0,
    api_key: str | None = None,
    client_email: str | None = None,
    client_password: str | None = None,
) -> list[NormalizedShowtime]:
    return scrape_cartelera_completa(
        theater_code,
        days=days,
        start_date=start_date,
        timeout=timeout,
        api_key=api_key,
        client_email=client_email,
        client_password=client_password,
    ).funciones


def scrape_cartelera_completa(
    theater_code: str = DEFAULT_THEATER_CODE,
    *,
    days: int = DEFAULT_RANGE_DAYS,
    start_date: date | None = None,
    timeout: float = 20.0,
    api_key: str | None = None,
    client_email: str | None = None,
    client_password: str | None = None,
) -> CarteleraData:
    theater_code = theater_code.strip()
    if not theater_code.isdecimal():
        raise ValueError("theater_code debe contener solo números.")
    if type(days) is not int or not 1 <= days <= DEFAULT_RANGE_DAYS:
        raise ValueError("days debe ser un entero entre 1 y 7.")

    first_day = start_date or timezone.localdate()
    if isinstance(first_day, datetime):
        first_day = first_day.date()
    if not isinstance(first_day, date):
        raise ValueError("start_date debe ser una fecha.")

    api_key, client_email, client_password = _auth_settings(
        api_key,
        client_email,
        client_password,
    )
    token = _get_token(api_key, client_email, client_password, timeout)
    usrlock = _get_usrlock(api_key, token, timeout)

    showtimes: list[dict[str, object]] = []
    for day_index in range(days):
        request_date = first_day + timedelta(days=day_index)
        parsed_day = _fetch_day(
            theater_code,
            request_date,
            usrlock=usrlock,
            api_key=api_key,
            token=token,
            timeout=timeout,
        )
        showtimes.extend(parsed_day.funciones)
        if day_index < days - 1:
            sleep(REQUEST_PAUSE_SECONDS)

    try:
        normalized = normalize_showtimes(showtimes)
    except ValueError as exc:
        raise CinelandScraperError(
            f"No se pudo normalizar la cartelera de Cineland: {exc}"
        ) from exc
    return CarteleraData(funciones=normalized, proximos_estrenos=[])


def _auth_settings(
    api_key: str | None,
    client_email: str | None,
    client_password: str | None,
) -> tuple[str, str, str]:
    values = (
        api_key if api_key is not None else config("CINELAND_API_KEY", default=""),
        client_email
        if client_email is not None
        else config("CINELAND_EMAIL", default=""),
        client_password
        if client_password is not None
        else config("CINELAND_PASSWORD", default=""),
    )
    cleaned = tuple(value.strip() for value in values)
    if not all(cleaned):
        raise CinelandScraperError(
            "Configura CINELAND_API_KEY, CINELAND_EMAIL y CINELAND_PASSWORD "
            "en el entorno del backend."
        )
    return cleaned


def _get_token(
    api_key: str,
    client_email: str,
    client_password: str,
    timeout: float,
) -> str:
    payload = _post_json(
        {"email": client_email, "pwd": client_password},
        api_key=api_key,
        route="login",
        timeout=timeout,
    )
    _check_transaction(payload)
    data = payload.get("data") if isinstance(payload, dict) else None
    token = data.get("token") if isinstance(data, dict) else None
    if not isinstance(token, str) or not token.strip():
        raise CinelandScraperError("Cineland no devolvió un token de sesión válido.")
    return token.strip()


def _get_usrlock(api_key: str, token: str, timeout: float) -> str:
    payload = _post_json(
        {},
        api_key=api_key,
        route="get_consecutivo_temporal",
        authorization=token,
        timeout=timeout,
    )
    _check_transaction(payload)
    data = payload.get("data") if isinstance(payload, dict) else None
    usrlock = data.get("usrlock") if isinstance(data, dict) else None
    if not isinstance(usrlock, str) or not usrlock.strip():
        raise CinelandScraperError("Cineland no devolvió un usrlock válido.")
    return usrlock.strip()


def _fetch_day(
    theater_code: str,
    request_date: date,
    *,
    usrlock: str,
    api_key: str,
    token: str,
    timeout: float,
) -> CarteleraData:
    date_value = request_date.isoformat()
    payload = _post_json(
        {
            "usrlock": usrlock,
            "fechacon1": date_value,
            "fechacon2": date_value,
            "codteatro": theater_code,
        },
        api_key=api_key,
        route="get_cartelera_agrupada",
        authorization=token,
        timeout=timeout,
    )
    return parse_cartelera_data(
        payload,
        theater_code=theater_code,
        source_url=CINELAND_CARTELERA_URL,
    )


def _post_json(
    payload: Mapping[str, object],
    *,
    api_key: str,
    route: str,
    authorization: str | None = None,
    timeout: float,
) -> object:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json; charset=utf-8",
        "Api-Key": api_key,
        "Route": route,
    }
    if authorization:
        headers["Authorization"] = authorization
    request = Request(
        CINELAND_CARTELERA_URL,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers=headers,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read(MAX_RESPONSE_BYTES + 1)
    except URLError as exc:
        raise CinelandScraperError(
            f"No se pudo consultar la ruta '{route}' de Cineland: {exc}"
        ) from exc

    if len(response_body) > MAX_RESPONSE_BYTES:
        raise CinelandScraperError(
            "La respuesta de Cineland excede el tamaño permitido."
        )
    return _decode_json(response_body)


def parse_cartelera_response(
    body: bytes,
    *,
    theater_code: str = DEFAULT_THEATER_CODE,
    source_url: str = CINELAND_CARTELERA_URL,
) -> CarteleraData:
    payload = _decode_json(body)
    return parse_cartelera_data(
        payload,
        theater_code=theater_code,
        source_url=source_url,
    )


def _decode_json(body: bytes) -> object:
    try:
        return json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CinelandScraperError(
            "La respuesta de Cineland no contiene JSON UTF-8 válido."
        ) from exc


def _check_transaction(payload: object) -> None:
    if not isinstance(payload, dict):
        raise CinelandScraperError("La respuesta de Cineland debe ser un objeto JSON.")
    transaction_status = payload.get("transaction_status")
    if (
        isinstance(transaction_status, dict)
        and transaction_status.get("status") is False
    ):
        message = transaction_status.get("msg") or "transacción rechazada"
        raise CinelandScraperError(f"Cineland rechazó la consulta: {message}")


def parse_cartelera_data(
    payload: object,
    *,
    theater_code: str = DEFAULT_THEATER_CODE,
    source_url: str = CINELAND_CARTELERA_URL,
) -> CarteleraData:
    if not isinstance(payload, dict):
        raise CinelandScraperError("La respuesta de Cineland debe ser un objeto JSON.")

    _check_transaction(payload)

    movies = payload.get("data")
    if not isinstance(movies, list):
        raise CinelandScraperError(
            "La respuesta de Cineland no contiene una lista 'data'."
        )

    records: list[dict[str, object]] = []
    for movie in movies:
        if not isinstance(movie, dict):
            raise CinelandScraperError("Cineland devolvió una película inválida.")
        original_title = _required_text(
            movie, "nombre_pelicula_original", "película"
        )
        dates = _required_list(movie, "fechas", original_title)

        for date_record in dates:
            if not isinstance(date_record, dict):
                raise CinelandScraperError(
                    f"Cineland devolvió una fecha inválida para {original_title}."
                )
            show_date = _parse_date(date_record.get("date"), original_title)
            attributes = _required_list(
                date_record, "atributos", original_title
            )

            for attribute in attributes:
                if not isinstance(attribute, dict):
                    raise CinelandScraperError(
                        f"Cineland devolvió un formato inválido para {original_title}."
                    )
                movie_code = _optional_text(attribute.get("codigo_pelicula"))
                display_title = _optional_text(attribute.get("nombre_pelicula"))
                format_name = attribute.get("atributos_pelicula")
                rooms = _required_list(attribute, "salas", original_title)

                for room in rooms:
                    if not isinstance(room, dict):
                        raise CinelandScraperError(
                            f"Cineland devolvió una sala inválida para {original_title}."
                        )
                    room_name = _required_text(room, "nombre_sala", original_title)
                    room_code = _optional_text(room.get("codigo_sala"))
                    sessions = _required_list(
                        room, "funciones_y_tarifas", original_title
                    )

                    for session in sessions:
                        if not isinstance(session, dict):
                            raise CinelandScraperError(
                                f"Cineland devolvió una función inválida para "
                                f"{original_title}."
                            )
                        showtime = _parse_time(session.get("funcion"), original_title)
                        record: dict[str, object] = {
                            "titulo": original_title,
                            "cine": CINELAND_CINEMA_NAME,
                            "ciudad": CINELAND_CITY,
                            "fecha": show_date,
                            "hora": showtime,
                            "sala": room_name,
                            "formato": format_name,
                            "fuente_scraping": source_url,
                            "cine_id_origen": theater_code,
                            "funcion_id_origen": _function_id(
                                session,
                                movie_code=movie_code or original_title,
                                room_code=room_code or room_name,
                                show_date=show_date,
                                showtime=showtime,
                            ),
                        }
                        if display_title and display_title.casefold() != original_title.casefold():
                            record["titulo_alternativo"] = display_title
                        records.append(record)

    try:
        normalized = normalize_showtimes(records)
    except ValueError as exc:
        raise CinelandScraperError(
            f"No se pudo normalizar la cartelera de Cineland: {exc}"
        ) from exc
    return CarteleraData(funciones=normalized, proximos_estrenos=[])


def _required_list(record: Mapping[str, object], field: str, context: str) -> list[object]:
    value = record.get(field)
    if not isinstance(value, list):
        raise CinelandScraperError(
            f"Cineland omitió la lista '{field}' ({context})."
        )
    return value


def _required_text(record: Mapping[str, object], field: str, context: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CinelandScraperError(
            f"Cineland omitió el campo '{field}' ({context})."
        )
    return " ".join(value.split())


def _optional_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    return str(value)


def _parse_date(value: object, title: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            if "T" in value:
                return datetime.fromisoformat(value).date()
            return date.fromisoformat(value)
        except ValueError as exc:
            raise CinelandScraperError(
                f"Cineland devolvió una fecha inválida para {title}: {value!r}."
            ) from exc
    raise CinelandScraperError(
        f"Cineland omitió la fecha de una función de {title}."
    )


def _parse_time(value: object, title: str) -> time:
    if not isinstance(value, str):
        raise CinelandScraperError(
            f"Cineland omitió la hora de una función de {title}."
        )
    try:
        if "T" in value:
            return datetime.fromisoformat(value).time()
        return time.fromisoformat(value)
    except ValueError as exc:
        raise CinelandScraperError(
            f"Cineland devolvió una hora inválida para {title}: {value!r}."
        ) from exc


def _function_id(
    session: Mapping[str, object],
    *,
    movie_code: str,
    room_code: str,
    show_date: date,
    showtime: time,
) -> str:
    for field in ("codigo_funcion", "id_funcion", "funcion_id"):
        value = _optional_text(session.get(field))
        if value:
            return value
    time_precision = (
        "minutes"
        if showtime.second == 0 and showtime.microsecond == 0
        else "auto"
    )
    return ":".join(
        (
            movie_code,
            room_code,
            show_date.isoformat(),
            showtime.isoformat(timespec=time_precision),
        )
    )