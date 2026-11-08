from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from usuarios.models import Usuario


class PerfilTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="ana", email="ana@example.com", password="Un4Clave-Segura!", first_name="Ana"
        )
        self.otro = Usuario.objects.create_user(
            username="beto", email="beto@example.com", password="Un4Clave-Segura!"
        )
        self.url = reverse("usuarios_me")

    def test_requiere_sesion(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.patch(self.url, {"biografia": "x"}).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ver_perfil_incluye_avatar_y_biografia(self):
        self.client.force_authenticate(self.usuario)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for campo in ("id", "username", "nombre", "email", "avatar", "biografia", "is_staff"):
            self.assertIn(campo, response.data)
        self.assertNotIn("password", response.data)

    def test_editar_perfil(self):
        self.client.force_authenticate(self.usuario)

        response = self.client.patch(
            self.url,
            {"first_name": "Ana María", "biografia": "Fan del cine.", "avatar": "https://example.com/a.png"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.first_name, "Ana María")
        self.assertEqual(self.usuario.biografia, "Fan del cine.")
        self.assertEqual(self.usuario.avatar, "https://example.com/a.png")
        self.assertEqual(response.data["nombre"], "Ana María")

    def test_no_puede_cambiar_usuario_ni_permisos(self):
        self.client.force_authenticate(self.usuario)

        self.client.patch(self.url, {"username": "hackeado", "is_staff": True, "is_superuser": True})

        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.username, "ana")
        self.assertFalse(self.usuario.is_staff)
        self.assertFalse(self.usuario.is_superuser)

    def test_cambiar_correo_valida_que_no_este_en_uso(self):
        self.client.force_authenticate(self.usuario)

        repetido = self.client.patch(self.url, {"email": "BETO@example.com"})
        propio = self.client.patch(self.url, {"email": "Ana@Example.com"})
        nuevo = self.client.patch(self.url, {"email": "nuevo@example.com"})

        self.assertEqual(repetido.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(propio.status_code, status.HTTP_200_OK)  # su propio correo no cuenta como repetido
        self.assertEqual(nuevo.status_code, status.HTTP_200_OK)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.email, "nuevo@example.com")

    def test_biografia_demasiado_larga(self):
        self.client.force_authenticate(self.usuario)

        response = self.client.patch(self.url, {"biografia": "x" * 501})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_se_puede_borrar_el_perfil_por_la_api(self):
        self.client.force_authenticate(self.usuario)

        self.assertEqual(self.client.delete(self.url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_ruta_antigua_sigue_funcionando(self):
        self.client.force_authenticate(self.usuario)

        self.assertEqual(self.client.get(reverse("usuario_me")).status_code, status.HTTP_200_OK)
