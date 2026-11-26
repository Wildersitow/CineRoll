"""Cliente mínimo de TMDB para completar las películas creadas por el scraper.

Solo se usa si hay una clave en ``TMDB_API_KEY`` (sirve la "API Key" v3 o el
"API Read Access Token" v4). Sin clave, o si TMDB falla, el scraper sigue
funcionando con los datos de la página del cine.
"""

from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher
import json
import logging
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from decouple import config
from django.conf import settings
from django.utils import timezone


TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p"
USER_AGENT = "CineRoll cartelera scraper/0.1 (development project)"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
REQUEST_TIMEOUT = 8.0
MAX_CAST = 8

logger = logging.getLogger(__name__)


class TmdbError(RuntimeError):
    pass


@dataclass(frozen=True)
class TmdbPelicula:
    tmdb_id: int
    titulo: str
    titulo_original: str = ""
    sinopsis: str = ""
    duracion: int | None = None
    fecha_estreno: date | None = None
    poster_url: str = ""
    backdrop_url: str = ""
    trailer_url: str = ""
    generos: tuple[str, ...] = ()
    directores: tuple[str, ...] = ()
    actores: tuple[str, ...] = field(default_factory=tuple)


def api_key() -> str:
    """Clave configurada. En las pruebas solo cuenta si se fija con override_settings."""
    key = getattr(settings, "TMDB_API_KEY", None)
    if key is None:
        key = "" if getattr(settings, "TESTING", False) else config("TMDB_API_KEY", default="")
    return (key or "").strip()


def configurado() -> bool:
    return bool(api_key())


def idioma() -> str:
    return getattr(settings, "TMDB_IDIOMA", None) or config("TMDB_IDIOMA", default="es-MX")


def buscar_pelicula(
    titulos: list[str],
    normalizar,
) -> TmdbPelicula | None:
    """Busca la película por cada título y devuelve la primera coincidencia segura.

    ``normalizar`` es la misma función que usa el scraper para comparar títulos,
    así una diferencia de mayúsculas, tildes o "DOB 2D" no impide la coincidencia.
    """
    if not configurado():
        return None
    for titulo in titulos:
        consulta = normalizar(titulo)
        if not consulta:
            continue
        try:
            resultados = _get("/search/movie", {"query": consulta, "include_adult": "false"})
        except TmdbError as exc:
            logger.warning("TMDB no respondió al buscar %r: %s", titulo, exc)
            return None
        candidato = _elegir(resultados.get("results"), consulta, normalizar)
        if candidato is None:
            continue
        try:
            return obtener_detalle(int(candidato["id"]))
        except (TmdbError, KeyError, TypeError, ValueError) as exc:
            logger.warning("TMDB no devolvió el detalle de %r: %s", titulo, exc)
            return None
    return None


def obtener_detalle(tmdb_id: int) -> TmdbPelicula:
    data = _get(f"/movie/{tmdb_id}", {"append_to_response": "videos,credits", "include_video_language": "es,en,null"})
    sinopsis = (data.get("overview") or "").strip()
    if not sinopsis:
        try:
            sinopsis = (_get(f"/movie/{tmdb_id}", {"language": "en-US"}).get("overview") or "").strip()
        except TmdbError:
            sinopsis = ""

    credits = data.get("credits") if isinstance(data.get("credits"), dict) else {}
    directores = tuple(
        persona["name"]
        for persona in credits.get("crew", [])
        if isinstance(persona, dict) and persona.get("job") == "Director" and persona.get("name")
    )
    actores = tuple(
        persona["name"]
        for persona in credits.get("cast", [])[:MAX_CAST]
        if isinstance(persona, dict) and persona.get("name")
    )
    generos = tuple(
        genero["name"]
        for genero in data.get("genres", [])
        if isinstance(genero, dict) and genero.get("name")
    )
    duracion = data.get("runtime")
    return TmdbPelicula(
        tmdb_id=int(data["id"]),
        titulo=(data.get("title") or data.get("original_title") or "").strip(),
        titulo_original=(data.get("original_title") or "").strip(),
        sinopsis=sinopsis,
        duracion=duracion if isinstance(duracion, int) and duracion > 0 else None,
        fecha_estreno=_fecha(data.get("release_date")),
        poster_url=_imagen(data.get("poster_path"), "w500"),
        backdrop_url=_imagen(data.get("backdrop_path"), "w1280"),
        trailer_url=_trailer(data.get("videos")),
        generos=generos,
        directores=directores,
        actores=actores,
    )


def _elegir(resultados, consulta: str, normalizar) -> dict | None:
    if not isinstance(resultados, list):
        return None
    hoy = timezone.localdate()
    exactos: list[dict] = []
    parecidos: list[dict] = []
    for resultado in resultados[:20]:
        if not isinstance(resultado, dict) or not resultado.get("id"):
            continue
        nombres = {
            normalizar(resultado.get("title") or ""),
            normalizar(resultado.get("original_title") or ""),
        } - {""}
        estreno = _fecha(resultado.get("release_date"))
        reciente = estreno is not None and abs((estreno - hoy).days) <= 550
        if consulta in nombres:
            exactos.append({**resultado, "_reciente": reciente})
        elif reciente and any(
            SequenceMatcher(None, consulta, nombre).ratio() >= 0.88 for nombre in nombres
        ):
            parecidos.append(resultado)

    # Para la cartelera conviene la versión más reciente (hay muchos remakes).
    for resultado in exactos:
        if resultado["_reciente"]:
            return resultado
    if exactos:
        return exactos[0]
    if len(parecidos) == 1:
        return parecidos[0]
    return None


def _get(path: str, params: dict[str, str]) -> dict:
    key = api_key()
    query = {"language": idioma(), "region": "CO", **params}
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"
    else:
        query["api_key"] = key
    request = Request(f"{TMDB_API_URL}{path}?{urlencode(query)}", headers=headers)
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except (URLError, TimeoutError, OSError) as exc:
        raise TmdbError(str(exc)) from exc
    if len(body) > MAX_RESPONSE_BYTES:
        raise TmdbError("La respuesta de TMDB excede el tamaño permitido.")
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TmdbError("TMDB devolvió una respuesta que no es JSON.") from exc
    if not isinstance(data, dict):
        raise TmdbError("TMDB devolvió una respuesta inesperada.")
    return data


def _fecha(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _imagen(path: object, size: str) -> str:
    if not isinstance(path, str) or not path.startswith("/"):
        return ""
    return f"{TMDB_IMAGE_URL}/{size}{path}"


def _trailer(videos: object) -> str:
    if not isinstance(videos, dict):
        return ""
    candidatos = [
        video
        for video in videos.get("results", [])
        if isinstance(video, dict)
        and video.get("site") == "YouTube"
        and video.get("type") == "Trailer"
        and video.get("key")
    ]
    if not candidatos:
        return ""
    candidatos.sort(key=lambda video: (not video.get("official", False),))
    return f"https://www.youtube.com/watch?v={candidatos[0]['key']}"
