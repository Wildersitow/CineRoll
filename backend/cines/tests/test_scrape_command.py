import json
from io import StringIO
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

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


CINEPOLIS_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "cinepolis_valledupar_sample.json"
)


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
    def test_matching_uses_alternate_title_from_normalized_scraper_data(self, scrape):
        record = {
            **self.showtime,
            "titulo": "Título localizado sin coincidencia",
            "titulo_alternativo": "Original Movie",
        }
        scrape.return_value = CarteleraData(
            funciones=[record],
            proximos_estrenos=[],
        )
        media = Media.objects.create(
            titulo="Título del catálogo",
            titulo_original="Original Movie",
            tipo=Media.Tipo.PELICULA,
        )

        call_command("scrape_cartelera", cine="cinemark", ciudad="bogota")

        self.assertEqual(Funcion.objects.get().media, media)
        self.assertEqual(TituloPendiente.objects.count(), 0)

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
    def test_scrape_removes_obsolete_and_changed_room_format_functions(self, scrape):
        scrape.return_value = self.cartelera
        media = Media.objects.create(
            titulo="Cómo entrenar a tu dragón",
            tipo=Media.Tipo.PELICULA,
        )
        cinema = Cine.objects.create(
            nombre=self.showtime["cine"],
            ciudad="bogota",
            sitio_web="https://www.cinemark.com.co/",
        )
        previous_time = datetime.combine(
            self.showtime["fecha"],
            self.showtime["hora"],
        )
        outdated_room = Funcion.objects.create(
            media=media,
            cine=cinema,
            fecha_hora=previous_time,
            sala="Sala antigua",
            formato="Formato antiguo",
        )
        removed_media = Media.objects.create(
            titulo="Película que ya no está",
            tipo=Media.Tipo.PELICULA,
        )
        removed_function = Funcion.objects.create(
            media=removed_media,
            cine=cinema,
            fecha_hora=previous_time + timedelta(hours=2),
            sala="Sala 2",
            formato="2D",
        )
        other_city_cinema = Cine.objects.create(
            nombre="Cinemark en Cali",
            ciudad="cali",
            sitio_web="https://www.cinemark.com.co/",
        )
        other_city_function = Funcion.objects.create(
            media=removed_media,
            cine=other_city_cinema,
            fecha_hora=previous_time + timedelta(hours=3),
            sala="Sala 3",
            formato="2D",
        )
        other_provider_cinema = Cine.objects.create(
            nombre="Cinépolis en Bogotá",
            ciudad="bogota",
            sitio_web="https://cinepolis.com.co/",
        )
        other_provider_function = Funcion.objects.create(
            media=removed_media,
            cine=other_provider_cinema,
            fecha_hora=previous_time + timedelta(hours=4),
            sala="Sala 4",
            formato="2D",
        )

        result = scrape_and_save_cartelera("cinemark", city_slug="bogota")

        self.assertEqual(result.funciones_obsoletas_eliminadas, 2)
        self.assertFalse(Funcion.objects.filter(pk=outdated_room.pk).exists())
        self.assertFalse(Funcion.objects.filter(pk=removed_function.pk).exists())
        self.assertTrue(Funcion.objects.filter(pk=other_city_function.pk).exists())
        self.assertTrue(Funcion.objects.filter(pk=other_provider_function.pk).exists())
        self.assertEqual(Funcion.objects.filter(cine=cinema).count(), 1)
        synced = Funcion.objects.get(cine=cinema)
        self.assertEqual(synced.media, media)
        self.assertEqual(synced.sala, self.showtime["sala"])
        self.assertEqual(synced.formato, self.showtime["formato"])

    @patch("cines.scrapers.cinemark.scrape_cartelera_completa")
    def test_empty_response_warns_and_preserves_future_functions(self, scrape):
        scrape.return_value = CarteleraData(funciones=[], proximos_estrenos=[])
        media = Media.objects.create(
            titulo="Película de la cartelera",
            tipo=Media.Tipo.PELICULA,
        )
        cinema = Cine.objects.create(
            nombre="Cinemark existente",
            ciudad="bogota",
            sitio_web="https://www.cinemark.com.co/",
        )
        existing = Funcion.objects.create(
            media=media,
            cine=cinema,
            fecha_hora=timezone.now() + timedelta(days=1),
            sala="Sala 1",
            formato="2D",
        )

        with self.assertLogs("cines.services", level="WARNING") as logs:
            result = scrape_and_save_cartelera("cinemark", city_slug="bogota")

        self.assertTrue(Funcion.objects.filter(pk=existing.pk).exists())
        self.assertEqual(result.funciones_obsoletas_eliminadas, 0)
        self.assertIn("respuesta llegó vacía", logs.output[0])

    @patch("cines.scrapers.cinemark.scrape_cartelera_completa")
    def test_response_below_half_previous_functions_skips_synchronization(self, scrape):
        scrape.return_value = self.cartelera
        media = Media.objects.create(
            titulo="Cómo entrenar a tu dragón",
            tipo=Media.Tipo.PELICULA,
        )
        cinema = Cine.objects.create(
            nombre=self.showtime["cine"],
            ciudad="bogota",
            sitio_web="https://www.cinemark.com.co/",
        )
        current_time = datetime.combine(
            self.showtime["fecha"],
            self.showtime["hora"],
        )
        existing_functions = [
            Funcion.objects.create(
                media=media,
                cine=cinema,
                fecha_hora=current_time,
                sala=self.showtime["sala"],
                formato=self.showtime["formato"],
            )
        ]
        for index in range(2):
            other_media = Media.objects.create(
                titulo=f"Película anterior {index}",
                tipo=Media.Tipo.PELICULA,
            )
            existing_functions.append(
                Funcion.objects.create(
                    media=other_media,
                    cine=cinema,
                    fecha_hora=current_time + timedelta(hours=index + 1),
                    sala=f"Sala {index + 2}",
                    formato="2D",
                )
            )

        with self.assertLogs("cines.services", level="WARNING") as logs:
            result = scrape_and_save_cartelera("cinemark", city_slug="bogota")

        self.assertEqual(result.funciones_obsoletas_eliminadas, 0)
        self.assertEqual(Funcion.objects.filter(cine=cinema).count(), 3)
        self.assertIn("menos del 50%", logs.output[0])

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
        self.assertIn("0 funciones futuras obsoletas eliminadas", output.getvalue())
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

    @patch("cines.services.timezone.now")
    @patch("cines.scrapers.cinepolis.urlopen")
    def test_one_command_scrapes_cinepolis_example_into_valledupar(
        self,
        open_url,
        now,
    ):
        with CINEPOLIS_FIXTURE_PATH.open(encoding="utf-8") as fixture:
            payload = json.load(fixture)
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(payload).encode("utf-8")
        response.headers.get_content_charset.return_value = "utf-8"
        open_url.return_value = response
        now.return_value = datetime(2026, 11, 13, 12, 0, tzinfo=ZoneInfo("America/Bogota"))
        media = Media.objects.create(
            titulo="Cómo robar un banco",
            tipo=Media.Tipo.PELICULA,
        )

        output = StringIO()
        call_command(
            "scrape_cartelera",
            cine="cinepolis",
            ciudad="valledupar",
            stdout=output,
        )

        open_url.assert_called_once()
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(
            json.loads(request.data),
            {"claveCiudad": "valledupar-colombia", "esVIP": False},
        )
        function = Funcion.objects.get()
        self.assertEqual(function.media, media)
        self.assertEqual(function.cine.ciudad, "valledupar")
        local_time = timezone.localtime(function.fecha_hora)
        self.assertEqual(local_time.date(), date(2026, 11, 13))
        self.assertEqual(local_time.time().hour, 20)
        self.assertIn("1 funciones leídas, 1 asociadas", output.getvalue())

    @patch("cines.services.timezone.now")
    @patch("cines.scrapers.royal_films.sleep")
    @patch("cines.scrapers.royal_films._fetch_json")
    def test_one_command_scrapes_royal_films_example_into_valledupar(
        self,
        fetch_json,
        sleep,
        now,
    ):
        billboard = {
            "status": True,
            "data": [
                {
                    "pelicula": {
                        "pelicula_id": 4209,
                        "pelicula_titulo": "CÓMO ROBAR UN BANCO",
                        "pelicula_nombre_original": "HOW TO ROB A BANK",
                    }
                }
            ],
        }
        functions = {
            "status": True,
            "data": [
                {
                    "funcion_id": 957376,
                    "funcion_fecha": "2026-11-13",
                    "funcion_pelicula_id": 4209,
                    "funcion_multicine_id": 2032,
                    "funcion_hora_inicio": "1970-01-01T16:30:00.000Z",
                    "formato": {"formato_nombre": "2D"},
                    "multicine": {
                        "multicine_nombre": "Multicine Unicentro Valledupar"
                    },
                    "sala": {"sala_nombre": "SALA 2 STD"},
                }
            ],
        }
        fetch_json.side_effect = [billboard, functions]
        now.return_value = datetime(2026, 11, 13, 12, 0, tzinfo=ZoneInfo("America/Bogota"))
        media = Media.objects.create(
            titulo="Cómo robar un banco",
            tipo=Media.Tipo.PELICULA,
        )

        output = StringIO()
        call_command(
            "scrape_cartelera",
            cine="royal_films",
            ciudad="valledupar",
            stdout=output,
        )

        self.assertEqual(
            [call.args[0] for call in fetch_json.call_args_list],
            [
                "https://cinemasroyalfilms.com/api/billboard/city/1006",
                "https://cinemasroyalfilms.com/api/movies/functions/4209/city/1006",
            ],
        )
        sleep.assert_called_once()
        function = Funcion.objects.get()
        self.assertEqual(function.media, media)
        self.assertEqual(function.cine.ciudad, "valledupar")
        local_time = timezone.localtime(function.fecha_hora)
        self.assertEqual(local_time.date(), date(2026, 11, 13))
        self.assertEqual(local_time.time().hour, 16)
        self.assertIn("1 funciones leídas, 1 asociadas", output.getvalue())

    @patch("cines.scrapers.cinemark.scrape_cartelera_completa")
    def test_cinemark_is_not_configured_for_valledupar(self, scrape):
        with self.assertRaisesMessage(ValueError, "para la ciudad 'valledupar'"):
            scrape_and_save_cartelera("cinemark", city_slug="valledupar")

        scrape.assert_not_called()
