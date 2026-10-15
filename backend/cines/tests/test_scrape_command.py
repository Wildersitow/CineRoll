from datetime import date, time
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.test import TestCase

from cines.models import Cine, Funcion, TituloPendiente
from media.models import Media


class ScrapeCarteleraCommandTests(TestCase):
    def setUp(self):
        self.showtime = {
            "titulo": "COMO ENTRENAR A TU DRAGON (DOB 2D)",
            "cine": "Cine de prueba",
            "ciudad": "bogota",
            "fecha": date(2026, 10, 15),
            "hora": time(19, 30, tzinfo=ZoneInfo("America/Bogota")),
            "sala": "Sala 1",
            "formato": "2D, Doblada",
            "fuente_scraping": "https://www.cinemark.com.co/cartelera/bogota",
            "cine_id_origen": "2401",
            "funcion_id_origen": "session-1",
        }

    @patch("cines.management.commands.scrape_cartelera.scrape_cartelera")
    def test_matches_and_saves_function_idempotently(self, scrape):
        scrape.return_value = [self.showtime]
        media = Media.objects.create(
            titulo="Cómo entrenar a tu dragón",
            tipo=Media.Tipo.PELICULA,
        )

        call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")
        call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")

        self.assertEqual(Cine.objects.count(), 1)
        self.assertEqual(Funcion.objects.count(), 1)
        function = Funcion.objects.get()
        self.assertEqual(function.media, media)
        self.assertEqual(function.cine.nombre, "Cine de prueba")
        self.assertEqual(function.formato, "2D, Doblada")
        self.assertEqual(TituloPendiente.objects.count(), 0)

    @patch("cines.management.commands.scrape_cartelera.scrape_cartelera")
    def test_unknown_title_is_recorded_for_manual_review(self, scrape):
        scrape.return_value = [self.showtime]

        call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")
        call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")

        self.assertEqual(Funcion.objects.count(), 0)
        self.assertEqual(Cine.objects.count(), 0)
        self.assertEqual(TituloPendiente.objects.count(), 1)
        pending = TituloPendiente.objects.get()
        self.assertEqual(pending.titulo_original, self.showtime["titulo"])
        self.assertEqual(pending.estado, TituloPendiente.Estado.PENDIENTE)
        self.assertEqual(pending.apariciones_detectadas, 2)
