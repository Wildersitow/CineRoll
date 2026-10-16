from datetime import datetime, timezone

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cines.models import Cine, Funcion
from media.models import Media


class CarteleraApiTests(APITestCase):
    def setUp(self):
        self.media = Media.objects.create(
            titulo="Película de prueba",
            tipo=Media.Tipo.PELICULA,
        )
        self.cine = Cine.objects.create(
            nombre="Cine de prueba",
            ciudad="Bogotá",
            direccion="Calle 1",
            sitio_web="https://example.com/",
        )
        self.other_cine = Cine.objects.create(
            nombre="Otro cine",
            ciudad="Bogotá",
            direccion="Calle 2",
        )
        self.function = Funcion.objects.create(
            media=self.media,
            cine=self.cine,
            fecha_hora=datetime(2026, 10, 15, 19, 30, tzinfo=timezone.utc),
            sala="Sala 1",
            formato="2D, Doblada",
            fuente_scraping="https://example.com/cartelera/",
        )
        self.other_date_function = Funcion.objects.create(
            media=self.media,
            cine=self.other_cine,
            fecha_hora=datetime(2026, 10, 16, 20, 0, tzinfo=timezone.utc),
            sala="Sala 2",
            formato="3D",
        )

    def test_cinema_list_is_public_and_paginated(self):
        response = self.client.get(reverse("cine-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            {cine["nombre"] for cine in response.data["results"]},
            {"Cine de prueba", "Otro cine"},
        )

    def test_movie_showtimes_are_public_and_include_freshness(self):
        response = self.client.get(
            reverse("media-funciones", kwargs={"media_id": self.media.pk})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["resultados"]), 2)
        self.assertIsNotNone(response.data["ultima_actualizacion"])
        result = response.data["resultados"][0]
        self.assertEqual(result["media_id"], self.media.pk)
        self.assertEqual(result["media_titulo"], "Película de prueba")
        self.assertIn("fecha_hora", result)
        self.assertIn("fecha_actualizacion", result)
        self.assertEqual(result["cine"]["id"], self.cine.pk)

    def test_movie_showtimes_can_filter_by_cinema_and_date(self):
        response = self.client.get(
            reverse("media-funciones", kwargs={"media_id": self.media.pk}),
            {"cine": self.cine.pk, "fecha": "2026-10-15"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["resultados"]), 1)
        self.assertEqual(response.data["resultados"][0]["id"], self.function.pk)
        self.assertEqual(
            response.data["resultados"][0]["cine"]["id"], self.cine.pk
        )
        self.assertIsNotNone(response.data["ultima_actualizacion"])

    def test_invalid_cinema_and_date_filters_return_bad_request(self):
        url = reverse("media-funciones", kwargs={"media_id": self.media.pk})

        invalid_cinema = self.client.get(url, {"cine": "not-an-id"})
        invalid_date = self.client.get(url, {"fecha": "tomorrow"})

        self.assertEqual(invalid_cinema.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_date.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_media_returns_not_found(self):
        response = self.client.get(
            reverse("media-funciones", kwargs={"media_id": 999999})
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_matches_returns_empty_list_and_null_freshness(self):
        response = self.client.get(
            reverse("media-funciones", kwargs={"media_id": self.media.pk}),
            {"fecha": "2030-01-01"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["resultados"], [])
        self.assertIsNotNone(response.data["ultima_actualizacion"])

    def test_invalid_calendar_date_returns_bad_request(self):
        response = self.client.get(
            reverse("media-funciones", kwargs={"media_id": self.media.pk}),
            {"fecha": "2026-02-30"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
