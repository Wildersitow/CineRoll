from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Media
from social.models import Resena, Seguimiento

Usuario = get_user_model()


class SeguimientoYFeedAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = Usuario.objects.create_user(
            username="ana", email="ana@example.com", password="Password123!", first_name="Ana", last_name="García"
        )
        cls.user2 = Usuario.objects.create_user(
            username="beto", email="beto@example.com", password="Password123!", first_name="Beto", last_name="Pérez"
        )
        cls.user3 = Usuario.objects.create_user(
            username="carla", email="carla@example.com", password="Password123!", first_name="Carla"
        )
        cls.media1 = Media.objects.create(
            titulo="Blade Runner", tipo=Media.Tipo.PELICULA
        )
        cls.media2 = Media.objects.create(
            titulo="Dune", tipo=Media.Tipo.PELICULA
        )

    def test_seguir_usuario_primera_vez_201_y_segunda_vez_200(self):
        self.client.force_authenticate(self.user1)
        url = reverse("usuario-seguir", args=["beto"])

        # Primera vez -> 201 Created
        res1 = self.client.post(url)
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Seguimiento.objects.filter(seguidor=self.user1, seguido=self.user2).exists())

        # Segunda vez -> 200 OK (idempotente)
        res2 = self.client.post(url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(Seguimiento.objects.filter(seguidor=self.user1, seguido=self.user2).count(), 1)

    def test_dejar_de_seguir_204_idempotente(self):
        Seguimiento.objects.create(seguidor=self.user1, seguido=self.user2)
        self.client.force_authenticate(self.user1)
        url = reverse("usuario-seguir", args=["beto"])

        # Dejar de seguir cuando ya lo seguía -> 204
        res1 = self.client.delete(url)
        self.assertEqual(res1.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Seguimiento.objects.filter(seguidor=self.user1, seguido=self.user2).exists())

        # Dejar de seguir cuando no lo seguía -> 204 también
        res2 = self.client.delete(url)
        self.assertEqual(res2.status_code, status.HTTP_204_NO_CONTENT)

    def test_autoseguimiento_da_400(self):
        self.client.force_authenticate(self.user1)
        url = reverse("usuario-seguir", args=["ana"])

        res_post = self.client.post(url)
        self.assertEqual(res_post.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", res_post.data)

        res_del = self.client.delete(url)
        self.assertEqual(res_del.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", res_del.data)

    def test_seguir_sin_sesion_da_401(self):
        url = reverse("usuario-seguir", args=["beto"])
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(res.data["error"]["codigo"], "not_authenticated")

    def test_seguir_usuario_inexistente_da_404(self):
        self.client.force_authenticate(self.user1)
        url = reverse("usuario-seguir", args=["inexistente"])
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_listado_seguidores_paginado(self):
        Seguimiento.objects.create(seguidor=self.user1, seguido=self.user2)
        Seguimiento.objects.create(seguidor=self.user3, seguido=self.user2)

        url = reverse("usuario-seguidores", args=["beto"])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
        self.assertEqual(res.data["count"], 2)

        usernames = [u["username"] for u in res.data["results"]]
        self.assertIn("ana", usernames)
        self.assertIn("carla", usernames)
        self.assertIn("nombre", res.data["results"][0])

    def test_listado_siguiendo_paginado(self):
        Seguimiento.objects.create(seguidor=self.user1, seguido=self.user2)
        Seguimiento.objects.create(seguidor=self.user1, seguido=self.user3)

        url = reverse("usuario-siguiendo", args=["ana"])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
        self.assertEqual(res.data["count"], 2)

        usernames = [u["username"] for u in res.data["results"]]
        self.assertIn("beto", usernames)
        self.assertIn("carla", usernames)

    def test_feed_actividad_solo_muestra_seguidos_visibles(self):
        # ana sigue a beto, pero NO a carla
        Seguimiento.objects.create(seguidor=self.user1, seguido=self.user2)

        # beto tiene una reseña visible y una oculta
        Resena.objects.create(
            usuario=self.user2, media=self.media1, puntuacion=9, texto="Increíble", oculta=False
        )
        Resena.objects.create(
            usuario=self.user2, media=self.media2, puntuacion=1, texto="Spam", oculta=True
        )

        # carla tiene una reseña visible
        Resena.objects.create(
            usuario=self.user3, media=self.media2, puntuacion=8, texto="Muy buena", oculta=False
        )

        self.client.force_authenticate(self.user1)
        url = reverse("usuario-feed")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
        self.assertEqual(res.data["count"], 1)

        primera = res.data["results"][0]
        self.assertEqual(primera["usuario"], "beto")
        self.assertEqual(primera["media_titulo"], "Blade Runner")
        self.assertEqual(primera["puntuacion"], 9)
        self.assertEqual(primera["texto"], "Increíble")

    def test_feed_actividad_numero_fijo_de_consultas(self):
        # Crear varios seguidos y reseñas
        Seguimiento.objects.create(seguidor=self.user1, seguido=self.user2)
        Seguimiento.objects.create(seguidor=self.user1, seguido=self.user3)

        for i in range(10):
            m = Media.objects.create(titulo=f"Película {i}", tipo=Media.Tipo.PELICULA)
            Resena.objects.create(usuario=self.user2, media=m, puntuacion=8, texto=f"Texto {i}")

        self.client.force_authenticate(self.user1)
        url = reverse("usuario-feed")

        # Con select_related("usuario", "media"), solo se ejecutan 2 consultas: COUNT y SELECT paginado con JOINs
        with self.assertNumQueries(2):
            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(res.data["count"], 10)
