from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from usuarios.models import Usuario
from usuarios.tasks import limpiar_tokens_vencidos


class LimpiarTokensVencidosTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(username="ana", password="x")

    def _token_vencido(self):
        """Crea un refresh token y retrocede su vencimiento al pasado."""
        refresh = RefreshToken.for_user(self.usuario)
        OutstandingToken.objects.filter(jti=refresh["jti"]).update(
            expires_at=timezone.now() - timedelta(days=1)
        )
        return refresh

    def test_borra_los_vencidos_y_conserva_los_vigentes(self):
        vencido = self._token_vencido()
        vigente = RefreshToken.for_user(self.usuario)

        resultado = limpiar_tokens_vencidos.apply().get()

        self.assertTrue(resultado["ok"])
        jtis = set(OutstandingToken.objects.values_list("jti", flat=True))
        self.assertNotIn(vencido["jti"], jtis)
        self.assertIn(vigente["jti"], jtis)

    def test_borra_tambien_la_entrada_de_lista_negra_del_vencido(self):
        vencido = self._token_vencido()
        BlacklistedToken.objects.create(
            token=OutstandingToken.objects.get(jti=vencido["jti"])
        )

        limpiar_tokens_vencidos.apply().get()

        self.assertFalse(BlacklistedToken.objects.exists())

    def test_un_token_vigente_en_lista_negra_se_conserva(self):
        # Si lo borráramos antes de vencer, volvería a ser utilizable.
        vigente = RefreshToken.for_user(self.usuario)
        vigente.blacklist()

        limpiar_tokens_vencidos.apply().get()

        self.assertTrue(BlacklistedToken.objects.exists())
        self.assertTrue(
            OutstandingToken.objects.filter(jti=vigente["jti"]).exists()
        )

    def test_la_tarea_esta_registrada_en_celery(self):
        from config import celery_app

        celery_app.loader.import_default_modules()
        self.assertIn("usuarios.tasks.limpiar_tokens_vencidos", celery_app.tasks)