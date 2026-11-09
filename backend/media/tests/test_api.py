from datetime import date, datetime, timezone

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cines.models import Cine, Funcion
from media.models import Credito, Genero, Media, Persona
from usuarios.models import Usuario


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

        director = Persona.objects.create(
            nombre="Directora de prueba",
            biografia="Directora de películas de prueba.",
            fecha_nacimiento=date(1975, 3, 10),
        )
        self.actor = Persona.objects.create(
            nombre="Actor de prueba",
            biografia="Actor de películas de prueba.",
            fecha_nacimiento=date(1985, 6, 20),
        )
        Credito.objects.create(
            media=self.media,
            persona=director,
            rol=Credito.Rol.DIRECTOR,
        )
        Credito.objects.create(
            media=self.media,
            persona=self.actor,
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
        self.assertEqual(response.data["id"], self.media.pk)
        self.assertEqual(response.data["titulo"], "Ficha de prueba")
        self.assertEqual(response.data["titulo_original"], "Test title")
        self.assertEqual(response.data["generos"][0]["nombre"], "Drama")
        self.assertEqual(response.data["reparto"][0]["nombre"], "Actor de prueba")
        self.assertEqual(
            response.data["directores"][0]["nombre"], "Directora de prueba"
        )

    def test_genre_list_is_public(self):
        response = self.client.get(reverse("genero-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["nombre"], "Drama")

    def test_persona_list_and_detail_are_public_and_include_profile_fields(self):
        list_response = self.client.get(reverse("persona-list"))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        actor_in_list = next(
            persona
            for persona in list_response.data["results"]
            if persona["id"] == self.actor.pk
        )
        self.assertEqual(actor_in_list["biografia"], "Actor de películas de prueba.")
        self.assertEqual(actor_in_list["fecha_nacimiento"], "1985-06-20")

        detail_response = self.client.get(
            reverse("persona-detail", kwargs={"pk": self.actor.pk})
        )

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["nombre"], "Actor de prueba")
        self.assertEqual(
            detail_response.data["biografia"], "Actor de películas de prueba."
        )
        self.assertEqual(detail_response.data["fecha_nacimiento"], "1985-06-20")

    def test_media_list_requires_staff_for_write_requests(self):
        url = reverse("media-list")
        data = {"titulo": "No permitido", "tipo": Media.Tipo.PELICULA}

        anonymous_response = self.client.post(url, data)
        self.assertEqual(
            anonymous_response.status_code, status.HTTP_401_UNAUTHORIZED
        )

        regular_user = Usuario.objects.create_user(
            username="lector", password="test-password"
        )
        self.client.force_authenticate(user=regular_user)
        user_response = self.client.post(url, data)
        self.assertEqual(user_response.status_code, status.HTTP_403_FORBIDDEN)

        admin_user = Usuario.objects.create_user(
            username="admin-catalogo",
            password="test-password",
            is_staff=True,
        )
        self.client.force_authenticate(user=admin_user)
        admin_response = self.client.post(url, data)
        self.assertEqual(admin_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(admin_response.data["titulo"], "No permitido")

    def test_media_can_be_updated_and_deleted_by_admin(self):
        admin_user = Usuario.objects.create_user(
            username="admin-media",
            password="test-password",
            is_staff=True,
        )
        self.client.force_authenticate(user=admin_user)
        url = reverse("media-detail", kwargs={"pk": self.media.pk})

        update_response = self.client.patch(url, {"titulo": "Título actualizado"})
        delete_response = self.client.delete(url)

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["titulo"], "Título actualizado")
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Media.objects.filter(pk=self.media.pk).exists())

    def test_genre_and_person_crud_is_admin_only(self):
        regular_user = Usuario.objects.create_user(
            username="lector-catalogo", password="test-password"
        )
        self.client.force_authenticate(user=regular_user)
        genre_forbidden = self.client.post(
            reverse("genero-list"), {"nombre": "Acción"}
        )
        person_forbidden = self.client.post(
            reverse("persona-list"), {"nombre": "Persona no autorizada"}
        )
        self.assertEqual(genre_forbidden.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(person_forbidden.status_code, status.HTTP_403_FORBIDDEN)

        admin_user = Usuario.objects.create_user(
            username="admin-personas",
            password="test-password",
            is_staff=True,
        )
        self.client.force_authenticate(user=admin_user)

        genre_response = self.client.post(
            reverse("genero-list"), {"nombre": "Acción"}
        )
        self.assertEqual(genre_response.status_code, status.HTTP_201_CREATED)
        genre_url = reverse("genero-detail", kwargs={"pk": genre_response.data["id"]})
        genre_update = self.client.patch(genre_url, {"nombre": "Aventura"})
        genre_delete = self.client.delete(genre_url)
        self.assertEqual(genre_update.status_code, status.HTTP_200_OK)
        self.assertEqual(genre_update.data["nombre"], "Aventura")
        self.assertEqual(genre_delete.status_code, status.HTTP_204_NO_CONTENT)

        person_response = self.client.post(
            reverse("persona-list"),
            {
                "nombre": "Persona de prueba",
                "biografia": "Biografía inicial.",
                "fecha_nacimiento": "1980-01-02",
            },
        )
        self.assertEqual(person_response.status_code, status.HTTP_201_CREATED)
        person_url = reverse(
            "persona-detail", kwargs={"pk": person_response.data["id"]}
        )
        person_update = self.client.patch(
            person_url, {"biografia": "Biografía actualizada."}
        )
        person_delete = self.client.delete(person_url)
        self.assertEqual(person_update.status_code, status.HTTP_200_OK)
        self.assertEqual(person_update.data["biografia"], "Biografía actualizada.")
        self.assertEqual(person_delete.status_code, status.HTTP_204_NO_CONTENT)

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

    def test_each_catalog_filter_selects_matching_media(self):
        genero = Genero.objects.create(nombre="Comedia")
        target = Media.objects.create(
            titulo="Serie filtrable",
            tipo=Media.Tipo.SERIE,
            fecha_estreno=date(2024, 7, 12),
            estado=Media.Estado.EN_CARTELERA,
        )
        target.generos.add(genero)
        Media.objects.create(
            titulo="Anime alternativo",
            tipo=Media.Tipo.ANIME,
            fecha_estreno=date(2023, 4, 1),
            estado=Media.Estado.FUERA_CARTELERA,
        )

        for filter_params in (
            {"genero": "Comedia"},
            {"tipo": Media.Tipo.SERIE},
            {"anio": "2024"},
            {"estado": Media.Estado.EN_CARTELERA},
        ):
            with self.subTest(filter=filter_params):
                response = self.client.get(reverse("media-list"), filter_params)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data["count"], 1)
                self.assertEqual(response.data["results"][0]["id"], target.pk)

    def test_cinema_filter_uses_showtime_relationship_without_duplicates(self):
        matching_cinema = Cine.objects.create(nombre="Cine filtrado", ciudad="Bogotá")
        other_cinema = Cine.objects.create(nombre="Otro cine", ciudad="Cali")
        other_media = Media.objects.create(
            titulo="Sin funciones en el cine",
            tipo=Media.Tipo.PELICULA,
        )
        Funcion.objects.create(
            media=self.media,
            cine=matching_cinema,
            fecha_hora=datetime(2026, 11, 10, 19, 30, tzinfo=timezone.utc),
        )
        Funcion.objects.create(
            media=self.media,
            cine=matching_cinema,
            fecha_hora=datetime(2026, 11, 11, 19, 30, tzinfo=timezone.utc),
        )
        Funcion.objects.create(
            media=self.media,
            cine=other_cinema,
            fecha_hora=datetime(2026, 11, 12, 19, 30, tzinfo=timezone.utc),
        )
        Funcion.objects.create(
            media=other_media,
            cine=other_cinema,
            fecha_hora=datetime(2026, 11, 12, 20, 30, tzinfo=timezone.utc),
        )

        response = self.client.get(
            reverse("media-list"),
            {"cine": str(matching_cinema.pk)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.media.pk)

    def test_invalid_or_unknown_cinema_filter(self):
        invalid = self.client.get(reverse("media-list"), {"cine": "valledupar"})
        unknown = self.client.get(reverse("media-list"), {"cine": "999999"})

        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(unknown.status_code, status.HTTP_200_OK)
        self.assertEqual(unknown.data["count"], 0)

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