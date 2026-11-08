from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from media.models import Media
from social.models import Resena
from usuarios.models import Usuario

CLAVE = "Un4Clave-Segura!"


class EscalaCalificacionTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(username="ana", email="ana@example.com", password=CLAVE)
        self.url = reverse("usuarios_me")

    def test_por_defecto_es_de_1_a_10(self):
        self.assertEqual(self.usuario.escala_calificacion, 10)

    def test_aparece_en_el_perfil_y_en_el_login(self):
        self.client.force_authenticate(self.usuario)
        self.assertEqual(self.client.get(self.url).data["escala_calificacion"], 10)

        self.client.force_authenticate(None)
        login = self.client.post(reverse("auth_login"), {"usuario": "ana", "clave": CLAVE})
        self.assertEqual(login.data["escala_calificacion"], 10)

    def test_el_usuario_puede_elegir_cualquiera_de_las_dos_escalas(self):
        self.client.force_authenticate(self.usuario)

        for escala in (5, 10, "5"):
            with self.subTest(escala=escala):
                response = self.client.patch(self.url, {"escala_calificacion": escala})
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.usuario.refresh_from_db()
                self.assertEqual(self.usuario.escala_calificacion, int(escala))

    def test_rechaza_escalas_que_no_existen(self):
        self.client.force_authenticate(self.usuario)

        for escala in (0, 3, 7, 100, "abc", None):
            with self.subTest(escala=escala):
                response = self.client.patch(self.url, {"escala_calificacion": escala}, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.escala_calificacion, 10)

    def test_se_puede_elegir_al_registrarse(self):
        datos = {"username": "nueva", "email": "nueva@example.com", "password": CLAVE}

        con_escala = self.client.post(reverse("auth_registro"), {**datos, "escala_calificacion": 5})
        self.assertEqual(con_escala.status_code, status.HTTP_201_CREATED)
        self.assertEqual(con_escala.data["escala_calificacion"], 5)

        sin_escala = self.client.post(
            reverse("auth_registro"),
            {"username": "otra", "email": "otra@example.com", "password": CLAVE},
        )
        self.assertEqual(sin_escala.data["escala_calificacion"], 10)

    def test_cambiar_la_escala_no_altera_las_reseñas_guardadas(self):
        media = Media.objects.create(titulo="A", tipo=Media.Tipo.PELICULA)
        resena = Resena.objects.create(usuario=self.usuario, media=media, puntuacion=7)

        self.client.force_authenticate(self.usuario)
        self.client.patch(self.url, {"escala_calificacion": 5})

        resena.refresh_from_db()
        self.assertEqual(resena.puntuacion, 7)  # sigue en 1–10; solo cambia cómo se muestra
        detalle = self.client.get(reverse("resena-detail", kwargs={"pk": resena.pk}))
        self.assertEqual(detalle.data["puntuacion"], 7)