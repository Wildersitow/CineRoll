from io import StringIO
from datetime import date, timedelta
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone

from cines.models import Cine, Funcion, TituloPendiente
from cines.scrapers.cinemark import CinemarkScraperError
from cines.services import (
    CarteleraData,
    CarteleraScrapeResult,
    scrape_and_save_cartelera,
)
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
        self.cartelera = CarteleraData(
            funciones=[self.showtime],
            proximos_estrenos=[],
        )

    @patch("cines.scrapers.cinemark.scrape_cartelera_completa")
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
        self.assertEqual(function.cine.ciudad, "bogota")
        self.assertEqual(function.formato, "2D, Doblada")
        self.assertEqual(TituloPendiente.objects.count(), 0)
        scrape.assert_called_with(city_slug="bogota")

    @patch("cines.scrapers.cinemark.scrape_cartelera_completa")
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

    @patch("cines.scrapers.cinemark.scrape_cartelera_completa")
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

    @patch("cines.scrapers.cinemark.scrape_cartelera_completa")
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

    @patch("cines.scrapers.cinemark.scrape_cartelera_completa")
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

    @patch("cines.scrapers.cinemark.scrape_cartelera_completa")
    def test_scrape_deletes_expired_functions_and_updates_status_globally(self, scrape):
        scrape.return_value = CarteleraData(funciones=[], proximos_estrenos=[])
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

    @patch("cines.scrapers.cinemark.scrape_cartelera_completa")
    def test_upcoming_release_updates_matched_media_without_creating_movies(self, scrape):
        scrape.return_value = CarteleraData(
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

    @patch("cines.management.commands.scrape_cartelera.scrape_and_save_cartelera")
    def test_command_delegates_to_service_and_formats_result(self, scrape):
        scrape.return_value = CarteleraScrapeResult(
            cine="cinemark",
            ciudad="bogota",
            funciones_leidas=10,
            funciones_asociadas=8,
            funciones_creadas=3,
            funciones_actualizadas=5,
            titulos_pendientes=1,
            peliculas_en_cartelera=2,
            estrenos_leidos=4,
            estrenos_asociados=3,
            funciones_vencidas_eliminadas=6,
            peliculas_fuera_cartelera=1,
            estrenos_sin_coincidencia=("Película sin catálogo",),
            titulos_pendientes_mostrar=("#1 Película — Cine (bogota)",),
        )

        output = StringIO()
        call_command(
            "scrape_cartelera",
            cine="cinemark",
            ciudad="BOGOTA",
            stdout=output,
        )

        scrape.assert_called_once_with(cinema_provider="cinemark", city_slug="BOGOTA")
        self.assertIn("10 funciones leídas", output.getvalue())
        self.assertIn("Película sin catálogo", output.getvalue())
        self.assertIn("#1 Película — Cine (bogota)", output.getvalue())

    @patch("cines.management.commands.scrape_cartelera.scrape_and_save_cartelera")
    def test_command_converts_scraper_errors_to_command_error(self, scrape):
        scrape.side_effect = CinemarkScraperError("Fallo de lectura")

        with self.assertRaisesMessage(CommandError, "Fallo de lectura"):
            call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")

    @patch("cines.scrapers.cinemark.scrape_cartelera_completa")
    def test_created_cinema_uses_the_provider_website(self, scrape):
        scrape.return_value = self.cartelera
        Media.objects.create(
            titulo="Cómo entrenar a tu dragón",
            tipo=Media.Tipo.PELICULA,
        )

        call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")

        self.assertEqual(Cine.objects.get().sitio_web, "https://www.cinemark.com.co/")

    def test_unknown_provider_is_rejected(self):
        with self.assertRaisesMessage(ValueError, "desconocido"):
            scrape_and_save_cartelera("desconocido")

    @patch("cines.scrapers.cinepolis.scrape_cartelera_completa")
    def test_provider_city_key_and_canonical_city_are_used(self, scrape):
        scrape.return_value = self.cartelera
        media = Media.objects.create(
            titulo="Cómo entrenar a tu dragón",
            tipo=Media.Tipo.PELICULA,
        )

        scrape_and_save_cartelera("cinepolis", city_slug="valledupar")

        scrape.assert_called_once_with(city_key="valledupar-colombia")
        self.assertEqual(Funcion.objects.get().media, media)
        self.assertEqual(Cine.objects.get().ciudad, "valledupar")

    @patch("cines.scrapers.royal_films.scrape_cartelera_completa")
    def test_royal_films_provider_uses_its_configured_city_id(self, scrape):
        scrape.return_value = self.cartelera
        Media.objects.create(
            titulo="Cómo entrenar a tu dragón",
            tipo=Media.Tipo.PELICULA,
        )

        scrape_and_save_cartelera("royal_films", city_slug="valledupar")

        scrape.assert_called_once_with(city_id="1006")
        self.assertEqual(Cine.objects.get().ciudad, "valledupar")

    @patch("cines.scrapers.cinemark.scrape_cartelera_completa")
    def test_cinemark_is_not_configured_for_valledupar(self, scrape):
        with self.assertRaisesMessage(ValueError, "para la ciudad 'valledupar'"):
            scrape_and_save_cartelera("cinemark", city_slug="valledupar")

        scrape.assert_not_called()
