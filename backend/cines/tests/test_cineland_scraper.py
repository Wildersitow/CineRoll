import json
from datetime import date, time, timedelta
from io import BytesIO
from unittest import TestCase
from unittest.mock import call, patch
from zoneinfo import ZoneInfo

from cines.services import CITY_PROVIDER_KEYS, SCRAPERS, CarteleraData
from cines.scrapers.cineland import (
    CINELAND_CARTELERA_URL,
    REQUEST_PAUSE_SECONDS,
    CinelandScraperError,
    parse_cartelera_data,
    parse_cartelera_response,
    scrape_cartelera_completa,
)


def _showtime_payload(show_date="2026-11-08", function="13:30"):
    return {
        "count": 1,
        "transaction_status": {"status": True, "code": 200},
        "data": [
            {
                "nombre_pelicula_original": "AVENGERS DOOMSDAY",
                "url_imagen_pelicula": "https://cineland.website/poster.jpg",
                "genero": "Acción",
                "fechas": [
                    {
                        "date": show_date,
                        "preventa": False,
                        "atributos": [
                            {
                                "codigo_pelicula": "260920",
                                "nombre_pelicula": "Avengers: Doomsday (DOB)",
                                "atributos_pelicula": "3D DOBLADA",
                                "salas": [
                                    {
                                        "codigo_sala": "2",
                                        "nombre_sala": "Sala 2",
                                        "funciones_y_tarifas": [
                                            {
                                                "funcion": function,
                                                "tarifa": "18000",
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }


class CinelandScraperTests(TestCase):
    def test_is_registered_for_valledupar(self):
        self.assertEqual(CITY_PROVIDER_KEYS["valledupar"]["cineland"], "0051")
        self.assertIn("cineland", SCRAPERS)
        self.assertEqual(
            SCRAPERS["cineland"].website,
            "https://home.cineland.co/",
        )

    def test_parser_flattens_movie_dates_formats_rooms_and_functions(self):
        result = parse_cartelera_data(_showtime_payload())

        self.assertIsInstance(result, CarteleraData)
        self.assertEqual(result.proximos_estrenos, [])
        self.assertEqual(
            result.funciones,
            [
                {
                    "titulo": "AVENGERS DOOMSDAY",
                    "titulo_alternativo": "Avengers: Doomsday (DOB)",
                    "cine": "CineLand C.C. Mayales",
                    "ciudad": "valledupar",
                    "fecha": date(2026, 11, 8),
                    "hora": time(13, 30, tzinfo=ZoneInfo("America/Bogota")),
                    "sala": "Sala 2",
                    "formato": "3D DOBLADA",
                    "fuente_scraping": CINELAND_CARTELERA_URL,
                    "cine_id_origen": "0051",
                    "funcion_id_origen": "260920:2:2026-11-08:13:30",
                }
            ],
        )

    def test_parser_handles_empty_data(self):
        result = parse_cartelera_data(
            {"data": [], "transaction_status": {"status": True, "code": 200}}
        )

        self.assertEqual(result, CarteleraData(funciones=[], proximos_estrenos=[]))

    def test_parser_rejects_failed_transaction(self):
        payload = {
            "data": [],
            "transaction_status": {
                "status": False,
                "code": 400,
                "msg": "Missing Key",
            },
        }

        with self.assertRaisesRegex(CinelandScraperError, "Missing Key"):
            parse_cartelera_data(payload)

    def test_parser_decodes_json_even_when_server_content_type_is_html(self):
        body = json.dumps(_showtime_payload()).encode("utf-8")

        result = parse_cartelera_response(body)

        self.assertEqual(len(result.funciones), 1)

    @patch("cines.scrapers.cineland.sleep")
    @patch("cines.scrapers.cineland.urlopen")
    def test_fetches_one_post_per_day_with_pause_between_days(self, urlopen, sleep):
        login_payload = {"data": {"token": "test-token"}}
        usrlock_payload = {"data": {"usrlock": "test-usrlock"}}
        cartelera_payload = {
            "data": [],
            "transaction_status": {"status": True, "code": 200},
        }
        urlopen.side_effect = [
            BytesIO(json.dumps(login_payload).encode("utf-8")),
            BytesIO(json.dumps(usrlock_payload).encode("utf-8")),
            *[
                BytesIO(json.dumps(cartelera_payload).encode("utf-8"))
                for _ in range(7)
            ],
        ]

        result = scrape_cartelera_completa(
            start_date=date(2026, 11, 8),
            days=7,
            api_key="test-api-key",
            client_email="cineland@example.com",
            client_password="test-password",
        )

        self.assertEqual(result, CarteleraData(funciones=[], proximos_estrenos=[]))
        self.assertEqual(urlopen.call_count, 9)
        self.assertEqual(
            sleep.call_args_list,
            [call(REQUEST_PAUSE_SECONDS)] * 6,
        )

        requests = [entry.args[0] for entry in urlopen.call_args_list]
        request_bodies = [json.loads(request.data) for request in requests[2:]]
        expected_dates = [
            (date(2026, 11, 8) + timedelta(days=index)).isoformat()
            for index in range(7)
        ]
        self.assertEqual(
            [body["fechacon1"] for body in request_bodies], expected_dates
        )
        self.assertEqual(
            [body["fechacon2"] for body in request_bodies], expected_dates
        )
        self.assertTrue(
            all(body["codteatro"] == "0051" for body in request_bodies)
        )

        login_request, usrlock_request = requests[:2]
        self.assertEqual(
            json.loads(login_request.data),
            {"email": "cineland@example.com", "pwd": "test-password"},
        )
        self.assertEqual(login_request.headers["Route"], "login")
        self.assertEqual(
            usrlock_request.headers["Route"], "get_consecutivo_temporal"
        )
        self.assertEqual(usrlock_request.headers["Authorization"], "test-token")

        first_request = requests[2]
        self.assertEqual(first_request.full_url, CINELAND_CARTELERA_URL)
        self.assertEqual(first_request.get_method(), "POST")
        self.assertEqual(first_request.headers["Route"], "get_cartelera_agrupada")
        self.assertEqual(first_request.headers["Authorization"], "test-token")
        self.assertEqual(
            json.loads(first_request.data),
            {
                "usrlock": "test-usrlock",
                "fechacon1": "2026-11-08",
                "fechacon2": "2026-11-08",
                "codteatro": "0051",
            },
        )

    @patch("cines.scrapers.cineland.config", side_effect=lambda _name, default="": default)
    def test_requires_credentials_from_environment(self, _config):
        with self.assertRaisesRegex(
            CinelandScraperError,
            "CINELAND_API_KEY, CINELAND_EMAIL y CINELAND_PASSWORD",
        ):
            scrape_cartelera_completa(days=1, start_date=date(2026, 11, 8))

    def test_rejects_ranges_longer_than_seven_days(self):
        with self.assertRaisesRegex(ValueError, "entre 1 y 7"):
            scrape_cartelera_completa(days=8)