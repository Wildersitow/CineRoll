from datetime import datetime, time, timedelta, timezone

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone as django_timezone
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

    def test_cinema_list_filters_by_normalized_city(self):
        santa_marta = Cine.objects.create(
            nombre="Cine samario",
            ciudad="santa-marta",
        )

        for city, expected_ids in (
            ("BOGOTÁ", {self.cine.pk, self.other_cine.pk}),
            ("Santa Marta", {santa_marta.pk}),
            ("santa-marta", {santa_marta.pk}),
        ):
            with self.subTest(city=city):
                response = self.client.get(reverse("cine-list"), {"ciudad": city})

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    {item["id"] for item in response.data["results"]},
                    expected_ids,
                )

    def test_cinema_list_rejects_an_empty_city_filter(self):
        response = self.client.get(reverse("cine-list"), {"ciudad": "  "})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cinema_detail_and_showtimes_are_public(self):
        response = self.client.get(reverse("cine-detail", kwargs={"pk": self.cine.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.cine.pk)
        self.assertEqual(response.data["nombre"], "Cine de prueba")

        response = self.client.get(
            reverse("cine-funciones", kwargs={"cine_id": self.cine.pk}),
            {"fecha": "2026-10-15"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["resultados"]), 1)
        self.assertEqual(response.data["resultados"][0]["id"], self.function.pk)

    def test_cinema_showtimes_can_filter_by_date(self):
        response = self.client.get(
            reverse("cine-funciones", kwargs={"cine_id": self.other_cine.pk}),
            {"fecha": "2026-10-15"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["resultados"], [])

    def test_home_showtime_endpoints_return_all_todays_results_in_one_response(self):
        today = django_timezone.localdate()
        start = django_timezone.make_aware(datetime.combine(today, time.min))
        for index in range(25):
            Funcion.objects.create(
                media=self.media,
                cine=self.cine,
                fecha_hora=start + timedelta(minutes=index),
                sala=f"Sala {index}",
                formato="2D",
            )

        city_url = reverse("funcion-list")
        city_response = self.client.get(city_url, {"ciudad": "bogotá"})
        today_alias_response = self.client.get(
            city_url,
            {"fecha": "hoy", "ciudad": "bogotá"},
        )
        cinema_response = self.client.get(
            reverse("cine-funciones", kwargs={"cine_id": self.cine.pk})
        )

        self.assertEqual(city_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(city_response.data["resultados"]), 25)
        self.assertEqual(len(today_alias_response.data["resultados"]), 25)
        self.assertEqual(cinema_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(cinema_response.data["resultados"]), 25)
        self.assertIsNotNone(city_response.data["ultima_actualizacion"])
        self.assertIsNotNone(today_alias_response.data["ultima_actualizacion"])
        self.assertIsNotNone(cinema_response.data["ultima_actualizacion"])

    def test_home_showtime_freshness_uses_city_or_cinema_before_date_filter(self):
        now = django_timezone.now()
        oldest_update = now - timedelta(days=2)
        latest_city_update = now - timedelta(days=1)
        latest_other_city_update = now
        Funcion.objects.filter(pk=self.function.pk).update(
            fecha_actualizacion=oldest_update
        )
        Funcion.objects.filter(pk=self.other_date_function.pk).update(
            fecha_actualizacion=latest_city_update
        )

        medellin = Cine.objects.create(nombre="Cine Medellín", ciudad="Medellín")
        medellin_function = Funcion.objects.create(
            media=self.media,
            cine=medellin,
            fecha_hora=datetime(2026, 10, 15, 20, 0, tzinfo=timezone.utc),
        )
        Funcion.objects.filter(pk=medellin_function.pk).update(
            fecha_actualizacion=latest_other_city_update
        )

        city_response = self.client.get(
            reverse("funcion-list"),
            {"fecha": "2099-01-01", "ciudad": "bogota"},
        )
        cinema_response = self.client.get(
            reverse("cine-funciones", kwargs={"cine_id": self.cine.pk}),
            {"fecha": "2099-01-01"},
        )

        self.assertEqual(city_response.data["resultados"], [])
        self.assertEqual(
            city_response.data["ultima_actualizacion"], latest_city_update
        )
        self.assertEqual(cinema_response.data["resultados"], [])
        self.assertEqual(
            cinema_response.data["ultima_actualizacion"], oldest_update
        )

    def test_unknown_cinema_showtimes_return_not_found(self):
        response = self.client.get(
            reverse("cine-funciones", kwargs={"cine_id": 999999})
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_all_showtimes_can_filter_by_date_and_city(self):
        response = self.client.get(
            reverse("funcion-list"),
            {"fecha": "2026-10-15", "ciudad": "bogotá"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["resultados"]), 1)
        self.assertEqual(response.data["resultados"][0]["id"], self.function.pk)

    def test_invalid_showtime_filters_return_bad_request(self):
        invalid_date = self.client.get(reverse("funcion-list"), {"fecha": "tomorrow"})
        invalid_city = self.client.get(reverse("funcion-list"), {"ciudad": "  "})

        self.assertEqual(invalid_date.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_city.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cine_writes_are_forbidden_for_anonymous_and_regular_users(self):
        url = reverse("cine-list")
        payload = {"nombre": "Nuevo cine", "ciudad": "Bogotá"}

        anonymous_response = self.client.post(url, payload)

        regular_user = get_user_model().objects.create_user(
            username="regular", password="test-password"
        )
        self.client.force_authenticate(user=regular_user)
        regular_response = self.client.post(url, payload)

        self.assertEqual(anonymous_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(regular_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Cine.objects.filter(nombre="Nuevo cine").exists())

    def test_staff_user_can_write_cines(self):
        admin = get_user_model().objects.create_user(
            username="staff", password="test-password", is_staff=True
        )
        self.client.force_authenticate(user=admin)

        create_response = self.client.post(
            reverse("cine-list"),
            {"nombre": "Nuevo cine", "ciudad": "Valledupar"},
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        cine_id = create_response.data["id"]
        update_response = self.client.patch(
            reverse("cine-detail", kwargs={"pk": cine_id}),
            {"direccion": "Calle 10"},
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["direccion"], "Calle 10")

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

    def test_city_filter_ignores_accents_case_and_slugs(self):
        slug_cinema = Cine.objects.create(nombre="Cine slug", ciudad="bogota")
        slug_function = Funcion.objects.create(
            media=self.media,
            cine=slug_cinema,
            fecha_hora=datetime(2026, 10, 15, 21, 0, tzinfo=timezone.utc),
            sala="Sala 9",
            formato="2D",
        )
        other_cinema = Cine.objects.create(nombre="Otra ciudad", ciudad="Medellín")
        Funcion.objects.create(
            media=self.media,
            cine=other_cinema,
            fecha_hora=datetime(2026, 10, 15, 20, 0, tzinfo=timezone.utc),
        )

        for city in ("Bogotá", "bogota", "BOGOTÁ", "bogotá"):
            with self.subTest(city=city):
                response = self.client.get(
                    reverse("funcion-list"), {"fecha": "2026-10-15", "ciudad": city}
                )
                ids = {item["id"] for item in response.data["resultados"]}
                self.assertEqual(ids, {self.function.pk, slug_function.pk})

    def test_city_filter_matches_slug_with_hyphens(self):
        cinema = Cine.objects.create(nombre="Cine Samario", ciudad="santa-marta")
        function = Funcion.objects.create(
            media=self.media,
            cine=cinema,
            fecha_hora=datetime(2026, 10, 15, 20, 0, tzinfo=timezone.utc),
        )

        response = self.client.get(
            reverse("funcion-list"), {"fecha": "2026-10-15", "ciudad": "Santa Marta"}
        )

        self.assertEqual(
            [item["id"] for item in response.data["resultados"]], [function.pk]
        )

    def test_valledupar_filter_returns_functions_from_all_cinemas(self):
        cinemas = [
            Cine.objects.create(nombre=name, ciudad="valledupar")
            for name in ("Cinépolis", "Royal Films", "Cineland")
        ]
        functions = [
            Funcion.objects.create(
                media=self.media,
                cine=cinema,
                fecha_hora=datetime(2026, 10, 15, 20, 0, tzinfo=timezone.utc),
            )
            for cinema in cinemas
        ]

        response = self.client.get(
            reverse("funcion-list"),
            {"fecha": "2026-10-15", "ciudad": "valledupar"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["id"] for item in response.data["resultados"]},
            {function.pk for function in functions},
        )
