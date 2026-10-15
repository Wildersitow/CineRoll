import json
from datetime import date, time
from unittest import TestCase
from zoneinfo import ZoneInfo

from cines.scrapers.cinemark import (
    CinemarkScraperError,
    parse_cartelera_page,
)


class CinemarkScraperTests(TestCase):
    def test_parses_city_movies_and_showtime_attributes(self):
        payload = {
            "props": {
                "pageProps": {
                    "city": "bogota",
                    "PremieresBillboard": [
                        {
                            "Title": "PELICULA (DOB 2D)",
                            "TitleAlt": "Película",
                            "CinemaId": "2401",
                            "CinemaName": "Cinemark Gran Plaza",
                            "Sessions": [
                                {
                                    "CinemaId": "2401",
                                    "SessionId": "session-1",
                                    "Showtime": "2026-10-15T19:30:00",
                                    "ScreenName": "Sala 3",
                                    "Attributes": [
                                        {"Description": "2D"},
                                        {"Description": "Doblada"},
                                    ],
                                }
                            ],
                        }
                    ],
                    "Presales": [],
                    "UpcomingReleases": [
                        {"Title": "No tiene funciones", "Sessions": []}
                    ],
                }
            }
        }
        source_url = "https://www.cinemark.com.co/cartelera/bogota"
        html = (
            '<html><script id="__NEXT_DATA__" type="application/json">'
            f"{json.dumps(payload)}</script></html>"
        )

        results = parse_cartelera_page(html, "bogota", source_url)

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0],
            {
                "titulo": "Película",
                "cine": "Cinemark Gran Plaza",
                "ciudad": "bogota",
                "fecha": date(2026, 10, 15),
                "hora": time(19, 30, tzinfo=ZoneInfo("America/Bogota")),
                "sala": "Sala 3",
                "formato": "2D, Doblada",
                "fuente_scraping": source_url,
                "cine_id_origen": "2401",
                "funcion_id_origen": "session-1",
            },
        )

    def test_rejects_page_for_a_different_city(self):
        html = (
            '<script id="__NEXT_DATA__">'
            '{"props":{"pageProps":{"city":"armenia"}}}</script>'
        )

        with self.assertRaisesRegex(CinemarkScraperError, "ciudad solicitada"):
            parse_cartelera_page(
                html,
                "bogota",
                "https://www.cinemark.com.co/cartelera/bogota",
            )

    def test_rejects_html_without_next_data(self):
        with self.assertRaisesRegex(CinemarkScraperError, "__NEXT_DATA__"):
            parse_cartelera_page(
                "<html>sin datos</html>",
                "bogota",
                "https://www.cinemark.com.co/cartelera/bogota",
            )
