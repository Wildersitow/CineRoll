from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import SimpleRateThrottle

from config.throttling import ambito_de
from media.models import Media
from social.views import MediaResenaListCreateView
from usuarios.models import Usuario


def _peticion(url_name, metodo="GET"):
    return SimpleNamespace(
        resolver_match=SimpleNamespace(url_name=url_name), method=metodo
    )


class AmbitoDeTests(APITestCase):
    def test_login_registro_y_cambio_de_clave_son_acceso(self):
        for nombre in (
            "auth_login",
            "usuario_login",
            "token_obtain_pair",
            "auth_registro",
            "usuarios_me_clave",
            "auth_cambiar_clave",
        ):
            with self.subTest(ruta=nombre):
                self.assertEqual(ambito_de(_peticion(nombre, "POST"), object()), "acceso")

    def test_escribir_en_social_es_escritura_social(self):
        vista = MediaResenaListCreateView()
        for metodo in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(metodo=metodo):
                self.assertEqual(
                    ambito_de(_peticion("media-resenas", metodo), vista),
                    "escritura_social",
                )

    def test_leer_en_social_es_general(self):
        self.assertEqual(
            ambito_de(_peticion("media-resenas", "GET"), MediaResenaListCreateView()),
            "general",
        )

    def test_lo_demas_es_general(self):
        self.assertEqual(ambito_de(_peticion("media-list", "GET"), object()), "general")
        self.assertEqual(ambito_de(_peticion("usuarios_me", "PATCH"), object()), "general")
        self.assertEqual(ambito_de(_peticion("auth_refresh", "POST"), object()), "general")


class LimitesDeUsoTests(APITestCase):
    """Las tasas se bajan solo dentro de cada prueba; en TESTING son altísimas."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def tasas(self, **tasas):
        parche = patch.dict(SimpleRateThrottle.THROTTLE_RATES, tasas)
        parche.start()
        self.addCleanup(parche.stop)

    def _login(self):
        return self.client.post(
            reverse("auth_login"), {"usuario": "nadie", "clave": "x"}
        )

    def test_el_login_se_bloquea_al_pasar_el_limite_con_el_formato_unico(self):
        self.tasas(acceso="3/min")

        for _ in range(3):
            self.assertEqual(self._login().status_code, status.HTTP_400_BAD_REQUEST)
        bloqueada = self._login()

        self.assertEqual(bloqueada.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(set(bloqueada.data), {"error"})
        error = bloqueada.data["error"]
        self.assertEqual(error["codigo"], "throttled")
        self.assertIn("Demasiadas solicitudes", error["mensaje"])
        self.assertGreaterEqual(error["espera_segundos"], 1)
        self.assertNotIn("campos", error)
        self.assertIn("Retry-After", bloqueada)

    def test_login_y_registro_comparten_el_mismo_contador(self):
        self.tasas(acceso="3/min")

        self._login()
        self._login()
        self.client.post(reverse("auth_registro"), {})  # 400, pero cuenta
        bloqueada = self._login()

        self.assertEqual(bloqueada.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_bloquear_el_acceso_no_afecta_a_las_lecturas(self):
        self.tasas(acceso="1/min")
        self._login()
        self.assertEqual(self._login().status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        self.assertEqual(
            self.client.get(reverse("media-list")).status_code, status.HTTP_200_OK
        )

    def test_las_lecturas_tienen_su_propio_limite(self):
        self.tasas(general="2/min")
        url = reverse("media-list")

        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.get(url).status_code, status.HTTP_429_TOO_MANY_REQUESTS
        )

    def test_la_escritura_social_se_cuenta_por_usuario_y_no_afecta_a_las_lecturas(self):
        self.tasas(escritura_social="2/min")
        ana = Usuario.objects.create_user(username="ana", password="x")
        beto = Usuario.objects.create_user(username="beto", password="x")
        titulos = [
            Media.objects.create(
                titulo=f"Título {i}",
                tipo=Media.Tipo.PELICULA,
                estado=Media.Estado.EN_CARTELERA,
            )
            for i in range(3)
        ]

        def reseñar(titulo):
            return self.client.post(
                reverse("media-resenas", kwargs={"media_id": titulo.pk}),
                {"puntuacion": 8},
            )

        self.client.force_authenticate(ana)
        self.assertEqual(reseñar(titulos[0]).status_code, status.HTTP_201_CREATED)
        self.assertEqual(reseñar(titulos[1]).status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            reseñar(titulos[2]).status_code, status.HTTP_429_TOO_MANY_REQUESTS
        )

        # Leer sigue funcionando para quien agotó su cupo de escritura...
        lectura = self.client.get(
            reverse("media-resenas", kwargs={"media_id": titulos[0].pk})
        )
        self.assertEqual(lectura.status_code, status.HTTP_200_OK)

        # ...y otro usuario tiene su propio contador.
        self.client.force_authenticate(beto)
        self.assertEqual(reseñar(titulos[2]).status_code, status.HTTP_201_CREATED)

    def test_si_redis_falla_la_peticion_pasa_y_se_avisa_en_el_log(self):
        with patch.object(
            SimpleRateThrottle,
            "allow_request",
            side_effect=__import__("redis").exceptions.ConnectionError("sin Redis"),
        ):
            with self.assertLogs("config.throttling", level="WARNING"):
                response = self.client.get(reverse("media-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)