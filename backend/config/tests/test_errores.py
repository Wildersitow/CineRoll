from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Media

Usuario = get_user_model()


class FormatoErroresTests(APITestCase):
    """Todas las respuestas de error usan {"error": {"codigo", "mensaje", "campos"?}}."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="ana", email="ana@example.com", password="Secur3Passw0rd!"
        )
        cls.media = Media.objects.create(titulo="Ficha", tipo=Media.Tipo.PELICULA)

    def assertFormatoError(self, response, status_esperado, codigo):
        self.assertEqual(response.status_code, status_esperado)
        self.assertEqual(set(response.data), {"error"})
        self.assertEqual(response.data["error"]["codigo"], codigo)
        self.assertIsInstance(response.data["error"]["mensaje"], str)
        self.assertTrue(response.data["error"]["mensaje"])

    def test_no_encontrado(self):
        response = self.client.get(reverse("media-detail", args=[999999]))
        self.assertFormatoError(response, status.HTTP_404_NOT_FOUND, "not_found")

    def test_sin_sesion(self):
        response = self.client.get(reverse("usuarios_me"))
        self.assertFormatoError(
            response, status.HTTP_401_UNAUTHORIZED, "not_authenticated"
        )

    def test_token_invalido(self):
        response = self.client.get(
            reverse("usuarios_me"), HTTP_AUTHORIZATION="Bearer token-falso"
        )
        self.assertFormatoError(response, status.HTTP_401_UNAUTHORIZED, "token_not_valid")

    def test_sin_permiso(self):
        self.client.force_authenticate(self.usuario)
        response = self.client.post(reverse("media-list"), {"titulo": "Nueva"})
        self.assertFormatoError(
            response, status.HTTP_403_FORBIDDEN, "permission_denied"
        )

    def test_metodo_no_permitido(self):
        self.client.force_authenticate(self.usuario)
        response = self.client.delete(reverse("cine-list"))
        self.assertFormatoError(
            response, status.HTTP_405_METHOD_NOT_ALLOWED, "method_not_allowed"
        )

    def test_validacion_por_campos_incluye_campos(self):
        response = self.client.post(
            reverse("auth_registro"),
            {"username": "ana", "email": "no-es-correo", "password": "123"},
        )
        self.assertFormatoError(
            response, status.HTTP_400_BAD_REQUEST, "datos_invalidos"
        )
        campos = response.data["error"]["campos"]
        self.assertIn("username", campos)
        self.assertIn("email", campos)

    def test_validacion_de_parametro_de_filtro(self):
        response = self.client.get(reverse("media-list"), {"anio": "abc"})
        self.assertFormatoError(
            response, status.HTTP_400_BAD_REQUEST, "datos_invalidos"
        )
        self.assertIn("anio", response.data["error"]["campos"])

    def test_login_sin_datos(self):
        response = self.client.post(reverse("auth_login"), {})
        self.assertFormatoError(
            response, status.HTTP_400_BAD_REQUEST, "datos_incompletos"
        )
        self.assertNotIn("campos", response.data["error"])

    def test_login_credenciales_incorrectas(self):
        response = self.client.post(
            reverse("auth_login"), {"usuario": "ana", "clave": "otra"}
        )
        self.assertFormatoError(
            response, status.HTTP_400_BAD_REQUEST, "credenciales_invalidas"
        )
        self.assertEqual(response.data["error"]["mensaje"], "Credenciales incorrectas.")

    def test_error_con_detail_usa_su_mensaje(self):
        self.client.force_authenticate(self.usuario)
        url = reverse("media-resenas", args=[self.media.pk])
        self.client.post(url, {"puntuacion": 8})
        response = self.client.post(url, {"puntuacion": 9})
        self.assertFormatoError(response, status.HTTP_400_BAD_REQUEST, "invalid")
        self.assertIn("Ya reseñaste", response.data["error"]["mensaje"])
        self.assertNotIn("campos", response.data["error"])
