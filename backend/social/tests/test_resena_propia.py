from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Media
from social.models import Resena
from usuarios.models import Usuario


class ResenaPropiaMediaTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="valeria", email="valeria@example.com", password="Passw0rd-2026!"
        )
        self.otro_usuario = Usuario.objects.create_user(
            username="sergio", email="sergio@example.com", password="Passw0rd-2026!"
        )
        self.media = Media.objects.create(
            titulo="Spider-Man", tipo=Media.Tipo.PELICULA
        )
        self.otra_media = Media.objects.create(
            titulo="Batman", tipo=Media.Tipo.PELICULA
        )
        self.url = reverse("media-resena-propia", kwargs={"media_id": self.media.id})

    def test_visitante_no_autenticado_retorna_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_usuario_sin_resena_retorna_404(self):
        self.client.force_authenticate(self.usuario)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_usuario_con_resena_retorna_su_resena(self):
        # Crear reseña propia
        resena = Resena.objects.create(
            usuario=self.usuario,
            media=self.media,
            puntuacion=9,
            texto="Excelente película animada",
        )
        # Sergio también reseña Spider-Man
        Resena.objects.create(
            usuario=self.otro_usuario,
            media=self.media,
            puntuacion=4,
            texto="No me gustó",
        )

        self.client.force_authenticate(self.usuario)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], resena.id)
        self.assertEqual(response.data["usuario"], "valeria")
        self.assertEqual(response.data["puntuacion"], 9)
        self.assertEqual(response.data["texto"], "Excelente película animada")
        self.assertEqual(response.data["media_titulo"], "Spider-Man")

    def test_alias_de_url_funcionan_igual(self):
        resena = Resena.objects.create(
            usuario=self.usuario,
            media=self.media,
            puntuacion=10,
        )
        self.client.force_authenticate(self.usuario)

        alias_urls = [
            reverse("media-resenas-propia", kwargs={"media_id": self.media.id}),
            reverse("media-resenas-me", kwargs={"media_id": self.media.id}),
        ]
        for url in alias_urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, status.HTTP_200_OK)
                self.assertEqual(res.data["id"], resena.id)
