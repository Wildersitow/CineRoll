import json
from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from cines.models import Cine, Funcion
from cines.services import CarteleraScrapeResult, ScraperError
from backend.usuarios.tasks import limpiar_cartelera_vencida, scrape_cartelera_task
from media.models import Media


def _resultado(**cambios):
    datos = dict(
        cine="cinepolis",
        ciudad="valledupar",
        funciones_leidas=10,
        funciones_asociadas=8,
        funciones_creadas=3,
        funciones_actualizadas=5,
        titulos_pendientes=2,
        peliculas_en_cartelera=1,
        estrenos_leidos=0,
        estrenos_asociados=0,
        funciones_vencidas_eliminadas=4,
        peliculas_fuera_cartelera=0,
        estrenos_sin_coincidencia=(),
        titulos_pendientes_mostrar=("#1 Película — Cine (valledupar)",),
    )
    datos.update(cambios)
    return CarteleraScrapeResult(**datos)


def _candado_falso(libre):
    @contextmanager
    def candado(cine, ciudad, timeout):
        yield libre

    return candado


class ScrapeCarteleraTaskTests(TestCase):
    def setUp(self):
        # Las pruebas no usan Redis: el candado siempre está libre.
        parche = patch("cines.tasks.candado_scraping", _candado_falso(True))
        parche.start()
        self.addCleanup(parche.stop)

    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_la_tarea_solo_delega_en_el_servicio(self, servicio):
        servicio.return_value = _resultado()

        resultado = scrape_cartelera_task.apply(args=("cinepolis", "valledupar")).get()

        servicio.assert_called_once_with(
            cinema_provider="cinepolis", city_slug="valledupar"
        )
        self.assertEqual(resultado["cine"], "cinepolis")
        self.assertEqual(resultado["funciones_leidas"], 10)
        self.assertEqual(resultado["funciones_creadas"], 3)

    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_el_resultado_se_puede_serializar_en_json(self, servicio):
        servicio.return_value = _resultado()

        resultado = scrape_cartelera_task.apply(args=("cinepolis", "valledupar")).get()

        json.dumps(resultado)  # Celery lo exige para guardarlo en Redis

    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_scraper_error_se_reintenta_y_luego_falla(self, servicio):
        servicio.side_effect = ScraperError("el sitio no responde")

        resultado = scrape_cartelera_task.apply(args=("cinepolis", "valledupar"))

        self.assertTrue(resultado.failed())
        self.assertEqual(servicio.call_count, 4)  # 1 intento + 3 reintentos

    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_un_reintento_exitoso_devuelve_el_resultado(self, servicio):
        servicio.side_effect = [ScraperError("falla temporal"), _resultado()]

        resultado = scrape_cartelera_task.apply(args=("cinepolis", "valledupar"))

        self.assertTrue(resultado.successful())
        self.assertEqual(resultado.get()["funciones_leidas"], 10)
        self.assertEqual(servicio.call_count, 2)

    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_los_errores_de_configuracion_no_se_reintentan(self, servicio):
        servicio.side_effect = ValueError("ciudad sin configuración")

        resultado = scrape_cartelera_task.apply(args=("cinepolis", "bogota"))

        self.assertTrue(resultado.failed())
        self.assertEqual(servicio.call_count, 1)

    def test_tiene_limites_de_tiempo_y_maximo_de_reintentos(self):
        self.assertEqual(scrape_cartelera_task.max_retries, 3)
        self.assertLess(
            scrape_cartelera_task.soft_time_limit, scrape_cartelera_task.time_limit
        )


class CandadoDeScrapingTaskTests(TestCase):
    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_si_ya_hay_una_ejecucion_en_curso_se_omite(self, servicio):
        with patch("cines.tasks.candado_scraping", _candado_falso(False)):
            resultado = scrape_cartelera_task.apply(
                args=("cinepolis", "valledupar")
            ).get()

        servicio.assert_not_called()
        self.assertEqual(
            resultado,
            {
                "cine": "cinepolis",
                "ciudad": "valledupar",
                "omitido": True,
                "motivo": "ya_en_ejecucion",
            },
        )


class LimpiarCarteleraVencidaTaskTests(TestCase):
    def test_borra_funciones_vencidas_y_saca_de_cartelera(self):
        media = Media.objects.create(
            titulo="Solo funciones pasadas",
            tipo=Media.Tipo.PELICULA,
            estado=Media.Estado.EN_CARTELERA,
        )
        cine = Cine.objects.create(nombre="Cine A", ciudad="valledupar")
        Funcion.objects.create(
            cine=cine, media=media, fecha_hora=timezone.now() - timedelta(hours=1)
        )

        resultado = limpiar_cartelera_vencida.apply().get()

        self.assertEqual(resultado["funciones_vencidas_eliminadas"], 1)
        self.assertEqual(resultado["peliculas_fuera_cartelera"], 1)
        self.assertFalse(Funcion.objects.exists())
        media.refresh_from_db()
        self.assertEqual(media.estado, Media.Estado.FUERA_CARTELERA)