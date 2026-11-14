import json
from copy import deepcopy
from datetime import date, time
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from cines.scrapers.cinepolis import (
    CINEPOLIS_CARTELERA_URL,
    CinepolisScraperError,
    parse_cartelera_data,
    scrape_cartelera_completa,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "cinepolis_valledupar_sample.json"
)


class CinepolisScraperTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with FIXTURE_PATH.open(encoding="utf-8") as fixture:
            cls.payload = json.load(fixture)

    def test_parses_the_sample_response_into_the_common_contract(self):
        result = parse_cartelera_data(
            self.payload,
            "valledupar-colombia",
            CINEPOLIS_CARTELERA_URL,
        )

        self.assertEqual(len(result.funciones), 1)
        self.assertEqual(result.proximos_estrenos, [])
        self.assertEqual(
            result.funciones[0],
            {
                "titulo": "Cómo robar un banco",
                "cine": "Cinépolis Mega Mall",
                "ciudad": "Valledupar, Colombia",
                "fecha": date(2026, 11, 13),
                "hora": time(20, 10, tzinfo=ZoneInfo("America/Bogota")),
                "sala": "",
                "formato": "DOB, DOBLADA",
                "fuente_scraping": CINEPOLIS_CARTELERA_URL,
                "cine_id_origen": "577",
                "funcion_id_origen": "64989",
            },
        )

    def test_posts_once_with_requested_city_and_vip_disabled(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(self.payload).encode("utf-8")
        response.headers.get_content_charset.return_value = "utf-8"

        with patch(
            "cines.scrapers.cinepolis.urlopen",
            return_value=response,
        ) as open_url:
            result = scrape_cartelera_completa()

        open_url.assert_called_once()
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, CINEPOLIS_CARTELERA_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(
            json.loads(request.data),
            {"claveCiudad": "valledupar-colombia", "esVIP": False},
        )
        self.assertEqual(len(result.funciones), 1)

    def test_rejects_a_response_for_another_city(self):
        with self.assertRaisesRegex(CinepolisScraperError, "ciudad distinta"):
            parse_cartelera_data(
                self.payload,
                "bogota",
                CINEPOLIS_CARTELERA_URL,
            )

    def test_keeps_original_title_as_optional_alternative(self):
        payload = deepcopy(self.payload)
        movie = payload["d"]["Cinemas"][0]["Dates"][0]["Movies"][0]
        movie["OriginalTitle"] = "How to Rob a Bank"

        result = parse_cartelera_data(
            payload,
            "valledupar-colombia",
            CINEPOLIS_CARTELERA_URL,
        )

        self.assertEqual(
            result.funciones[0]["titulo_alternativo"],
            "How to Rob a Bank",
        )
