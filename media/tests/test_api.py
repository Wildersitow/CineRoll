from datetime import date

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

    def test_search_matches_title_original_and_synopsis(self):
        response = self.client.get(reverse("media-list"), {"search": "TEST"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.media.pk)

    def test_filters_can_be_combined_and_genre_ignores_accents(self):
        genero = Genero.objects.create(nombre="Acción")
        media = Media.objects.create(
            titulo="Acción de prueba",
            titulo_original="Action test",
            tipo=Media.Tipo.PELICULA,
            fecha_estreno=date(2025, 5, 2),
            estado=Media.Estado.EN_CARTELERA,
        )
        media.generos.add(genero)

        response = self.client.get(
            reverse("media-list"),
            {
                "genero": "accion",
                "tipo": "pelicula",
                "anio": "2025",
                "estado": "en_cartelera",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], media.pk)

    def test_media_list_uses_configured_pagination(self):
        for index in range(21):
            Media.objects.create(
                titulo=f"Ficha adicional {index:02}",
                tipo=Media.Tipo.PELICULA,
            )

        first_page = self.client.get(reverse("media-list"))
        second_page = self.client.get(reverse("media-list"), {"page": 2})

        self.assertEqual(first_page.data["count"], 22)
        self.assertEqual(len(first_page.data["results"]), 20)
        self.assertEqual(len(second_page.data["results"]), 2)

    def test_invalid_year_returns_bad_request(self):
        response = self.client.get(reverse("media-list"), {"anio": "dosmil"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)