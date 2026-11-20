import logging

from django.conf import settings
from django.test import SimpleTestCase


class LoggingTests(SimpleTestCase):
    def test_hay_un_handler_de_consola_con_fecha_y_nombre_del_logger(self):
        formato = settings.LOGGING["formatters"]["estandar"]["format"]

        self.assertIn("console", settings.LOGGING["handlers"])
        self.assertIn("{asctime}", formato)
        self.assertIn("{name}", formato)

    def test_el_root_envia_a_la_consola(self):
        self.assertEqual(settings.LOGGING["root"]["handlers"], ["console"])

    def test_los_avisos_de_cartelera_llegan_al_root(self):
        # Los loggers de cines.* no tienen handler propio: deben propagar al root.
        for nombre in ("cines.services", "cines.locks"):
            with self.subTest(logger=nombre):
                logger = logging.getLogger(nombre)
                self.assertEqual(logger.handlers, [])
                self.assertTrue(logger.propagate)
                self.assertTrue(logger.isEnabledFor(logging.WARNING))