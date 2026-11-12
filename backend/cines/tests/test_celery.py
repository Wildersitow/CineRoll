from django.test import SimpleTestCase

from cines.tasks import ping
from config import celery_app


class CeleryTests(SimpleTestCase):
    def test_la_tarea_de_prueba_se_ejecuta(self):
        self.assertEqual(ping.apply().get(), "pong")

    def test_celery_lee_la_configuracion_de_django(self):
        self.assertTrue(celery_app.conf.broker_url.startswith("redis://"))

    def test_la_tarea_queda_registrada(self):
        celery_app.loader.import_default_modules()
        self.assertIn("cines.tasks.ping", celery_app.tasks)