from django.contrib import admin
from django.test import TestCase
from django.urls import reverse

from media.admin import CreditoInline
from media.models import Credito, Genero, Media, Persona
from usuarios.models import Usuario


class CatalogAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_superuser(
            username="admin-catalogo",
            email="admin@example.com",
            password="test-password",
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_catalog_models_are_registered_with_admin(self):
        for model in (Media, Genero, Persona, Credito):
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)

        self.assertIn(CreditoInline, admin.site._registry[Media].inlines)

    def test_admin_list_and_add_pages_are_available(self):
        model_names = ("media", "genero", "persona", "credito")

        for model_name in model_names:
            with self.subTest(model=model_name, page="changelist"):
                response = self.client.get(
                    reverse(f"admin:media_{model_name}_changelist")
                )
                self.assertEqual(response.status_code, 200)

            with self.subTest(model=model_name, page="add"):
                response = self.client.get(
                    reverse(f"admin:media_{model_name}_add")
                )
                self.assertEqual(response.status_code, 200)