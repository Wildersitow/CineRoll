from datetime import date, time
from unittest import TestCase
from zoneinfo import ZoneInfo

from cines.services import (
    CANONICAL_CITY,
    CITY_PROVIDER_KEYS,
    CINEMA_NAME_MAX_LENGTH,
    FORMAT_MAX_LENGTH,
    ROOM_MAX_LENGTH,
    TITLE_MAX_LENGTH,
    normalize_showtime,
    normalize_showtimes,
)


class ShowtimeNormalizationTests(TestCase):
    def test_valledupar_uses_the_city_key_for_each_provider(self):
        self.assertEqual(CANONICAL_CITY, "valledupar")
        self.assertEqual(
            CITY_PROVIDER_KEYS[CANONICAL_CITY],
            {
                "cinepolis": "valledupar-colombia",
                "royal_films": "1006",
                "cineland": "0051",
            },
        )

    def test_normalizes_shared_fields_and_timezone(self):
        result = normalize_showtime(
            {
                "titulo": "  Película   de prueba ",
                "cine": " Cine de prueba ",
                "ciudad": " Bogotá ",
                "fecha_hora": "2026-10-15T23:30:00+00:00",
                "sala": " Sala   4 ",
                "formato": [
                    {"Description": "2D"},
                    {"Description": " Doblada "},
                    {"Description": "2d"},
                ],
            }
        )

        self.assertEqual(result["titulo"], "Película de prueba")
        self.assertEqual(result["cine"], "Cine de prueba")
        self.assertEqual(result["ciudad"], "Bogotá")
        self.assertEqual(result["fecha"], date(2026, 10, 15))
        self.assertEqual(
            result["hora"],
            time(18, 30, tzinfo=ZoneInfo("America/Bogota")),
        )
        self.assertEqual(result["sala"], "Sala 4")
        self.assertEqual(result["formato"], "2D, Doblada")
        self.assertNotIn("titulo_alternativo", result)

    def test_normalizes_optional_alternate_title(self):
        result = normalize_showtime(
            {
                "titulo": "Título localizado",
                "titulo_alternativo": "  Original   Title ",
                "cine": "Cine",
                "ciudad": "bogota",
                "fecha": "2026-10-15",
                "hora": "19:30:00",
            }
        )

        self.assertEqual(result["titulo_alternativo"], "Original Title")

    def test_accepts_separate_iso_date_and_time_fields(self):
        result = normalize_showtime(
            {
                "titulo": "Película",
                "cine": "Cine",
                "ciudad": "bogota",
                "fecha": "2026-10-15",
                "hora": "19:30:00",
                "formato": "2D, Doblada",
            }
        )

        self.assertEqual(result["fecha"], date(2026, 10, 15))
        self.assertEqual(
            result["hora"],
            time(19, 30, tzinfo=ZoneInfo("America/Bogota")),
        )

    def test_deduplicates_showtimes_independent_of_source_ids(self):
        base = {
            "titulo": "Película",
            "cine": "Cine",
            "ciudad": "bogota",
            "fecha_hora": "2026-10-15T19:30:00",
            "sala": "Sala 1",
            "formato": "2D",
        }
        duplicate = {
            **base,
            "titulo": "  PELÍCULA ",
            "cine_id_origen": "other-cinema-id",
            "funcion_id_origen": "other-session-id",
        }

        results = normalize_showtimes([base, duplicate])

        self.assertEqual(len(results), 1)

    def test_requires_title_cinema_city_and_time(self):
        with self.assertRaisesRegex(ValueError, "titulo"):
            normalize_showtime(
                {
                    "cine": "Cine",
                    "ciudad": "bogota",
                    "fecha_hora": "2026-10-15T19:30:00",
                }
            )

        with self.assertRaisesRegex(ValueError, "fecha_hora"):
            normalize_showtime(
                {"titulo": "Película", "cine": "Cine", "ciudad": "bogota"}
            )

    def test_trunca_campos_que_exceden_el_limite_de_la_base_de_datos(self):
        result = normalize_showtime(
            {
                "titulo": "T" * (TITLE_MAX_LENGTH + 50),
                "cine": "C" * (CINEMA_NAME_MAX_LENGTH + 50),
                "ciudad": "valledupar",
                "fecha": "2026-11-13",
                "hora": "20:10:00",
                "sala": "S" * (ROOM_MAX_LENGTH + 50),
                "formato": [f"Atributo largo {index}" for index in range(40)],
            }
        )

        self.assertLessEqual(len(result["titulo"]), TITLE_MAX_LENGTH)
        self.assertLessEqual(len(result["cine"]), CINEMA_NAME_MAX_LENGTH)
        self.assertLessEqual(len(result["sala"]), ROOM_MAX_LENGTH)
        self.assertLessEqual(len(result["formato"]), FORMAT_MAX_LENGTH)
        self.assertTrue(result["formato"].startswith("Atributo largo 0, Atributo largo 1"))
        self.assertFalse(result["formato"].endswith(" "))

    def test_no_modifica_valores_que_caben(self):
        result = normalize_showtime(
            {
                "titulo": "Película",
                "cine": "Cine",
                "ciudad": "valledupar",
                "fecha": "2026-11-13",
                "hora": "20:10:00",
                "sala": "Sala 1",
                "formato": ["2D", "Doblada"],
            }
        )

        self.assertEqual(result["sala"], "Sala 1")
        self.assertEqual(result["formato"], "2D, Doblada")
