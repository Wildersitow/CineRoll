from datetime import date, time
from unittest import TestCase
from zoneinfo import ZoneInfo

from cines.services import normalize_showtime, normalize_showtimes


class ShowtimeNormalizationTests(TestCase):
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
