from django.contrib import admin
from django.test import TestCase
from django.urls import reverse

from media.models import Media
from social.models import Resena
from usuarios.models import Usuario


class ResenaAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_superuser(username="root", email="root@example.com", password="x")
        cls.media = Media.objects.create(titulo="A", tipo=Media.Tipo.PELICULA)
        lector = Usuario.objects.create_user(username="lector", password="x")
        cls.resena = Resena.objects.create(usuario=lector, media=cls.media, puntuacion=1, texto="Spam")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_resena_esta_registrada(self):
        self.assertIn(Resena, admin.site._registry)

    def test_paginas_del_admin(self):
        self.assertEqual(self.client.get(reverse("admin:social_resena_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:social_resena_add")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("admin:social_resena_change", args=[self.resena.pk])).status_code, 200
        )

    def _accion(self, nombre):
        return self.client.post(
            reverse("admin:social_resena_changelist"),
            {"action": nombre, "_selected_action": [self.resena.pk]},
            follow=True,
        )

    def test_el_administrador_puede_ocultar_y_volver_a_mostrar(self):
        self._accion("ocultar_resenas")
        self.resena.refresh_from_db()
        self.assertTrue(self.resena.oculta)

        self._accion("mostrar_resenas")
        self.resena.refresh_from_db()
        self.assertFalse(self.resena.oculta)

    def test_el_administrador_puede_borrar_resenas_inapropiadas(self):
        response = self.client.post(
            reverse("admin:social_resena_delete", args=[self.resena.pk]), {"post": "yes"}, follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Resena.objects.exists())
