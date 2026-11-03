import json
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

from cines.services import NormalizedShowtime, normalize_showtimes


CINEMARK_CARTELERA_URL = "https://www.cinemark.com.co/cartelera"
USER_AGENT = "CineRoll cartelera scraper/0.1 (development project)"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class CinemarkScraperError(RuntimeError):
    """Raised when Cinemark's cartelera cannot be fetched or parsed."""


def scrape_cartelera(
    city_slug: str = "bogota", timeout: float = 20.0
) -> list[NormalizedShowtime]:
    """Fetch one city's server-rendered Cinemark cartelera and extract showtimes."""
    city_slug = city_slug.strip().lower()
    if not re.fullmatch(r"[a-z0-9-]+", city_slug):
        raise ValueError("city_slug debe contener solo letras, números y guiones.")

    source_url = f"{CINEMARK_CARTELERA_URL}/{city_slug}"
    request = Request(
        source_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            charset = response.headers.get_content_charset() or "utf-8"
    except URLError as exc:
        raise CinemarkScraperError(
            f"No se pudo consultar la cartelera de Cinemark para {city_slug}: {exc}"
        ) from exc

    if len(body) > MAX_RESPONSE_BYTES:
        raise CinemarkScraperError("La respuesta de Cinemark excede el tamaño permitido.")

    try:
        html = body.decode(charset)
    except (LookupError, UnicodeDecodeError) as exc:
        raise CinemarkScraperError("Cinemark devolvió una codificación no válida.") from exc

    return parse_cartelera_page(html, city_slug, source_url)


def parse_cartelera_page(
    html: str,
    city_slug: str,
    source_url: str,
) -> list[NormalizedShowtime]:
    """Parse the __NEXT_DATA__ JSON embedded in Cinemark's cartelera HTML."""
    next_data = re.search(
        r'<script\b[^>]*\bid=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if next_data is None:
        raise CinemarkScraperError("No se encontró __NEXT_DATA__ en la página de Cinemark.")

    try:
        payload = json.loads(next_data.group(1))
    except json.JSONDecodeError as exc:
        raise CinemarkScraperError("El JSON de cartelera de Cinemark no es válido.") from exc

    try:
        page_props = payload["props"]["pageProps"]
    except (KeyError, TypeError) as exc:
        raise CinemarkScraperError("La respuesta de Cinemark no contiene pageProps.") from exc

    if not isinstance(page_props, dict) or page_props.get("city") != city_slug:
        raise CinemarkScraperError(
            f"Cinemark no devolvió datos para la ciudad solicitada: {city_slug}."
        )

    showtimes: list[dict[str, object]] = []
    for section in ("PremieresBillboard", "Presales"):
        movies = page_props.get(section, [])
        if not isinstance(movies, list):
            raise CinemarkScraperError(f"La sección {section} de Cinemark no es válida.")

        for movie in movies:
            if not isinstance(movie, dict):
                raise CinemarkScraperError(f"Se encontró una película inválida en {section}.")

            title = movie.get("TitleAlt") or movie.get("Title")
            cinema_name = movie.get("CinemaName")
            cinema_id = movie.get("CinemaId")
            sessions = movie.get("Sessions", [])
            if not isinstance(sessions, list):
                raise CinemarkScraperError(
                    f"Las funciones de {title or 'una película'} no tienen un formato válido."
                )
            if not sessions:
                continue
            if not title or not cinema_name or not cinema_id:
                raise CinemarkScraperError(
                    "Cinemark omitió el título o el cine de una película con funciones."
                )

            for session in sessions:
                showtimes.append(
                    _parse_session(
                        session,
                        title=title,
                        cinema_name=cinema_name,
                        cinema_id=str(cinema_id),
                        city_slug=city_slug,
                        source_url=source_url,
                    )
                )

    try:
        return normalize_showtimes(showtimes)
    except ValueError as exc:
        raise CinemarkScraperError(f"No se pudo normalizar la cartelera: {exc}") from exc


def _parse_session(
    session: object,
    *,
    title: str,
    cinema_name: str,
    cinema_id: str,
    city_slug: str,
    source_url: str,
) -> dict[str, object]:
    if not isinstance(session, dict):
        raise CinemarkScraperError(f"Se encontró una función inválida para {title}.")

    session_id = session.get("SessionId")
    raw_showtime = session.get("Showtime")
    session_cinema_id = session.get("CinemaId")
    if not session_id or not raw_showtime or str(session_cinema_id) != cinema_id:
        raise CinemarkScraperError(
            f"Cinemark devolvió datos incompletos o inconsistentes para {title}."
        )

    attributes = session.get("Attributes", [])
    if not isinstance(attributes, list):
        raise CinemarkScraperError(f"El formato de la función de {title} no es válido.")
    screen_name = session.get("ScreenName") or session.get("ScreenNumber") or ""
    return {
        "titulo": title.strip(),
        "cine": cinema_name.strip(),
        "ciudad": city_slug,
        "fecha_hora": raw_showtime,
        "sala": str(screen_name).strip(),
        "formato": attributes,
        "fuente_scraping": source_url,
        "cine_id_origen": cinema_id,
        "funcion_id_origen": str(session_id),
    }
