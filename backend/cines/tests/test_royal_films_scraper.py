from datetime import date, time
from unittest import TestCase
from unittest.mock import call, patch
from zoneinfo import ZoneInfo

from cines.services import CarteleraData
from cines.scrapers.royal_films import (
    ROYAL_FILMS_API_URL,
    REQUEST_PAUSE_SECONDS,
    RoyalFilmsScraperError,
    parse_cartelera_data,
    scrape_cartelera_completa,
)


def _billboard(
    movie_id="4209",
    title="CÓMO ROBAR UN BANCO",
    original_title="HOW TO ROB A BANK",
):
    return {
        "status": True,
        "data": [
            {
                "pelicula": {
                    "pelicula_id": int(movie_id),
                    "pelicula_titulo": title,
                    "pelicula_nombre_original": original_title,
                }
            }
        ],
    }


def _function_response(
    movie_id="4209",
    function_id=957376,
    showtime="1970-01-01T16:30:00.000Z",
):
    return {
        "status": True,
        "data": [
            {
                "funcion_id": function_id,
                "funcion_fecha": "2026-11-13",
                "funcion_pelicula_id": int(movie_id),
                "funcion_multicine_id": 2032,
                "funcion_sala_id": 3128,
                "funcion_hora_inicio": showtime,
                "formato": {"formato_nombre": "2D"},
                "multicine": {
                    "multicine_nombre": "Multicine Unicentro Valledupar"
                },
                "sala": {"sala_nombre": "SALA 2 STD"},
            }
        ],
    }


class RoyalFilmsScraperTests(TestCase):
    def test_parser_keeps_the_clock_time_without_timezone_conversion(self):
        result = parse_cartelera_data(
            _billboard(),
            {"4209": _function_response()},
            "1006",
        )

        self.assertIsInstance(result, CarteleraData)
        self.assertEqual(len(result.funciones), 1)
        self.assertEqual(result.proximos_estrenos, [])
        self.assertEqual(
            result.funciones[0],
            {
                "titulo": "CÓMO ROBAR UN BANCO",
                "titulo_alternativo": "HOW TO ROB A BANK",
                "cine": "Multicine Unicentro Valledupar",
                "ciudad": "valledupar",
                "fecha": date(2026, 11, 13),
                "hora": time(16, 30, tzinfo=ZoneInfo("America/Bogota")),
                "sala": "SALA 2 STD",
                "formato": "2D",
                "fuente_scraping": (
                    f"{ROYAL_FILMS_API_URL}/movies/functions/4209/city/1006"
                ),
                "cine_id_origen": "2032",
                "funcion_id_origen": "957376",
            },
        )

    def test_fetches_each_movie_functions_endpoint_with_a_pause(self):
        billboard = {
            "status": True,
            "data": [
                {"pelicula": {"pelicula_id": 4209, "pelicula_titulo": "Película 1"}},
                {"pelicula": {"pelicula_id": 4102, "pelicula_titulo": "Película 2"}},
            ],
        }
        empty_functions = {"status": True, "data": []}

        with (
            patch(
                "cines.scrapers.royal_films._fetch_json",
                side_effect=[billboard, empty_functions, empty_functions],
            ) as fetch,
            patch("cines.scrapers.royal_films.sleep") as pause,
        ):
            result = scrape_cartelera_completa(city_id="1006")

        self.assertEqual(result.funciones, [])
        self.assertEqual(
            [entry.args[0] for entry in fetch.call_args_list],
            [
                f"{ROYAL_FILMS_API_URL}/billboard/city/1006",
                f"{ROYAL_FILMS_API_URL}/movies/functions/4209/city/1006",
                f"{ROYAL_FILMS_API_URL}/movies/functions/4102/city/1006",
            ],
        )
        self.assertEqual(
            pause.call_args_list,
            [call(REQUEST_PAUSE_SECONDS), call(REQUEST_PAUSE_SECONDS)],
        )

    def test_rejects_function_for_another_movie(self):
        response = _function_response(movie_id="4102")

        with self.assertRaisesRegex(RoyalFilmsScraperError, "otra película"):
            parse_cartelera_data(
                _billboard(),
                {"4209": response},
                "1006",
            )
