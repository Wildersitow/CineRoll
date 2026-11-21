from contextlib import contextmanager
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase

from cines.models import EjecucionScraping
from cines.services import CarteleraScrapeResult
from backend.usuarios.tasks import scrape_cartelera_task
from config import celery_app


@contextmanager
def _candado_libre(cine, ciudad, timeout):
    yield True


def _resultado():
    return CarteleraScrapeResult(
        cine="cinepolis",
        ciudad="valledupar",
        funciones_leidas=7,
        funciones_asociadas=7,
        funciones_creadas=7,
        funciones_actualizadas=0,
        titulos_pendientes=0,
        peliculas_en_cartelera=1,
        estrenos_leidos=0,
        estrenos_asociados=0,
        funciones_vencidas_eliminadas=0,
        peliculas_fuera_cartelera=0,
        estrenos_sin_coincidencia=(),
        titulos_pendientes_mostrar=(),
    )


class ModoSincronoTests(TestCase):
    def setUp(self):
        anterior = celery_app.conf.task_always_eager
        celery_app.conf.task_always_eager = True
        self.addCleanup(setattr, celery_app.conf, "task_always_eager", anterior)

        parche = patch("cines.tasks.candado_scraping", _candado_libre)
        parche.start()
        self.addCleanup(parche.stop)

    @patch("cines.tasks.scrape_and_save_cartelera")
    def test_delay_ejecuta_la_tarea_en_el_mismo_proceso(self, servicio):
        servicio.return_value = _resultado()

        resultado = scrape_cartelera_task.delay("cinepolis", "valledupar")

        self.assertTrue(resultado.successful())
        self.assertEqual(resultado.get()["funciones_leidas"], 7)
        self.assertEqual(
            EjecucionScraping.objects.get().estado, EjecucionScraping.Estado.EXITOSA
        )


class ConfiguracionDeWorkerTests(SimpleTestCase):
    def test_el_worker_reintenta_conectar_a_redis_al_arrancar(self):
        self.assertTrue(settings.CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP)

    def test_el_modo_sincrono_esta_apagado_por_defecto(self):
        # Si alguien lo deja en True en el .env de producción, las tareas no
        # llegarían nunca al worker. Esta prueba solo vale si el .env no lo activa.
        self.assertFalse(settings.CELERY_TASK_ALWAYS_EAGER)