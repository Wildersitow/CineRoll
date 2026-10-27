from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

Usuario = get_user_model()


class JWTAuthTestCase(APITestCase):
    def setUp(self):
        self.username = "testuser"
        self.email = "testuser@example.com"
        self.password = "Secur3Passw0rd!"
        self.first_name = "Victor"
        self.last_name = "Ospino"

        self.user = Usuario.objects.create_user(
            username=self.username,
            email=self.email,
            password=self.password,
            first_name=self.first_name,
            last_name=self.last_name,
        )

    def test_login_with_username_success(self):
        """Prueba login por username devolviendo tokens y datos limpios (sin codigo quemado)"""
        url = reverse("usuario_login")
        response = self.client.post(url, {"usuario": self.username, "clave": self.password})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["nombre"], "Victor Ospino")
        self.assertEqual(response.data["email"], self.email)
        # Verificar que el campo obsoleto 'codigo' NO exista
        self.assertNotIn("codigo", response.data)

        # Verificar claims dentro del token JWT
        access_token = AccessToken(response.data["token"])
        self.assertEqual(str(access_token["user_id"]), str(self.user.id))
        self.assertEqual(access_token["nombre"], "Victor Ospino")
        self.assertEqual(access_token["email"], self.email)
        self.assertEqual(access_token["username"], self.username)

    def test_login_with_email_success(self):
        """Prueba login con email"""
        url = reverse("usuario_login")
        response = self.client.post(url, {"usuario": self.email, "clave": self.password})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.id)
        self.assertNotIn("codigo", response.data)

    def test_login_invalid_credentials(self):
        """Prueba que credenciales incorrectas retornen 400"""
        url = reverse("usuario_login")
        response = self.client.post(url, {"usuario": self.username, "clave": "WrongPassword"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_token_obtain_pair_endpoint(self):
        """Prueba endpoint estándar /api/token/ con CustomTokenObtainPairSerializer"""
        url = reverse("token_obtain_pair")
        response = self.client.post(url, {"username": self.username, "password": self.password})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["nombre"], "Victor Ospino")
        self.assertNotIn("codigo", response.data)

    def test_current_user_me_authenticated(self):
        """Prueba endpoint /api/usuario/me/ con Bearer Token"""
        login_url = reverse("usuario_login")
        login_res = self.client.post(login_url, {"usuario": self.username, "clave": self.password})
        token = login_res.data["token"]

        me_url = reverse("usuario_me")
        response = self.client.get(me_url, HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.id)
        self.assertEqual(response.data["username"], self.username)
        self.assertEqual(response.data["nombre"], "Victor Ospino")
        self.assertEqual(response.data["email"], self.email)

    def test_current_user_me_unauthorized(self):
        """Prueba endpoint /api/usuario/me/ sin token retorna 401"""
        me_url = reverse("usuario_me")
        response = self.client.get(me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_endpoint(self):
        """Prueba renovación de token con /api/token/refresh/"""
        login_url = reverse("usuario_login")
        login_res = self.client.post(login_url, {"usuario": self.username, "clave": self.password})
        refresh_token = login_res.data["refresh"]

        refresh_url = reverse("token_refresh")
        response = self.client.post(refresh_url, {"refresh": refresh_token})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
