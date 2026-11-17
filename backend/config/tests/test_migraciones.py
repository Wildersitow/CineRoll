from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class MigracionesAlDiaTests(TestCase):
    def test_los_modelos_no_tienen_migraciones_pendientes(self):
        salida = StringIO()

        try:
            call_command(
                "makemigrations",
                check=True,
                dry_run=True,
                stdout=salida,
                stderr=salida,
            )
        except SystemExit:
            self.fail(
                "Hay cambios en los modelos sin migración:\n" + salida.getvalue()
            )