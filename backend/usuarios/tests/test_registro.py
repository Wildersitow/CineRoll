from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from usuarios.models import Usuario

CLAVE_VALIDA = "Un4Clave-Segura!"


class RegistroTests(APITestCase):
    def setUp(self):
        self.url = reverse("auth_registro")
        self.datos = {
            "username": "nueva",
            "email": "Nueva@Example.com",
            "password": CLAVE_VALIDA,
            "first_name": "Nora",
            "last_name": "Vega",
        }

    def test_registro_crea_usuario_y_devuelve_tokens(self):
        response = self.client.post(self.url, self.datos)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for campo in ("id", "username", "nombre", "email", "token", "access", "refresh"):
            self.assertIn(campo, response.data)
        self.assertEqual(response.data["nombre"], "Nora Vega")
        self.assertNotIn("password", response.data)

        usuario = Usuario.objects.get(username="nueva")
        self.assertEqual(usuario.email, "nueva@example.com")  # normalizado a minúsculas
        self.assertNotEqual(usuario.password, CLAVE_VALIDA)  # guardada con hash
        self.assertTrue(usuario.check_password(CLAVE_VALIDA))
        self.assertFalse(usuario.is_staff)

    def test_el_token_del_registro_sirve_de_inmediato(self):
        token = self.client.post(self.url, self.datos).data["token"]

        response = self.client.get(reverse("usuarios_me"), HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "nueva")

    def test_se_puede_iniciar_sesion_despues_de_registrarse(self):
        self.client.post(self.url, self.datos)

        response = self.client.post(
            reverse("auth_login"), {"usuario": "nueva@example.com", "clave": CLAVE_VALIDA}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_permite_elevarse_a_administrador(self):
        self.client.post(self.url, {**self.datos, "is_staff": True, "is_superuser": True})

        usuario = Usuario.objects.get(username="nueva")
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)

    def test_rechaza_clave_debil(self):
        for clave in ("123", "12345678", "password"):
            with self.subTest(clave=clave):
                response = self.client.post(self.url, {**self.datos, "password": clave})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("password", response.data)
        self.assertFalse(Usuario.objects.filter(username="nueva").exists())

    def test_rechaza_clave_parecida_al_usuario(self):
        response = self.client.post(self.url, {**self.datos, "password": "nueva2026"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_rechaza_usuario_repetido(self):
        Usuario.objects.create_user(username="nueva", email="otra@example.com", password=CLAVE_VALIDA)

        response = self.client.post(self.url, self.datos)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_rechaza_correo_repetido_sin_distinguir_mayusculas(self):
        Usuario.objects.create_user(username="otra", email="nueva@example.com", password=CLAVE_VALIDA)

        response = self.client.post(self.url, self.datos)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_exige_usuario_correo_valido_y_clave(self):
        for campo in ("username", "email", "password"):
            with self.subTest(falta=campo):
                datos = {k: v for k, v in self.datos.items() if k != campo}
                self.assertEqual(self.client.post(self.url, datos).status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(self.url, {**self.datos, "email": "no-es-correo"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RutasDeAutenticacionTests(APITestCase):
    """Las rutas del reparto (/auth/...) y las que ya usa el frontend responden igual."""

    def setUp(self):
        Usuario.objects.create_user(username="ana", email="ana@example.com", password=CLAVE_VALIDA)

    def test_login_y_refresh_en_rutas_auth(self):
        login = self.client.post(reverse("auth_login"), {"usuario": "ana", "clave": CLAVE_VALIDA})
        self.assertEqual(login.status_code, status.HTTP_200_OK)

        refresh = self.client.post(reverse("auth_refresh"), {"refresh": login.data["refresh"]})
        self.assertEqual(refresh.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh.data)

    def test_login_con_correo_en_mayusculas(self):
        response = self.client.post(reverse("auth_login"), {"usuario": "ANA@Example.com", "clave": CLAVE_VALIDA})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_con_correo_inexistente_no_rompe(self):
        response = self.client.post(reverse("auth_login"), {"usuario": "nadie@example.com", "clave": "x"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ModeloUsuarioTests(APITestCase):
    def test_varios_usuarios_sin_correo_no_chocan(self):
        a = Usuario.objects.create_user(username="a", password=CLAVE_VALIDA)
        b = Usuario.objects.create_user(username="b", password=CLAVE_VALIDA)

        self.assertIsNone(a.email)
        self.assertIsNone(b.email)

    def test_avatar_y_biografia_son_opcionales(self):
        usuario = Usuario.objects.create_user(username="c", password=CLAVE_VALIDA)

        self.assertEqual(usuario.avatar, "")
        self.assertEqual(usuario.biografia, "")
