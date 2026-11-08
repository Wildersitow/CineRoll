from datetime import date, timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from cines.models import Cine, Funcion, TituloPendiente
from cines.scrapers.cinemark import CinemarkCartelera
from media.models import Media


class ScrapeCarteleraCommandTests(TestCase):
    def setUp(self):
        future_showtime = timezone.localtime(timezone.now() + timedelta(days=1))
        self.showtime = {
            "titulo": "COMO ENTRENAR A TU DRAGON (DOB 2D)",
            "cine": "Cine de prueba",
            "ciudad": "bogota",
            "fecha": future_showtime.date(),
            "hora": future_showtime.timetz().replace(second=0, microsecond=0),
            "sala": "Sala 1",
            "formato": "2D, Doblada",
            "fuente_scraping": "https://www.cinemark.com.co/cartelera/bogota",
            "cine_id_origen": "2401",
            "funcion_id_origen": "session-1",
        }
        self.cartelera = CinemarkCartelera(
            funciones=[self.showtime],
            proximos_estrenos=[],
        )

    @patch("cines.management.commands.scrape_cartelera.scrape_cartelera_completa")
    def test_matches_and_saves_function_idempotently(self, scrape):
        scrape.return_value = self.cartelera
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

    @patch("cines.management.commands.scrape_cartelera.scrape_cartelera_completa")
    def test_unknown_title_is_recorded_for_manual_review(self, scrape):
        scrape.return_value = self.cartelera

        call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")
        call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")

        self.assertEqual(Funcion.objects.count(), 0)
        self.assertEqual(Cine.objects.count(), 0)
        self.assertEqual(TituloPendiente.objects.count(), 1)
        pending = TituloPendiente.objects.get()
        self.assertEqual(pending.titulo_original, self.showtime["titulo"])
        self.assertEqual(pending.estado, TituloPendiente.Estado.PENDIENTE)
        self.assertEqual(pending.apariciones_detectadas, 2)

    @patch("cines.management.commands.scrape_cartelera.scrape_cartelera_completa")
    def test_manually_resolved_title_saves_functions(self, scrape):
        scrape.return_value = self.cartelera
        media = Media.objects.create(
            titulo="Dragones: la película",
            tipo=Media.Tipo.PELICULA,
        )

        call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")
        self.assertEqual(Funcion.objects.count(), 0)

        TituloPendiente.objects.update(
            estado=TituloPendiente.Estado.RESUELTO, media_asociada=media
        )
        call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")

        self.assertEqual(Funcion.objects.count(), 1)
        self.assertEqual(Funcion.objects.get().media, media)

    @patch("cines.management.commands.scrape_cartelera.scrape_cartelera_completa")
    def test_matched_movie_is_marked_now_showing(self, scrape):
        scrape.return_value = self.cartelera
        media = Media.objects.create(
            titulo="Cómo entrenar a tu dragón",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.FUERA_CARTELERA,
            fecha_estreno=date(2025, 6, 13),
        )

        call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")

        media.refresh_from_db()
        self.assertEqual(media.estado, Media.Estado.EN_CARTELERA)

    @patch("cines.management.commands.scrape_cartelera.scrape_cartelera_completa")
    def test_future_premiere_stays_upcoming(self, scrape):
        scrape.return_value = self.cartelera
        media = Media.objects.create(
            titulo="Cómo entrenar a tu dragón",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.PROXIMO_ESTRENO,
            fecha_estreno=date(2999, 1, 1),
        )

        call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")

        media.refresh_from_db()
        self.assertEqual(media.estado, Media.Estado.PROXIMO_ESTRENO)

    @patch("cines.management.commands.scrape_cartelera.scrape_cartelera_completa")
    def test_scrape_deletes_expired_functions_and_updates_status_globally(self, scrape):
        scrape.return_value = CinemarkCartelera(funciones=[], proximos_estrenos=[])
        past_only = Media.objects.create(
            titulo="Solo funciones pasadas",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.EN_CARTELERA,
        )
        still_showing = Media.objects.create(
            titulo="Función futura en otro cine",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.EN_CARTELERA,
        )
        upcoming = Media.objects.create(
            titulo="Próximo estreno",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.PROXIMO_ESTRENO,
        )
        expired_cinema = Cine.objects.create(nombre="Cine A", ciudad="bogota")
        other_cinema = Cine.objects.create(nombre="Cine B", ciudad="cali")
        now = timezone.now()
        expired_fields = {
            "fecha_hora": now - timedelta(minutes=1),
            "sala": "Sala 1",
        }
        Funcion.objects.create(
            cine=expired_cinema,
            media=past_only,
            formato="2D",
            **expired_fields,
        )
        Funcion.objects.create(
            cine=expired_cinema,
            media=still_showing,
            formato="2D",
            **expired_fields,
        )
        future_function = Funcion.objects.create(
            cine=other_cinema,
            media=still_showing,
            fecha_hora=now + timedelta(days=1),
            sala="Sala 2",
            formato="2D",
        )

        call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")

        self.assertFalse(Funcion.objects.filter(fecha_hora__lt=timezone.now()).exists())
        self.assertTrue(Funcion.objects.filter(pk=future_function.pk).exists())
        past_only.refresh_from_db()
        still_showing.refresh_from_db()
        upcoming.refresh_from_db()
        self.assertEqual(past_only.estado, Media.Estado.FUERA_CARTELERA)
        self.assertEqual(still_showing.estado, Media.Estado.EN_CARTELERA)
        self.assertEqual(upcoming.estado, Media.Estado.PROXIMO_ESTRENO)

    @patch("cines.management.commands.scrape_cartelera.scrape_cartelera_completa")
    def test_upcoming_release_updates_matched_media_without_creating_movies(self, scrape):
        scrape.return_value = CinemarkCartelera(
            funciones=[],
            proximos_estrenos=[
                {
                    "titulo": "Cómo entrenar a tu dragón",
                    "fecha_estreno": date(2026, 12, 17),
                    "fuente_scraping": "https://www.cinemark.com.co/cartelera/bogota",
                },
                {
                    "titulo": "Título no catalogado",
                    "fecha_estreno": date(2026, 12, 24),
                    "fuente_scraping": "https://www.cinemark.com.co/cartelera/bogota",
                },
            ],
        )
        media = Media.objects.create(
            titulo="Cómo entrenar a tu dragón",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.FUERA_CARTELERA,
        )

        call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")

        media.refresh_from_db()
        self.assertEqual(media.fecha_estreno, date(2026, 12, 17))
        self.assertEqual(media.estado, Media.Estado.PROXIMO_ESTRENO)
        self.assertEqual(Media.objects.count(), 1)
        self.assertEqual(Funcion.objects.count(), 0)
