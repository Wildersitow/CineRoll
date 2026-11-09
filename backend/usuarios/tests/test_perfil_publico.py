from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Media
from social.models import Resena

Usuario = get_user_model()


class PerfilPublicoTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="lucia",
            email="lucia@example.com",
            password="ClaveSegura123!",
            first_name="Lucía",
            last_name="Gómez",
            biografia="Cinéfila empedernida.",
            avatar="https://example.com/avatar.jpg",
        )
        self.media1 = Media.objects.create(
            titulo="Inception", tipo=Media.Tipo.PELICULA
        )
        self.media2 = Media.objects.create(
            titulo="Interstellar", tipo=Media.Tipo.PELICULA
        )
        self.media3 = Media.objects.create(
            titulo="Dunkirk", tipo=Media.Tipo.PELICULA
        )

        # Crear dos reseñas visibles y una oculta
        self.resena1 = Resena.objects.create(
            usuario=self.usuario, media=self.media1, puntuacion=9, texto="Obra maestra"
        )
        self.resena2 = Resena.objects.create(
            usuario=self.usuario, media=self.media2, puntuacion=8, texto="Muy buena"
        )
        self.resena_oculta = Resena.objects.create(
            usuario=self.usuario, media=self.media3, puntuacion=2, oculta=True
        )

        self.otro_usuario = Usuario.objects.create_user(
            username="mateo", email="mateo@example.com", password="ClaveSegura123!"
        )
        self.resena_otro = Resena.objects.create(
            usuario=self.otro_usuario, media=self.media2, puntuacion=7
        )

    def test_ver_perfil_publico_por_id_y_por_username(self):
        """Un visitante puede ver el perfil público sin credenciales ni datos privados."""
        urls = [
            reverse("usuarios_perfil_publico_id", kwargs={"pk": self.usuario.id}),
            reverse("usuarios_perfil_publico", kwargs={"username": self.usuario.username}),
        ]
        for url in urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, status.HTTP_200_OK)
                self.assertEqual(res.data["username"], "lucia")
                self.assertEqual(res.data["nombre"], "Lucía Gómez")
                self.assertEqual(res.data["avatar"], "https://example.com/avatar.jpg")
                self.assertEqual(res.data["biografia"], "Cinéfila empedernida.")
                self.assertEqual(res.data["total_resenas"], 2)  # solo las visibles
                self.assertEqual(res.data["promedio_puntuacion_dada"], 8.5)

                # NO debe exponer datos privados
                self.assertNotIn("email", res.data)
                self.assertNotIn("password", res.data)
                self.assertNotIn("is_staff", res.data)
                self.assertNotIn("is_superuser", res.data)

    def test_resenas_publicas_de_un_usuario(self):
        """Lista pública de reseñas de un usuario (solo visibles)."""
        url = reverse("usuarios_resenas_publicas", kwargs={"username": self.usuario.username})
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 2)
        titulos = [item["media_titulo"] for item in res.data["results"]]
        self.assertIn("Inception", titulos)
        self.assertIn("Interstellar", titulos)

    def test_mis_resenas_en_el_perfil(self):
        """Endpoint /api/usuarios/me/resenas/ devuelve solo reseñas del usuario autenticado."""
        url = reverse("usuarios_me_resenas")

        # Sin autenticación da 401
        self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED)

        # Autenticado con lucia
        self.client.force_authenticate(self.usuario)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 2)

        # Autenticado con mateo
        self.client.force_authenticate(self.otro_usuario)
        res_mateo = self.client.get(url)
        self.assertEqual(res_mateo.status_code, status.HTTP_200_OK)
        self.assertEqual(res_mateo.data["count"], 1)
