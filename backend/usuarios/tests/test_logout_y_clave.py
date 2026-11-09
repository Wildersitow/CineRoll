from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

Usuario = get_user_model()


class LogoutYBlacklistTests(APITestCase):
    def setUp(self):
        self.username = "carlos"
        self.email = "carlos@example.com"
        self.password = "Secur3Passw0rd!"
        self.usuario = Usuario.objects.create_user(
            username=self.username,
            email=self.email,
            password=self.password,
            first_name="Carlos",
        )
        self.logout_url = reverse("auth_logout")
        self.refresh_url = reverse("auth_refresh")
        self.login_url = reverse("auth_login")

    def _obtener_tokens(self):
        res = self.client.post(
            self.login_url, {"usuario": self.username, "clave": self.password}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        return res.data["access"], res.data["refresh"]

    def test_logout_invalida_refresh_token(self):
        """Cerrar sesión envía el refresh token a la lista negra."""
        _, refresh = self._obtener_tokens()

        # Cerrar sesión
        response = self.client.post(self.logout_url, {"refresh": refresh})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["mensaje"], "Sesión cerrada correctamente.")

        # Intentar refrescar con el token en lista negra debe fallar (401)
        res_refresh = self.client.post(self.refresh_url, {"refresh": refresh})
        self.assertEqual(res_refresh.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rotacion_con_lista_negra_activa(self):
        """Al rotar el token, el anterior queda en la lista negra (BLACKLIST_AFTER_ROTATION=True)."""
        _, refresh_inicial = self._obtener_tokens()

        # Primer refresco: rota el token
        res1 = self.client.post(self.refresh_url, {"refresh": refresh_inicial})
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        nuevo_refresh = res1.data.get("refresh")
        self.assertIsNotNone(nuevo_refresh)

        # Usar el refresh anterior debe fallar porque ya está en lista negra
        res_invalido = self.client.post(self.refresh_url, {"refresh": refresh_inicial})
        self.assertEqual(res_invalido.status_code, status.HTTP_401_UNAUTHORIZED)

        # El nuevo refresh sí debe ser válido
        res2 = self.client.post(self.refresh_url, {"refresh": nuevo_refresh})
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

    def test_logout_sin_refresh_token(self):
        """Llamar a logout sin enviar el refresh devuelve 400."""
        response = self.client.post(self.logout_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_con_token_ya_revocado(self):
        """Intentar revocar un token ya revocado devuelve 400."""
        _, refresh = self._obtener_tokens()
        self.client.post(self.logout_url, {"refresh": refresh})

        repetido = self.client.post(self.logout_url, {"refresh": refresh})
        self.assertEqual(repetido.status_code, status.HTTP_400_BAD_REQUEST)


class CambioPasswordTests(APITestCase):
    def setUp(self):
        self.username = "david"
        self.password = "ClaveAnterior123!"
        self.usuario = Usuario.objects.create_user(
            username=self.username,
            email="david@example.com",
            password=self.password,
        )
        self.url = reverse("usuarios_me_clave")
        self.login_url = reverse("auth_login")

    def test_requiere_autenticacion(self):
        response = self.client.post(
            self.url,
            {"clave_actual": self.password, "clave_nueva": "NuevaClave456!"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_clave_actual_incorrecta(self):
        self.client.force_authenticate(self.usuario)
        response = self.client.post(
            self.url,
            {"clave_actual": "ClaveEquivocada!", "clave_nueva": "NuevaClave456!"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_clave_nueva_debil(self):
        self.client.force_authenticate(self.usuario)
        response = self.client.post(
            self.url,
            {"clave_actual": self.password, "clave_nueva": "123"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cambio_clave_exitoso_y_login_con_nueva_clave(self):
        self.client.force_authenticate(self.usuario)
        nueva_clave = "Nuev4ClaveSegura-2026!"
        response = self.client.post(
            self.url,
            {"clave_actual": self.password, "clave_nueva": nueva_clave},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        # La clave anterior ya no sirve
        self.client.logout()
        res_fallo = self.client.post(
            self.login_url, {"usuario": self.username, "clave": self.password}
        )
        self.assertEqual(res_fallo.status_code, status.HTTP_400_BAD_REQUEST)

        # La nueva clave permite iniciar sesión
        res_exito = self.client.post(
            self.login_url, {"usuario": self.username, "clave": nueva_clave}
        )
        self.assertEqual(res_exito.status_code, status.HTTP_200_OK)
