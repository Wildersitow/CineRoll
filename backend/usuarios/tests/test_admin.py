from django.contrib import admin
from django.test import TestCase
from django.urls import reverse

from usuarios.models import Usuario


class UsuarioAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_superuser(
            username="root", email="root@example.com", password="test-password"
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_usuario_esta_registrado(self):
        self.assertIn(Usuario, admin.site._registry)

    def test_paginas_del_admin_de_usuarios(self):
        self.assertEqual(self.client.get(reverse("admin:usuarios_usuario_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:usuarios_usuario_add")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("admin:usuarios_usuario_change", args=[self.admin.pk])).status_code, 200
        )
