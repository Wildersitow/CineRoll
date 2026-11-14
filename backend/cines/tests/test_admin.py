from django.contrib import admin
from django.test import TestCase
from django.urls import reverse

from cines.models import Cine, Funcion, TituloPendiente
from cines.services import match_media_title
from media.models import Media
from usuarios.models import Usuario


class CinesAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_superuser(
            username="admin-cines",
            email="admin-cines@example.com",
            password="test-password",
        )
        cls.media = Media.objects.create(
            titulo="Cómo entrenar a tu dragón", tipo=Media.Tipo.PELICULA
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def _pendiente(self, **extra):
        datos = {
            "titulo_original": "COMO ENTRENAR A TU DRAGON",
            "titulo_normalizado": "como entrenar a tu dragon",
            "cine_nombre": "Cine de prueba",
            "ciudad": "bogota",
        }
        datos.update(extra)
        return TituloPendiente.objects.create(**datos)

    def test_cines_models_are_registered_with_admin(self):
        for model in (Cine, Funcion, TituloPendiente):
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)

    def test_admin_list_and_add_pages_are_available(self):
        for model_name in ("cine", "funcion", "titulopendiente"):
            for page in ("changelist", "add"):
                with self.subTest(model=model_name, page=page):
                    response = self.client.get(
                        reverse(f"admin:cines_{model_name}_{page}")
                    )
                    self.assertEqual(response.status_code, 200)

    def test_choosing_media_resolves_pending_title(self):
        pendiente = self._pendiente()
        url = reverse("admin:cines_titulopendiente_change", args=[pendiente.pk])

        response = self.client.post(
            url,
            {"estado": TituloPendiente.Estado.PENDIENTE, "media_asociada": self.media.pk},
        )

        self.assertEqual(response.status_code, 302)
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, TituloPendiente.Estado.RESUELTO)
        self.assertEqual(pendiente.media_asociada, self.media)

    def test_ignore_action_marks_titles_as_ignored(self):
        pendiente = self._pendiente()

        response = self.client.post(
            reverse("admin:cines_titulopendiente_changelist"),
            {"action": "marcar_ignorados", "_selected_action": [pendiente.pk]},
        )

        self.assertEqual(response.status_code, 302)
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, TituloPendiente.Estado.IGNORADO)

    def test_create_draft_action_resolves_titles_and_reuses_same_normalized_title(self):
        pendiente = self._pendiente(
            titulo_original="PELÍCULA DE PRUEBA (DOB 2D)",
            titulo_normalizado="pelicula de prueba",
        )
        mismo_titulo_otro_cine = self._pendiente(
            titulo_original="Película de prueba",
            titulo_normalizado="pelicula de prueba",
            cine_nombre="Otro cine",
            ciudad="cali",
        )

        response = self.client.post(
            reverse("admin:cines_titulopendiente_changelist"),
            {
                "action": "crear_fichas_borrador",
                "_selected_action": [pendiente.pk, mismo_titulo_otro_cine.pk],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Media.objects.count(), 2)
        ficha = Media.objects.get(titulo="pelicula de prueba")
        self.assertEqual(ficha.tipo, Media.Tipo.PELICULA)
        self.assertEqual(ficha.estado, Media.Estado.EN_CARTELERA)
        self.assertEqual(ficha.titulo_original, "")
        self.assertEqual(ficha.sinopsis, "")
        self.assertIsNone(ficha.fecha_estreno)
        self.assertIsNone(ficha.duracion)
        self.assertEqual(ficha.poster_url, "")
        self.assertEqual(ficha.trailer_url, "")
        self.assertEqual(ficha.generos.count(), 0)
        self.assertEqual(ficha.creditos.count(), 0)

        for titulo_pendiente in (pendiente, mismo_titulo_otro_cine):
            titulo_pendiente.refresh_from_db()
            self.assertEqual(titulo_pendiente.estado, TituloPendiente.Estado.RESUELTO)
            self.assertEqual(titulo_pendiente.media_asociada, ficha)

        self.assertEqual(match_media_title(pendiente.titulo_original), ficha)
