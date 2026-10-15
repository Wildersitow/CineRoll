from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Credito, Genero, Media, Persona


class CatalogApiTests(APITestCase):
    def setUp(self):
        genero = Genero.objects.create(nombre="Drama")
        self.media = Media.objects.create(
            titulo="Ficha de prueba",
            titulo_original="Test title",
            tipo=Media.Tipo.PELICULA,
            sinopsis="Una historia de prueba.",
        )
        self.media.generos.add(genero)

        director = Persona.objects.create(nombre="Directora de prueba")
        actor = Persona.objects.create(nombre="Actor de prueba")
        Credito.objects.create(
            media=self.media,
            persona=director,
            rol=Credito.Rol.DIRECTOR,
        )
        Credito.objects.create(
            media=self.media,
            persona=actor,
            rol=Credito.Rol.ACTOR,
        )

    def test_media_list_is_public_and_includes_genres(self):
        response = self.client.get(reverse("media-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["titulo"], "Ficha de prueba")
        self.assertEqual(
            response.data["results"][0]["generos"][0]["nombre"], "Drama"
        )

    def test_media_detail_includes_cast_directors_and_genres(self):
        response = self.client.get(
            reverse("media-detail", kwargs={"pk": self.media.pk})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["generos"][0]["nombre"], "Drama")
        self.assertEqual(response.data["reparto"][0]["nombre"], "Actor de prueba")
        self.assertEqual(
            response.data["directores"][0]["nombre"], "Directora de prueba"
        )

    def test_genre_list_is_public(self):
        response = self.client.get(reverse("genero-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["nombre"], "Drama")

    def test_media_list_does_not_allow_writes(self):
        response = self.client.post(
            reverse("media-list"), {"titulo": "No permitido"}
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)