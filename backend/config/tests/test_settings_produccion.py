import importlib
import os
import sys
from unittest import mock

from decouple import UndefinedValueError
from django.test import SimpleTestCase

MODULO = "config.settings.production"
VARIABLES = {
    "ALLOWED_HOSTS": "api.cineroll.com,cineroll.com",
    "CORS_ALLOWED_ORIGINS": "https://cineroll.com",
    "CSRF_TRUSTED_ORIGINS": "https://api.cineroll.com",
}


class SettingsProduccionTests(SimpleTestCase):
    """Carga config/settings/production.py con distintas variables de entorno."""

    def cargar(self, **variables):
        sys.modules.pop(MODULO, None)
        try:
            with mock.patch.dict(os.environ, variables):
                return importlib.import_module(MODULO)
        finally:
            sys.modules.pop(MODULO, None)

    def test_apaga_debug_y_lee_dominios_del_entorno(self):
        produccion = self.cargar(**VARIABLES)

        self.assertFalse(produccion.DEBUG)
        self.assertEqual(produccion.ALLOWED_HOSTS, ["api.cineroll.com", "cineroll.com"])
        self.assertEqual(produccion.CORS_ALLOWED_ORIGINS, ["https://cineroll.com"])
        self.assertFalse(produccion.CORS_ALLOW_ALL_ORIGINS)
        self.assertEqual(produccion.CSRF_TRUSTED_ORIGINS, ["https://api.cineroll.com"])

    def test_activa_seguridad_https_por_defecto(self):
        produccion = self.cargar(**VARIABLES)

        self.assertTrue(produccion.SESSION_COOKIE_SECURE)
        self.assertTrue(produccion.CSRF_COOKIE_SECURE)
        self.assertTrue(produccion.SECURE_SSL_REDIRECT)
        self.assertGreater(produccion.SECURE_HSTS_SECONDS, 0)

    def test_https_se_puede_apagar(self):
        produccion = self.cargar(**VARIABLES, USAR_HTTPS="False")

        self.assertFalse(produccion.SECURE_SSL_REDIRECT)
        self.assertEqual(produccion.SECURE_HSTS_SECONDS, 0)

    def test_falta_allowed_hosts_no_arranca(self):
        variables = {k: v for k, v in VARIABLES.items() if k != "ALLOWED_HOSTS"}
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ALLOWED_HOSTS", None)
            with self.assertRaises(UndefinedValueError):
                self.cargar(**variables)
