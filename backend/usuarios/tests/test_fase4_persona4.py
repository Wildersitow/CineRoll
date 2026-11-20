from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from social.models import Lista, Seguimiento

Usuario = get_user_model()


class Fase4Persona4UsuariosTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_existente = Usuario.objects.create_user(
            username="valeria",
            email="valeria@example.com",
            password="Secur3Password!",
            first_name="Valeria",
            last_name="Ríos",
        )
        cls.user2 = Usuario.objects.create_user(
            username="diego",
            email="diego@example.com",
            password="Secur3Password!",
        )

    def test_registro_rechaza_nombres_reservados(self):
        url = reverse("auth_registro")
        for reservado in ["me", "admin", "api", "root", "soporte", "staff", "ME", "Admin"]:
            res = self.client.post(
                url,
                {
                    "username": reservado,
                    "email": f"{reservado}@example.com",
                    "password": "Password123!",
                },
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("username", res.data["error"]["campos"])

    def test_registro_valida_username_unico_case_insensitive(self):
        url = reverse("auth_registro")
        # 'valeria' ya existe en setUpTestData; intentar registrar 'VALERIA' o 'Valeria' debe fallar
        res = self.client.post(
            url,
            {
                "username": "VALERIA",
                "email": "valeria2@example.com",
                "password": "Password123!",
            },
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", res.data["error"]["campos"])

    def test_registro_crea_listas_del_sistema_en_misma_transaccion(self):
        url = reverse("auth_registro")
        res = self.client.post(
            url,
            {
                "username": "sofia",
                "email": "sofia@example.com",
                "password": "Password123!",
            },
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        sofia = Usuario.objects.get(username="sofia")
        listas_sofia = Lista.objects.filter(usuario=sofia)
        self.assertEqual(listas_sofia.count(), 2)

        tipos = set(listas_sofia.values_list("tipo", flat=True))
        self.assertEqual(tipos, {Lista.Tipo.FAVORITAS, Lista.Tipo.POR_VER})

    def test_perfil_publico_ampliado_visitante(self):
        Seguimiento.objects.create(seguidor=self.user2, seguido=self.user_existente)

        url = reverse("usuarios_perfil_publico", args=["valeria"])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_seguidores"], 1)
        self.assertEqual(res.data["total_siguiendo"], 0)
        self.assertIsNone(res.data["lo_sigo"])  # Visitante -> null

    def test_perfil_publico_ampliado_usuario_autenticado(self):
        Seguimiento.objects.create(seguidor=self.user2, seguido=self.user_existente)

        # diego ve el perfil de valeria -> lo_sigo es True
        self.client.force_authenticate(self.user2)
        url = reverse("usuarios_perfil_publico", args=["valeria"])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_seguidores"], 1)
        self.assertTrue(res.data["lo_sigo"])

        # valeria ve su propio perfil público -> lo_sigo es False
        self.client.force_authenticate(self.user_existente)
        res_propio = self.client.get(url)
        self.assertEqual(res_propio.status_code, status.HTTP_200_OK)
        self.assertFalse(res_propio.data["lo_sigo"])

    def test_perfil_publico_sin_consultas_por_cada_usuario(self):
        Seguimiento.objects.create(seguidor=self.user2, seguido=self.user_existente)
        self.client.force_authenticate(self.user2)

        url = reverse("usuarios_perfil_publico", args=["valeria"])
        # Se ejecuta en 3 consultas: 1 para el usuario con todos los campos sociales anotados (seguidores, siguiendo, lo_sigo),
        # 1 para total_resenas y 1 para promedio_puntuacion_dada. Cero consultas adicionales por seguimiento.
        with self.assertNumQueries(3):
            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
